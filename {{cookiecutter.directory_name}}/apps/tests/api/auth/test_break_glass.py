"""
Tests for the break-glass login (IP-003 Q3): password, then TOTP, then a Django session.
"""

from http import HTTPStatus

import pyotp
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.core.models import User
from apps.tests.base import Base
from apps.tests.fixtures import UserFixture


class BreakGlassTestCase(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._login_url = reverse('break-glass-login')
        cls._verify_url = reverse('break-glass-verify')
        cls._session_url = reverse('session')
        cls._me_url = reverse('user-me')

    def setUp(self):
        super().setUp()
        self.superuser = UserFixture.create_superuser(email='breakglass@example.com')
        self.secret = pyotp.random_base32()
        self.superuser.two_factor_enabled = True
        self.superuser.two_factor_method = User.TwoFactorMethod.TOTP
        self.superuser.totp_secret = self.secret
        self.superuser.save()

    def start(self, email=None, password=None):
        return self.post(
            self._login_url,
            {'email': email or self.superuser.email, 'password': password or self.superuser.plain_password},
        )


class TestBreakGlassLogin(BreakGlassTestCase):
    def test_password_and_totp_open_a_session_that_serves_the_api(self):
        response = self.start()

        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED)
        challenge_id = response.content_dict['response']['challenge_id']

        response = self.post(self._verify_url, {'challenge_id': challenge_id, 'code': pyotp.TOTP(self.secret).now()})

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotIn('token', response.content_dict['response'])

        # The session cookie alone authenticates; no Authorization header and no API key
        browser = Client()
        browser.force_login(self.superuser, backend='django.contrib.auth.backends.ModelBackend')
        response = browser.get(self._me_url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_wrong_password_is_refused_with_the_same_401_for_unknown_emails(self):
        response = self.start(password='not-the-password')
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        response = self.start(email='nobody@example.com')
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_user_who_is_not_a_superuser_is_refused_after_the_password(self):
        user = UserFixture.create_user(email='regular@example.com')
        user.two_factor_enabled = True
        user.two_factor_method = User.TwoFactorMethod.TOTP
        user.totp_secret = self.secret
        user.save()

        response = self.start(email=user.email, password=user.plain_password)

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_superuser_without_authenticator_is_refused(self):
        self.superuser.two_factor_enabled = False
        self.superuser.save()

        response = self.start()

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_wrong_totp_code_is_refused(self):
        challenge_id = self.start().content_dict['response']['challenge_id']

        response = self.post(self._verify_url, {'challenge_id': challenge_id, 'code': '000000'})

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertFalse(self.client.session.keys())

    def test_repeated_password_failures_lock_the_account_even_for_the_right_password(self):
        for _ in range(5):
            self.start(password='wrong-password')

        response = self.start()

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.superuser.refresh_from_db()
        self.assertGreater(self.superuser.break_glass_locked_until, timezone.now())

    def test_a_verified_login_clears_the_failure_count(self):
        self.start(password='wrong-password')
        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.break_glass_failures, 1)

        challenge_id = self.start().content_dict['response']['challenge_id']
        self.post(self._verify_url, {'challenge_id': challenge_id, 'code': pyotp.TOTP(self.secret).now()})

        self.superuser.refresh_from_db()
        self.assertEqual(self.superuser.break_glass_failures, 0)

    def test_session_logout_ends_the_session(self):
        browser = Client()
        browser.force_login(self.superuser, backend='django.contrib.auth.backends.ModelBackend')

        response = browser.delete(self._session_url)

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(browser.get(self._me_url).status_code, HTTPStatus.UNAUTHORIZED)


class TestSessionCsrf(BreakGlassTestCase):
    def test_unsafe_session_request_without_csrf_token_is_refused(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.superuser, backend='django.contrib.auth.backends.ModelBackend')

        response = browser.post(reverse('user-me'), data='{}', content_type='application/json')

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_config_sets_the_csrf_cookie_the_spa_echoes_back(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.superuser, backend='django.contrib.auth.backends.ModelBackend')
        config = browser.get(reverse('auth-config'))
        self.assertEqual(config.status_code, HTTPStatus.OK)
        token = browser.cookies['csrftoken'].value

        response = browser.delete(self._session_url, HTTP_X_CSRFTOKEN=token)

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
