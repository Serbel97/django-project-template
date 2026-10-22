"""
SSO through django-allauth (IP-003 Key Components 2–5).

OIDC claims are first turned into a protocol-neutral :class:`SSOIdentity`, so a SAML mapper can be added
later without touching the user handling. The allauth adapters stay thin:

* ``populate_user`` — first login, on allauth's fresh unsaved user: maps the identity;
* ``save_user`` — first login: refuses a missing or taken e-mail, stores the user without a usable password;
* ``pre_social_login`` — every login of a known SocialAccount: refreshes the attributes and groups.

The identity is ``SocialAccount(provider, uid=sub)``; the e-mail stays the login field of ``users`` and
is refreshed from the IdP. There is no account linking by e-mail: an IdP that asserts the e-mail of an
existing account is refused rather than handed that account. A refused login is redirected to the
SPA's ``socialaccount_login_error`` page with ``?error=<code>``.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import NoReturn
from urllib.parse import urlencode, urlsplit

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme

from apps.core.models import User

logger = logging.getLogger(__name__)


class SSORefused(Exception):
    """An SSO login the API refuses; ``code`` reaches the SPA as ``?error=<code>``."""

    EMAIL_MISSING = 'email_missing'
    EMAIL_CONFLICT = 'email_conflict'

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SSOIdentity:
    """What the API keeps from an IdP login, independent of the protocol."""

    uid: str
    email: str | None = None
    name: str = ''
    surname: str = ''
    groups: list[str] = field(default_factory=list)


def claims_from_extra_data(extra_data) -> dict:
    """
    The flat claim set allauth stored for an OIDC login.

    Depending on the allauth version ``extra_data`` holds the claims themselves or
    ``{'id_token': {...}, 'userinfo': {...}}``; userinfo wins over the ID token.
    """
    data = dict(extra_data or {})
    nested = [data[key] for key in ('id_token', 'userinfo') if isinstance(data.get(key), dict)]
    if not nested:
        return data

    claims = {key: value for key, value in data.items() if key not in ('id_token', 'userinfo')}
    for part in nested:
        claims.update(part)
    return claims


def _text(value) -> str | None:
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return None
    text = str(value).strip()
    return text or None


def normalise_groups(value) -> list[str]:
    """Sorted, de-duplicated, non-empty group names; a single string counts as one group."""
    if isinstance(value, (str, int)):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return []
    return sorted({text for text in (_text(item) for item in value) if text})


def identity_from_claims(claims: dict, groups_claim: str, uid: str | None = None) -> SSOIdentity:
    """Map OIDC claims; ``uid`` (allauth's SocialAccount.uid) wins over the ``sub`` claim."""
    subject = uid or _text(claims.get('sub'))
    if not subject:
        raise ValueError('The OIDC claims carry no subject (sub).')

    name = _text(claims.get('given_name'))
    surname = _text(claims.get('family_name'))
    if name is None and surname is None:
        # Only a display name: first word as the name, the rest as the surname
        parts = (_text(claims.get('name')) or '').split(' ', 1)
        name, surname = parts[0] or None, (parts[1] if len(parts) > 1 else None)

    email = _text(claims.get('email'))

    return SSOIdentity(
        uid=subject,
        email=email.lower() if email else None,
        name=name or '',
        surname=surname or '',
        groups=normalise_groups(claims.get(groups_claim)),
    )


def _fit(field_name: str, value: str) -> str:
    max_length = User._meta.get_field(field_name).max_length
    return value[:max_length] if max_length else value


def apply_identity(user: User, identity: SSOIdentity) -> list[str]:
    """Write ``identity`` onto ``user`` (nothing is saved); returns the changed field names."""
    if not identity.email or len(identity.email) > User._meta.get_field('email').max_length:
        raise SSORefused(SSORefused.EMAIL_MISSING, 'The IdP sent no usable e-mail address.')

    changed = []
    for field_name, value in (
        ('email', identity.email),
        ('name', _fit('name', identity.name)),
        ('surname', _fit('surname', identity.surname)),
    ):
        if getattr(user, field_name) != value:
            setattr(user, field_name, value)
            changed.append(field_name)

    if list(user.idp_groups or []) != list(identity.groups):
        user.idp_groups = list(identity.groups)
        changed.append('idp_groups')

    return changed


def ensure_email_free(user: User) -> None:
    """Refuse an e-mail another user holds — soft-deleted users included, they keep the unique row."""
    taken = User.all_objects.filter(email__iexact=user.email)
    if user.pk is not None:
        taken = taken.exclude(pk=user.pk)

    if taken.exists():
        raise SSORefused(SSORefused.EMAIL_CONFLICT, 'The e-mail belongs to another account.')


def register_new_user(user: User) -> None:
    """First login: refuse conflicts before anything is written; SSO users get no password."""
    ensure_email_free(user)
    user.is_superuser = False
    user.is_staff = False
    user.set_unusable_password()


def refresh_existing_user(user: User, identity: SSOIdentity) -> None:
    """Every later login: the attributes and groups follow the IdP."""
    changed = apply_identity(user, identity)
    if not changed:
        return

    ensure_email_free(user)
    with conflicts_refused():
        user.save(update_fields=[*changed, 'updated_at'])


@contextmanager
def conflicts_refused() -> Iterator[None]:
    """
    Run the writes atomically; a unique violation of a concurrent login becomes an e-mail conflict.

    The existence checks run first, so this only catches the race between check and insert. The savepoint
    rolls back everything written inside, so no user is left without its SocialAccount.
    """
    try:
        with transaction.atomic():
            yield
    except IntegrityError as error:
        raise SSORefused(SSORefused.EMAIL_CONFLICT, 'The e-mail belongs to another account.') from error


def refuse(error: SSORefused) -> NoReturn:
    logger.warning('SSO login refused: %s', error.code)
    target = settings.HEADLESS_FRONTEND_URLS['socialaccount_login_error']
    raise ImmediateHttpResponse(HttpResponseRedirect(f'{target}?{urlencode({"error": error.code})}'))


class SSOSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin) -> bool:
        # Local sign-up through allauth is closed (NoSignupAccountAdapter); SSO users are created at first login.
        return True

    def is_auto_signup_allowed(self, request, sociallogin) -> bool:
        # Always straight to save_user(), which refuses a missing or taken e-mail. allauth would otherwise
        # fall back to a sign-up form the headless API has no page for.
        return True

    @staticmethod
    def _identity(sociallogin) -> SSOIdentity:
        claims = claims_from_extra_data(sociallogin.account.extra_data)
        return identity_from_claims(claims, settings.OIDC_GROUPS_CLAIM, uid=sociallogin.account.uid)

    def populate_user(self, request, sociallogin, data):
        user = sociallogin.user
        try:
            apply_identity(user, self._identity(sociallogin))
        except SSORefused as error:
            refuse(error)
        return user

    def save_user(self, request, sociallogin, form=None):
        user = sociallogin.user
        try:
            register_new_user(user)
            with conflicts_refused():
                sociallogin.save(request)
        except SSORefused as error:
            refuse(error)

        return user

    def pre_social_login(self, request, sociallogin):
        # A stored SocialAccount means a returning user; new ones go through save_user().
        if sociallogin.account.pk is None:
            return

        try:
            refresh_existing_user(sociallogin.user, self._identity(sociallogin))
        except SSORefused as error:
            refuse(error)


class NoSignupAccountAdapter(DefaultAccountAdapter):
    def __init__(self, request=None) -> None:
        # allauth ignores the argument and reads allauth.core.context.request, which is unset outside
        # allauth's middleware; keep an explicitly passed request as the fallback.
        super().__init__(request)
        self.request = context.request or request

    def is_open_for_signup(self, request) -> bool:
        return False

    def is_safe_url(self, url) -> bool:
        """Headless redirects may go to the SPA or back to the API host, nowhere else."""
        hosts = {urlsplit(settings.SPA_URL).netloc}
        if self.request is not None:
            hosts.add(self.request.get_host())
        return url_has_allowed_host_and_scheme(url, allowed_hosts=hosts)
