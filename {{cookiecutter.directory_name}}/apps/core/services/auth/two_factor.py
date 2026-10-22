"""
Two-factor authentication (IP-003).

Two methods are supported: a one-time code delivered by e-mail, and TOTP from an authenticator
application. Both go through the same challenge/verify handshake, so the API surface does not change
with the method:

1. the first factor succeeds and :meth:`TwoFactorService.start_challenge` opens a challenge
   (HTTP 202 instead of a token),
2. the client posts the code to ``/auth/2fa/verify`` with the challenge id,
3. :meth:`TwoFactorService.verify` returns the user and the caller issues the token.

Enabling TOTP is deliberately a two-step flow — :meth:`TwoFactorService.provision_totp` stores the secret
but leaves the second factor *off* until :meth:`TwoFactorService.confirm_totp` sees a working code. A
mis-scanned QR code therefore fails at setup instead of locking the account out at the next login.
"""

import secrets
from dataclasses import dataclass
from http import HTTPStatus
from typing import List
from uuid import UUID

import pyotp
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.api.errors import ProblemDetailException
from apps.core.models.backup_code import BackupCode
from apps.core.models.two_factor_challenge import TwoFactorChallenge
from apps.core.models.user import User
from apps.core.services.email_notification import NotificationEmailService

# Unambiguous alphabet: no 0/O or 1/l/I, so a code read off a screen and typed back does not fail
# for a reason the user cannot see.
BACKUP_CODE_ALPHABET = 'abcdefghjkmnpqrstuvwxyz23456789'
BACKUP_CODE_GROUP_LENGTH = 5


@dataclass
class TotpProvisioning:
    secret: str
    otpauth_uri: str


