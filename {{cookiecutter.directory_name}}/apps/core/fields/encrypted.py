from django.apps import apps
from django.db import models

from apps.core.encryption import get_keyring


class EncryptedField(models.Field):
    """
    Text encrypted at rest with AES-256-GCM and a versioned key (see ``apps.core.encryption``).

    The model sees plain text; the column holds ``bytea``. Every write uses a fresh nonce, so the stored
    value cannot be searched: only ``isnull`` lookups are supported. A value that does not decrypt (unknown
    key version, wrong key, altered data) raises ``DecryptionError`` when the row is loaded.
    """

    description = 'Text encrypted with AES-256-GCM'

    def get_internal_type(self):
        return 'BinaryField'

    def get_lookup(self, lookup_name):
        # Equality and friends would compare against a freshly encrypted value and never match.
        return super().get_lookup(lookup_name) if lookup_name == 'isnull' else None

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return None
        return get_keyring().encrypt(str(value))

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return get_keyring().decrypt(bytes(value))

    def to_python(self, value):
        if value is None or isinstance(value, str):
            return value
        return get_keyring().decrypt(bytes(value))


def encrypted_fields() -> list[tuple[type[models.Model], EncryptedField]]:
    """Every concrete ``EncryptedField`` of the installed models, with its model."""
    return [
        (model, field)
        for model in apps.get_models()
        if not model._meta.proxy and model._meta.managed
        for field in model._meta.concrete_fields
        if isinstance(field, EncryptedField)
    ]
