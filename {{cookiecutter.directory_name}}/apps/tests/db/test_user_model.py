"""
Tests for User email normalization and case-insensitive uniqueness.
"""
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.core.models import User


class TestUserEmailNormalization(TestCase):
    def test_save_strips_and_lowercases_email(self):
        user = User(email='  Mixed@Example.COM ', name='Mixed', surname='Case')
        user.set_unusable_password()
        user.save()
        user.refresh_from_db()

        self.assertEqual(user.email, 'mixed@example.com')

    def test_case_variant_email_violates_unique_constraint(self):
        User.objects.create_user(
            email='erik@mail.com', name='Erik', surname='B', password='Secret123!'
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                # Bypass manager/model normalization to prove the DB rejects it.
                User.objects.bulk_create([
                    User(email='Erik@mail.com', name='Erik', surname='B'),
                ])

    def test_get_by_natural_key_is_case_insensitive(self):
        user = User.objects.create_user(
            email='natural@example.com', name='Nat', surname='Key', password='Secret123!'
        )

        self.assertEqual(User.objects.get_by_natural_key('NATURAL@Example.com'), user)
