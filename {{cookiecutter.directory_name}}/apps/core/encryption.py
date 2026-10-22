"""
Application-level encryption of model fields with versioned keys (AES-256-GCM).

Keys come from ``AES_FIELD_KEYS``: comma-separated ``<version>:<base64 key>`` pairs, e.g.
``AES_FIELD_KEYS=2:<new key>,1:<old key>``. New values are encrypted with ``AES_FIELD_KEY_VERSION``
(the highest version when unset); any listed version still decrypts, so a key can be rotated without
downtime and old values re-encrypted afterwards with ``manage.py rotate_encryption_keys``.

Stored layout (``bytea``)::

    format (1 byte) | key version (2 bytes, big-endian) | nonce (12 bytes) | ciphertext + GCM tag

The format byte and the key version are authenticated as associated data, so a value whose header or
ciphertext was altered in the database fails to decrypt instead of decrypting to something else.

The configuration is parsed on first use, never at import: ``makemigrations`` and friends work without
keys, and the system check ``core.E002`` reports a missing or broken configuration.
"""

import base64
import binascii
import os
import struct
from dataclasses import dataclass
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

FORMAT_V1 = 1
HEADER = struct.Struct('>BH')
NONCE_LENGTH = 12
KEY_LENGTH = 32
MAX_VERSION = 0xFFFF


class DecryptionError(Exception):
    """A stored value could not be decrypted: unknown key version, wrong key or tampered data."""


@dataclass(frozen=True)
class Keyring:
    keys: dict[int, AESGCM]
    current_version: int

    def encrypt(self, plaintext: str) -> bytes:
        header = HEADER.pack(FORMAT_V1, self.current_version)
        nonce = os.urandom(NONCE_LENGTH)
        return header + nonce + self.keys[self.current_version].encrypt(nonce, plaintext.encode('utf-8'), header)

    def decrypt(self, token: bytes) -> str:
        version = key_version(token)
        if version not in self.keys:
            raise DecryptionError(f'No key with version {version} in AES_FIELD_KEYS.')

        header, nonce = token[: HEADER.size], token[HEADER.size : HEADER.size + NONCE_LENGTH]
        try:
            plaintext = self.keys[version].decrypt(nonce, token[HEADER.size + NONCE_LENGTH :], header)
        except InvalidTag as error:
            raise DecryptionError(
                f'Value does not decrypt with key version {version} (wrong key or altered).'
            ) from error

        return plaintext.decode('utf-8')


def key_version(token: bytes) -> int:
    """The key version a stored value was encrypted with."""
    if len(token) < HEADER.size + NONCE_LENGTH:
        raise DecryptionError('Value is too short to be an encrypted field value.')

    value_format, version = HEADER.unpack_from(token)
    if value_format != FORMAT_V1:
        raise DecryptionError(f'Unknown encrypted value format {value_format}.')

    return version


def parse_keys(raw: str, current: str | None) -> Keyring:
    """Parse ``AES_FIELD_KEYS`` / ``AES_FIELD_KEY_VERSION``; raises ImproperlyConfigured with the reason."""
    keys: dict[int, AESGCM] = {}

    for item in (raw or '').split(','):
        item = item.strip()
        if not item:
            continue

        version_text, separator, key_text = item.partition(':')
        if not separator or not version_text.strip().isdigit():
            raise ImproperlyConfigured('AES_FIELD_KEYS entries must look like <version>:<base64 key>.')

        version = int(version_text)
        if not 1 <= version <= MAX_VERSION:
            raise ImproperlyConfigured(f'AES_FIELD_KEYS versions must be between 1 and {MAX_VERSION}.')
        if version in keys:
            raise ImproperlyConfigured(f'AES_FIELD_KEYS lists version {version} twice.')

        try:
            key = base64.b64decode(key_text.strip(), validate=True)
        except (binascii.Error, ValueError) as error:
            raise ImproperlyConfigured(f'AES_FIELD_KEYS version {version} is not valid base64.') from error
        if len(key) != KEY_LENGTH:
            raise ImproperlyConfigured(f'AES_FIELD_KEYS version {version} must be {KEY_LENGTH} bytes (AES-256).')

        keys[version] = AESGCM(key)

    if not keys:
        raise ImproperlyConfigured('AES_FIELD_KEYS is not set.')

    if current in (None, ''):
        return Keyring(keys=keys, current_version=max(keys))

    if not str(current).strip().isdigit() or int(current) not in keys:
        raise ImproperlyConfigured('AES_FIELD_KEY_VERSION must name a version listed in AES_FIELD_KEYS.')

    return Keyring(keys=keys, current_version=int(current))


@lru_cache(maxsize=8)
def _cached_keyring(raw: str, current: str | None) -> Keyring:
    return parse_keys(raw, current)


def get_keyring() -> Keyring:
    """The configured keyring; cached per configuration value, so tests can override the settings."""
    current = getattr(settings, 'AES_FIELD_KEY_VERSION', None)
    return _cached_keyring(getattr(settings, 'AES_FIELD_KEYS', ''), None if current is None else str(current))


def generate_key() -> str:
    """A new random key, base64-encoded, ready for ``AES_FIELD_KEYS``."""
    return base64.b64encode(os.urandom(KEY_LENGTH)).decode('ascii')


__all__ = ['DecryptionError', 'Keyring', 'generate_key', 'get_keyring', 'key_version', 'parse_keys']
