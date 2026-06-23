"""
Tests for the token endpoint (DELETE /api/v1/token) — logout / token deletion.
"""
from http import HTTPStatus

from django.urls import reverse

from apps.core.models import Token
from apps.tests.base import Base
from apps.tests.fixtures import UserFixture


class TestLogout(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._token_url = reverse('token')

    def setUp(self):
        super().setUp()
        self.user = UserFixture.create_user(email='logout_test@example.com')

    def test_successful_logout(self):
        """A valid Bearer token is deleted and the endpoint returns 204."""
        auth = self.authenticate(self.user)
        token_id = auth['Authorization'].split(' ')[1]

        response = self.delete(self._token_url, headers=auth)

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(Token.objects.filter(pk=token_id).exists())

    def test_logout_without_token(self):
        response = self.delete(self._token_url)

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_logout_with_invalid_token(self):
        response = self.delete(
            self._token_url,
            headers={'Authorization': 'Bearer 00000000-0000-0000-0000-000000000000'},
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
