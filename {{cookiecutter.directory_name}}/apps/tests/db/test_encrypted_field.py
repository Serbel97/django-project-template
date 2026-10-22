"""
Tests for EncryptedField in the database (User.totp_secret), the rotation command and the key check.
"""
import base64
from io import StringIO

from django.core.exceptions import FieldError
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import TestCase, override_settings

from apps.core.checks import encryption_keys_configured
from apps.core.encryption import key_version, parse_keys
from apps.core.models import User
from apps.tests.fixtures import UserFixture

KEY_1 = base64.b64encode(b'0' * 32).decode()  # the test settings' key
KEY_2 = base64.b64encode(b'2' * 32).decode()
SECRET = 'JBSWY3DPEHPK3PXP'


def stored_value(user: User) -> bytes | None:
    with connection.cursor() as cursor:
        cursor.execute('SELECT totp_secret FROM users WHERE id = %s', [user.pk])
        value = cursor.fetchone()[0]
    return None if value is None else bytes(value)


class TestEncryptedField(TestCase):
    def setUp(self):
        self.user = UserFixture.create_user(email='crypto@example.com')

    def test_value_is_encrypted_in_the_database_and_plain_on_the_model(self):
        self.user.totp_secret = SECRET
        self.user.save()

        raw = stored_value(self.user)
        self.assertNotIn(SECRET.encode(), raw)
        self.assertEqual(key_version(raw), 1)
        self.assertEqual(User.objects.get(pk=self.user.pk).totp_secret, SECRET)

    def test_none_is_stored_as_null(self):
        self.assertIsNone(stored_value(self.user))
        self.assertIsNone(User.objects.get(pk=self.user.pk).totp_secret)

    def test_only_isnull_lookups_are_supported(self):
        self.user.totp_secret = SECRET
        self.user.save()

        self.assertTrue(User.objects.filter(totp_secret__isnull=False).exists())
        with self.assertRaises(FieldError):
            User.objects.filter(totp_secret=SECRET).exists()


class TestRotateEncryptionKeys(TestCase):
    def setUp(self):
        self.user = UserFixture.create_user(email='rotate@example.com')
        self.user.totp_secret = SECRET
        self.user.save()

    def rotate(self, *args) -> str:
        out = StringIO()
        call_command('rotate_encryption_keys', *args, stdout=out, stderr=StringIO())
        return out.getvalue()

    @override_settings(AES_FIELD_KEYS=f'2:{KEY_2},1:{KEY_1}')
    def test_old_values_are_re_encrypted_with_the_current_key(self):
        output = self.rotate()

        self.assertIn('core.User.totp_secret: v1: 1; re-encrypted 1 to v2', output)
        self.assertEqual(key_version(stored_value(self.user)), 2)
        self.assertEqual(User.objects.get(pk=self.user.pk).totp_secret, SECRET)

    @override_settings(AES_FIELD_KEYS=f'2:{KEY_2}')
    def test_after_rotation_the_old_key_can_be_dropped(self):
        with override_settings(AES_FIELD_KEYS=f'2:{KEY_2},1:{KEY_1}'):
            self.rotate()

        self.assertEqual(User.objects.get(pk=self.user.pk).totp_secret, SECRET)

    @override_settings(AES_FIELD_KEYS=f'2:{KEY_2},1:{KEY_1}')
    def test_dry_run_reports_without_writing(self):
        output = self.rotate('--dry-run')

        self.assertIn('would re-encrypt 1 to v2', output)
        self.assertEqual(key_version(stored_value(self.user)), 1)

    @override_settings(AES_FIELD_KEYS=f'2:{KEY_2},1:{KEY_1}')
    def test_soft_deleted_rows_are_rotated_too(self):
        self.user.delete()

        self.rotate()

        self.assertEqual(key_version(stored_value(self.user)), 2)

    @override_settings(AES_FIELD_KEYS=f'2:{KEY_2}')
    def test_values_of_a_missing_key_fail_the_command(self):
        with self.assertRaises(CommandError):
            self.rotate()

    def test_generate_key_prints_a_usable_key(self):
        key = self.rotate('--generate-key').strip()

        self.assertEqual(parse_keys(f'1:{key}', None).current_version, 1)


class TestEncryptionKeyCheck(TestCase):
    @override_settings(AES_FIELD_KEYS='')
    def test_missing_keys_are_an_error(self):
        self.assertEqual([error.id for error in encryption_keys_configured(None)], ['core.E002'])

    @override_settings(AES_FIELD_KEYS=f'1:{KEY_1}', AES_FIELD_KEY_VERSION='3')
    def test_unknown_current_version_is_an_error(self):
        self.assertEqual([error.id for error in encryption_keys_configured(None)], ['core.E002'])

    def test_valid_keys_pass(self):
        self.assertEqual(encryption_keys_configured(None), [])
