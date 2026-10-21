"""
Tests for the SSO routes (IP-003): the session-to-Bearer swap and allauth's headless config.
"""
from http import HTTPStatus

from django.contrib.auth import SESSION_KEY
from django.test import Client
from django.urls import reverse

from apps.core.models import Token
from apps.tests.base import Base
from apps.tests.fixtures import UserFixture

SSO_BACKEND = 'apps.core.auth.SSOSessionBackend'


class TestSSOTokenExchange(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._url = reverse('sso-token')

    def setUp(self):
        super().setUp()
        self.user = UserFixture.create_user(email='sso@example.com')

    def test_sso_session_is_swapped_for_a_bearer_token_and_ended(self):
        self.client.force_login(self.user, backend=SSO_BACKEND)

        response = self.post(self._url)

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        token = response.content_dict['response']['token']
        self.assertTrue(Token.objects.filter(pk=token, user=self.user).exists())
        self.assertNotIn(SESSION_KEY, self.client.session)

        # The token works like one from /token
        response = self.get(reverse('user-me'), headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_the_session_is_single_use(self):
        self.client.force_login(self.user, backend=SSO_BACKEND)
        self.post(self._url)

        response = self.post(self._url)

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_without_a_session_it_is_refused(self):
        response = self.post(self._url)

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_a_session_not_opened_by_sso_is_refused(self):
        self.client.force_login(self.user, backend='django.contrib.auth.backends.ModelBackend')

        response = self.post(self._url)

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_an_inactive_user_gets_no_token(self):
        self.client.force_login(self.user, backend=SSO_BACKEND)
        self.user.is_active = False
        self.user.save()

        response = self.post(self._url)

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_the_csrf_token_is_required(self):
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.user, backend=SSO_BACKEND)

        response = browser.post(
            self._url, data='', content_type='application/json', headers=self._headers('', self._url, None)
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertFalse(Token.objects.filter(user=self.user).exists())


class TestHeadlessConfig(Base):
    def test_allauth_lists_the_configured_provider(self):
        response = self.client.get('/_allauth/browser/v1/config')

        self.assertEqual(response.status_code, HTTPStatus.OK)
        providers = response.json()['data']['socialaccount']['providers']
        self.assertEqual([provider['id'] for provider in providers], ['test-idp'])
