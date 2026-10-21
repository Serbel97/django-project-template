"""
Break-glass login (IP-003 Key Component 8, Q3).

Routed only while ``BREAK_GLASS_ENABLED`` is on. Password, then TOTP (or a backup code), for superusers
with an authenticator enrolled; the result is a Django session, so the SPA works with the cookie and
no Bearer token is handed out. An account without the superuser flag is refused with 403 once its
password is proven.

Failures before the password is proven answer the same 401 whatever the reason, so the endpoint reveals
neither which emails exist nor why a login was refused.

Failed passwords and failed codes count toward a per-account lockout stored on the user row. A
locked account answers the same 401 as a wrong password, even with the right password and code.

Callers must not wrap these calls in a transaction: the failure counter of a refused attempt has to
survive the error response.
"""

from datetime import timedelta
from http import HTTPStatus
from typing import NoReturn
from uuid import UUID

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.api.errors import ProblemDetailException
from apps.core.models.two_factor_challenge import TwoFactorChallenge
from apps.core.models.user import User
from apps.core.services.auth.two_factor import TwoFactorService

# Backend recorded in the session; it must be listed in AUTHENTICATION_BACKENDS or the session never
# resolves to a user.
SESSION_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def _refuse_credentials() -> NoReturn:
    raise ProblemDetailException(_('Invalid credentials.'), status=HTTPStatus.UNAUTHORIZED)


def _is_locked(user: User) -> bool:
    return user.break_glass_locked_until is not None and user.break_glass_locked_until > timezone.now()


def _record_failure(user: User) -> None:
    user.break_glass_failures += 1
    if user.break_glass_failures >= settings.BREAK_GLASS_MAX_FAILURES:
        user.break_glass_locked_until = timezone.now() + timedelta(seconds=settings.BREAK_GLASS_LOCKOUT_SECONDS)
        user.break_glass_failures = 0
    user.save(update_fields=['break_glass_failures', 'break_glass_locked_until', 'updated_at'])


def _reset_failures(user: User) -> None:
    if user.break_glass_failures or user.break_glass_locked_until:
        user.break_glass_failures = 0
        user.break_glass_locked_until = None
        user.save(update_fields=['break_glass_failures', 'break_glass_locked_until', 'updated_at'])


def is_break_glass_user(user: User) -> bool:
    return user.is_active and user.is_superuser


class BreakGlassService:
    @staticmethod
    def start(email: str, password: str) -> TwoFactorChallenge:
        """First factor: the password of a superuser; opens a TOTP challenge."""
        user = User.objects.filter(email=email).first()

        # Timing parity: every refusal pays one password hash, so unknown emails and locked accounts answer as
        # fast as a wrong password does.
        if user is None or not user.has_usable_password() or _is_locked(user):
            make_password(password)
            _refuse_credentials()

        if not user.check_password(password):
            _record_failure(user)
            _refuse_credentials()

        if not user.is_active:
            _record_failure(user)
            _refuse_credentials()

        if not is_break_glass_user(user):
            raise ProblemDetailException(
                _('Break-glass login is restricted to superusers.'), status=HTTPStatus.FORBIDDEN
            )

        if not (user.two_factor_enabled and user.two_factor_method == User.TwoFactorMethod.TOTP):
            raise ProblemDetailException(
                _('The break-glass account has no authenticator enrolled.'), status=HTTPStatus.FORBIDDEN
            )

        return TwoFactorService.start_challenge(user)

    @staticmethod
    def verify(request, challenge_id: UUID, code: str) -> User:
        """Second factor: TOTP or a backup code; on success the request gets a Django session."""
        challenge = TwoFactorChallenge.objects.valid().select_related('user').filter(pk=challenge_id).first()

        if (
            challenge is None
            or challenge.method != User.TwoFactorMethod.TOTP
            or not is_break_glass_user(challenge.user)
        ):
            raise ProblemDetailException(
                _('Two-factor challenge expired or does not exist.'), status=HTTPStatus.NOT_FOUND
            )

        user = challenge.user

        if _is_locked(user):
            raise ProblemDetailException(_('Invalid verification code.'), status=HTTPStatus.UNAUTHORIZED)

        try:
            user = TwoFactorService.verify(challenge.pk, code)
        except ProblemDetailException:
            _record_failure(challenge.user)
            raise

        _reset_failures(user)

        # Rotates the session key and the CSRF token.
        login(request, user, backend=SESSION_BACKEND)

        return user


__all__ = ['BreakGlassService', 'SESSION_BACKEND', 'is_break_glass_user']
