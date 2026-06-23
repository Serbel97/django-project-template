"""
Tests for TokenManager.create — expiry is computed at creation time from
settings.TOKEN_EXPIRATION.
"""
from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Token
from apps.tests.fixtures import UserFixture


class TestTokenManager(TestCase):
    def test_create_sets_expiration_from_settings(self):
        user = UserFixture.create_user(email='token@example.com')

        before = timezone.now()
        token = Token.objects.create(user=user)
        after = timezone.now()

        self.assertGreaterEqual(token.expires_at, before + settings.TOKEN_EXPIRATION - timedelta(seconds=5))
        self.assertLessEqual(token.expires_at, after + settings.TOKEN_EXPIRATION + timedelta(seconds=5))

    def test_explicit_expiration_is_respected(self):
        user = UserFixture.create_user(email='token2@example.com')
        explicit = timezone.now() + timedelta(days=1)

        token = Token.objects.create(user=user, expires_at=explicit)

        self.assertEqual(token.expires_at, explicit)
