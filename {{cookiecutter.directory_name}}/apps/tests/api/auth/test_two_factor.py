"""
Tests for two-factor authentication (IP-003): TOTP and e-mail codes, backup codes and the login challenge.
"""

import re
from http import HTTPStatus

import pyotp
from django.core import mail
from django.urls import reverse

from apps.core.models import BackupCode, Token, User
from apps.tests.base import Base
from apps.tests.fixtures import UserFixture


class TwoFactorTestCase(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._token_url = reverse('token')
        cls._two_factor_url = reverse('two-factor')
        cls._confirm_url = reverse('two-factor-confirm')
        cls._verify_url = reverse('two-factor-verify')
        cls._backup_codes_url = reverse('two-factor-backup-codes')

    def setUp(self):
        super().setUp()
        self.user = UserFixture.create_user(email='mfa@example.com')
        self.auth = self.authenticate(self.user)

    def login(self):
        """Password login through POST /token; returns the response."""
        return self.post(self._token_url, {'email': self.user.email, 'password': self.user.plain_password})

    def enrol_totp(self) -> str:
        """Run the two-step TOTP setup and return the secret."""
        response = self.post(self._two_factor_url, {'method': User.TwoFactorMethod.TOTP}, headers=self.auth)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        secret = response.content_dict['response']['secret']

        response = self.post(self._confirm_url, {'code': pyotp.TOTP(secret).now()}, headers=self.auth)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.backup_codes = response.content_dict['response']['backup_codes']

        return secret


class TestTotpEnrolment(TwoFactorTestCase):
    def test_enrolment_returns_secret_and_leaves_second_factor_off(self):
        response = self.post(self._two_factor_url, {'method': User.TwoFactorMethod.TOTP}, headers=self.auth)

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertIn('otpauth_uri', response.content_dict['response'])
        self.user.refresh_from_db()
        self.assertTrue(self.user.totp_secret)
        self.assertFalse(self.user.two_factor_enabled)

    def test_confirm_with_correct_code_enables_and_returns_backup_codes(self):
        self.enrol_totp()

        self.user.refresh_from_db()
        self.assertTrue(self.user.two_factor_enabled)
        self.assertEqual(self.user.two_factor_method, User.TwoFactorMethod.TOTP)
        self.assertEqual(len(self.backup_codes), 10)
        self.assertEqual(BackupCode.objects.filter(user=self.user).count(), 10)

    def test_confirm_with_wrong_code_is_refused_and_keeps_second_factor_off(self):
        self.post(self._two_factor_url, {'method': User.TwoFactorMethod.TOTP}, headers=self.auth)

        response = self.post(self._confirm_url, {'code': '000000'}, headers=self.auth)

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.user.refresh_from_db()
        self.assertFalse(self.user.two_factor_enabled)

    def test_confirm_without_setup_conflicts(self):
        response = self.post(self._confirm_url, {'code': '123456'}, headers=self.auth)

        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)

    def test_disable_clears_secret_and_backup_codes(self):
        self.enrol_totp()

        response = self.delete(self._two_factor_url, headers=self.auth)

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.user.refresh_from_db()
        self.assertFalse(self.user.two_factor_enabled)
        self.assertIsNone(self.user.totp_secret)
        self.assertFalse(BackupCode.objects.filter(user=self.user).exists())

    def test_regenerating_backup_codes_invalidates_previous_ones(self):
        self.enrol_totp()
        old_codes = self.backup_codes

        response = self.post(self._backup_codes_url, headers=self.auth)

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        new_codes = response.content_dict['response']['backup_codes']
        self.assertNotEqual(old_codes, new_codes)
        self.assertEqual(BackupCode.objects.filter(user=self.user, used_at__isnull=True).count(), 10)


class TestTwoFactorLogin(TwoFactorTestCase):
    def test_password_login_returns_challenge_then_token_after_totp(self):
        secret = self.enrol_totp()

        response = self.login()

        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)
        self.assertNotIn('token', response.content_dict.get('response', {}))
        challenge_id = response.content_dict['response']['challenge_id']

        response = self.post(self._verify_url, {'challenge_id': challenge_id, 'code': pyotp.TOTP(secret).now()})

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        token = response.content_dict['response']['token']
        self.assertTrue(Token.objects.filter(pk=token, user=self.user).exists())

    def test_backup_code_replaces_the_authenticator_and_is_single_use(self):
        self.enrol_totp()
        backup_code = self.backup_codes[0]

        challenge_id = self.login().content_dict['response']['challenge_id']
        response = self.post(self._verify_url, {'challenge_id': challenge_id, 'code': backup_code})
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        challenge_id = self.login().content_dict['response']['challenge_id']
        response = self.post(self._verify_url, {'challenge_id': challenge_id, 'code': backup_code})
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_wrong_code_is_refused(self):
        self.enrol_totp()
        challenge_id = self.login().content_dict['response']['challenge_id']

        response = self.post(self._verify_url, {'challenge_id': challenge_id, 'code': '000000'})

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_too_many_wrong_codes_end_the_challenge(self):
        self.enrol_totp()
        challenge_id = self.login().content_dict['response']['challenge_id']

        for _ in range(5):
            self.post(self._verify_url, {'challenge_id': challenge_id, 'code': '000000'})

        response = self.post(self._verify_url, {'challenge_id': challenge_id, 'code': '000000'})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_login_without_second_factor_still_returns_token(self):
        response = self.login()

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertIn('token', response.content_dict['response'])

    def test_disabled_second_factor_no_longer_challenges(self):
        self.enrol_totp()
        self.delete(self._two_factor_url, headers=self.auth)

        response = self.login()

        self.assertEqual(response.status_code, HTTPStatus.CREATED)


class TestEmailTwoFactor(TwoFactorTestCase):
    def test_email_code_is_sent_and_completes_login(self):
        response = self.post(self._two_factor_url, {'method': User.TwoFactorMethod.EMAIL}, headers=self.auth)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(len(response.content_dict['response']['backup_codes']), 10)

        mail.outbox = []
        challenge_id = self.login().content_dict['response']['challenge_id']

        self.assertEqual(len(mail.outbox), 1)
        html = mail.outbox[0].alternatives[0][0]
        code = re.search(r"\b(\d{6})\b", html).group(1)

        response = self.post(self._verify_url, {'challenge_id': challenge_id, 'code': code})

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