class TwoFactorService:
    # -- challenge / verify ----------------------------------------------------

    @classmethod
    def start_challenge(cls, user: User) -> TwoFactorChallenge:
        """Open a second-factor challenge for a user who passed the first factor."""
        method = user.two_factor_method or User.TwoFactorMethod.EMAIL
        expires_at = timezone.now() + settings.TWO_FACTOR_CODE_EXPIRATION

        if method == User.TwoFactorMethod.EMAIL:
            code = f"{secrets.randbelow(1000000):06d}"
            challenge = TwoFactorChallenge.objects.create(
                user=user,
                method=method,
                code_hash=make_password(code),
                expires_at=expires_at,
            )

            NotificationEmailService.create(
                recipients=[f"{user.get_full_name()} <{user.email}>"],
                subject=_('Your verification code'),
                content={'code': code, 'user': user, 'expires_at': challenge.expires_at},
                template=settings.EMAIL_TWO_FACTOR_PATH,
            ).send_email()
        else:
            challenge = TwoFactorChallenge.objects.create(user=user, method=method, expires_at=expires_at)

        return challenge

    @classmethod
    def verify(cls, challenge_id: UUID, code: str) -> User:
        """
        Verify the second factor and return the authenticated user.

        A backup code is accepted in place of the expected factor, which is the only way back in once the
        authenticator or the mailbox is gone.
        """
        try:
            challenge = TwoFactorChallenge.objects.valid().select_related('user').get(pk=challenge_id)
        except TwoFactorChallenge.DoesNotExist as e:
            raise ProblemDetailException(
                _('Two-factor challenge expired or does not exist.'), status=HTTPStatus.NOT_FOUND, previous=e
            )

        if challenge.attempts >= settings.TWO_FACTOR_MAX_ATTEMPTS:
            raise ProblemDetailException(_('Too many verification attempts.'), status=HTTPStatus.FORBIDDEN)

        # Counted before the check and saved outside any surrounding transaction, so a failed attempt
        # survives the rollback that raising below causes.
        challenge.attempts += 1
        challenge.save(update_fields=['attempts', 'updated_at'])

        if challenge.method == User.TwoFactorMethod.EMAIL:
            is_valid = bool(challenge.code_hash) and check_password(code, challenge.code_hash)
        else:
            is_valid = cls._verify_totp(challenge.user, code)

        if not is_valid:
            is_valid = cls.consume_backup_code(challenge.user, code)

        if not is_valid:
            raise ProblemDetailException(_('Invalid verification code.'), status=HTTPStatus.UNAUTHORIZED)

        challenge.verified_at = timezone.now()
        challenge.save(update_fields=['verified_at', 'updated_at'])

        return challenge.user

    @staticmethod
    def _verify_totp(user: User, code: str) -> bool:
        if not user.totp_secret:
            return False

        return pyotp.TOTP(user.totp_secret).verify(code)

    # -- enrolment -------------------------------------------------------------

    @staticmethod
    def provision_totp(user: User) -> TotpProvisioning:
        """
        Generate and store a TOTP secret, leaving two-factor authentication switched off.

        The caller shows ``otpauth_uri`` as a QR code; the user then proves the app works through
        :meth:`confirm_totp`, which is what actually enables the second factor.
        """
        secret = pyotp.random_base32()
        otpauth_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.INSTANCE_NAME)

        user.totp_secret = secret
        user.save(update_fields=['totp_secret', 'updated_at'])

        return TotpProvisioning(secret=secret, otpauth_uri=otpauth_uri)

    @classmethod
    @transaction.atomic
    def confirm_totp(cls, user: User, code: str) -> List[str]:
        """Enable TOTP once ``code`` proves the authenticator is set up. Returns backup codes."""
        if not user.totp_secret:
            raise ProblemDetailException(
                _('No authenticator secret to confirm. Start the setup first.'), status=HTTPStatus.CONFLICT
            )

        if not cls._verify_totp(user, code):
            raise ProblemDetailException(_('Invalid verification code.'), status=HTTPStatus.UNAUTHORIZED)

        user.two_factor_method = User.TwoFactorMethod.TOTP
        user.two_factor_enabled = True
        user.save(update_fields=['two_factor_method', 'two_factor_enabled', 'updated_at'])

        return cls.generate_backup_codes(user)

    @classmethod
    @transaction.atomic
    def enable_email(cls, user: User) -> List[str]:
        """Enable e-mail one-time codes. Returns backup codes."""
        user.two_factor_method = User.TwoFactorMethod.EMAIL
        user.two_factor_enabled = True
        user.totp_secret = None
        user.save(update_fields=['two_factor_method', 'two_factor_enabled', 'totp_secret', 'updated_at'])

        return cls.generate_backup_codes(user)

    @staticmethod
    @transaction.atomic
    def disable(user: User) -> User:
        """Turn the second factor off and invalidate every secret and backup code."""
        user.two_factor_enabled = False
        user.two_factor_method = None
        user.totp_secret = None
        user.save(update_fields=['two_factor_enabled', 'two_factor_method', 'totp_secret', 'updated_at'])

        BackupCode.objects.filter(user=user).hard_delete()

        return user

    # -- backup codes ----------------------------------------------------------

    @staticmethod
    def _generate_backup_code() -> str:
        groups = [
            ''.join(secrets.choice(BACKUP_CODE_ALPHABET) for _ in range(BACKUP_CODE_GROUP_LENGTH)) for _ in range(2)
        ]
        return '-'.join(groups)

    @classmethod
    @transaction.atomic
    def generate_backup_codes(cls, user: User) -> List[str]:
        """
        Replace the user's backup codes and return the new ones in clear text.

        This is the only moment the codes are readable — only their hashes are stored.
        """
        BackupCode.objects.filter(user=user).hard_delete()

        codes = [cls._generate_backup_code() for _ in range(settings.TWO_FACTOR_BACKUP_CODE_COUNT)]

        BackupCode.objects.bulk_create([BackupCode(user=user, code_hash=make_password(code)) for code in codes])

        return codes

    @staticmethod
    def normalize_backup_code(code: str) -> str:
        return (code or '').strip().lower()

    @classmethod
    def consume_backup_code(cls, user: User, code: str) -> bool:
        """Spend one matching unused backup code. Returns whether one matched."""
        candidate = cls.normalize_backup_code(code)

        if not candidate:
            return False

        for backup_code in BackupCode.objects.filter(user=user, used_at__isnull=True):
            if check_password(candidate, backup_code.code_hash):
                backup_code.used_at = timezone.now()
                backup_code.save(update_fields=['used_at', 'updated_at'])
                return True

        return False

    @staticmethod
    def unused_backup_code_count(user: User) -> int:
        return BackupCode.objects.filter(user=user, used_at__isnull=True).count()


__all__ = ['TotpProvisioning', 'TwoFactorService']
