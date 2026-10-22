"""
Tests for the versioned AES-256-GCM keyring behind EncryptedField.
"""
import base64

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from apps.core.encryption import DecryptionError, generate_key, key_version, parse_keys

KEY_1 = base64.b64encode(b'1' * 32).decode()
KEY_2 = base64.b64encode(b'2' * 32).decode()


class TestKeyring(SimpleTestCase):
    def test_round_trip(self):
        keyring = parse_keys(f'1:{KEY_1}', None)

        self.assertEqual(keyring.decrypt(keyring.encrypt('JBSWY3DPEHPK3PXP')), 'JBSWY3DPEHPK3PXP')

    def test_every_encryption_uses_a_fresh_nonce(self):
        keyring = parse_keys(f'1:{KEY_1}', None)

        self.assertNotEqual(keyring.encrypt('same'), keyring.encrypt('same'))

    def test_plaintext_does_not_appear_in_the_stored_value(self):
        keyring = parse_keys(f'1:{KEY_1}', None)

        self.assertNotIn(b'JBSWY3DPEHPK3PXP', keyring.encrypt('JBSWY3DPEHPK3PXP'))

    def test_altered_ciphertext_is_refused(self):
        keyring = parse_keys(f'1:{KEY_1}', None)
        token = bytearray(keyring.encrypt('secret'))
        token[-1] ^= 1

        with self.assertRaises(DecryptionError):
            keyring.decrypt(bytes(token))

    def test_altered_key_version_header_is_refused(self):
        keyring = parse_keys(f'2:{KEY_2},1:{KEY_1}', '1')
        token = bytearray(keyring.encrypt('secret'))
        token[2] = 2  # claim version 2 for a value encrypted with version 1

        with self.assertRaises(DecryptionError):
            keyring.decrypt(bytes(token))

    def test_wrong_key_for_the_version_is_refused(self):
        token = parse_keys(f'1:{KEY_1}', None).encrypt('secret')

        with self.assertRaises(DecryptionError):
            parse_keys(f'1:{KEY_2}', None).decrypt(token)

    def test_unknown_key_version_is_refused(self):
        token = parse_keys(f'2:{KEY_2}', None).encrypt('secret')

        with self.assertRaises(DecryptionError):
            parse_keys(f'1:{KEY_1}', None).decrypt(token)

    def test_garbage_is_refused(self):
        with self.assertRaises(DecryptionError):
            parse_keys(f'1:{KEY_1}', None).decrypt(b'short')


class TestRotation(SimpleTestCase):
    def test_new_values_use_the_highest_version_by_default(self):
        keyring = parse_keys(f'1:{KEY_1},2:{KEY_2}', None)

        self.assertEqual(keyring.current_version, 2)
        self.assertEqual(key_version(keyring.encrypt('secret')), 2)

    def test_explicit_current_version_wins(self):
        keyring = parse_keys(f'1:{KEY_1},2:{KEY_2}', '1')

        self.assertEqual(key_version(keyring.encrypt('secret')), 1)

    def test_values_of_the_old_key_still_decrypt_after_a_new_key_is_added(self):
        old = parse_keys(f'1:{KEY_1}', None).encrypt('secret')

        rotated = parse_keys(f'2:{KEY_2},1:{KEY_1}', None)

        self.assertEqual(rotated.decrypt(old), 'secret')


class TestConfiguration(SimpleTestCase):
    def assertConfigError(self, raw, current=None):
        with self.assertRaises(ImproperlyConfigured):
            parse_keys(raw, current)

    def test_missing_keys(self):
        self.assertConfigError('')

    def test_entry_without_version(self):
        self.assertConfigError(KEY_1)

    def test_version_out_of_range(self):
        self.assertConfigError(f'0:{KEY_1}')
        self.assertConfigError(f'70000:{KEY_1}')

    def test_duplicate_version(self):
        self.assertConfigError(f'1:{KEY_1},1:{KEY_2}')

    def test_invalid_base64(self):
        self.assertConfigError('1:not-base64!!')

    def test_key_of_the_wrong_length(self):
        self.assertConfigError(f'1:{base64.b64encode(b"short").decode()}')

    def test_current_version_not_listed(self):
        self.assertConfigError(f'1:{KEY_1}', '2')

    def test_generated_keys_are_valid(self):
        self.assertEqual(parse_keys(f'1:{generate_key()}', None).current_version, 1)
