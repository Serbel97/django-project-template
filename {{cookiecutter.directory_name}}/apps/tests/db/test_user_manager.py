"""
Tests for UserManager (create_user / create_superuser / get_by_natural_key).
"""
from django.test import TestCase

from apps.core.models import User


class TestUserManager(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email='manager@example.com', name='Man', surname='Ager', password='Secret123!'
        )

        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('Secret123!'))

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='root@example.com', name='Root', surname='Admin', password='Secret123!'
        )

        self.assertTrue(user.is_superuser)

    def test_get_by_natural_key_is_case_insensitive(self):
        user = User.objects.create_user(
            email='Mixed@Example.com', name='Mixed', surname='Case', password='Secret123!'
        )

        self.assertEqual(User.objects.get_by_natural_key('mixed@example.com'), user)
