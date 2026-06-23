"""
Tests for the token endpoint (POST /api/v1/token) — login / token creation.
"""
from http import HTTPStatus

from django.urls import reverse

from apps.core.models import Token
from apps.tests.base import Base
from apps.tests.fixtures import UserFixture


class TestAuthentication(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._token_url = reverse('token')

    def setUp(self):
        super().setUp()
        self.user = UserFixture.create_user(email='auth_test@example.com', password='SecurePassword123!')

    def test_successful_token_creation(self):
        """Valid credentials return 201 with a token and persist it."""
        response = self.post(self._token_url, {'email': self.user.email, 'password': self.user.plain_password})

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertIn('token', response.content_dict['response'])
        token_id = response.content_dict['response']['token']
        self.assertTrue(Token.objects.filter(pk=token_id, user=self.user).exists())

    def test_fails_with_incorrect_password(self):
        response = self.post(self._token_url, {'email': self.user.email, 'password': 'WrongPassword123!'})

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_fails_with_nonexistent_email(self):
        response = self.post(self._token_url, {'email': 'nobody@example.com', 'password': 'SecurePassword123!'})

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_fails_when_user_inactive(self):
        inactive = UserFixture.create_inactive_user()
        response = self.post(self._token_url, {'email': inactive.email, 'password': inactive.plain_password})

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_fails_with_missing_fields(self):
        response = self.post(self._token_url, {'email': self.user.email})

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)

    def test_fails_without_api_key(self):
        """Even the login endpoint requires a valid X-Apikey header."""
        response = self.client.post(
            self._token_url,
            data='{}',
            content_type='application/json',
            headers={'Accept': 'application/json'},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
