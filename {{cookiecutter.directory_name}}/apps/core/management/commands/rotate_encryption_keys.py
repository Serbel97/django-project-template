"""
Re-encrypt every encrypted model field with the current key version.

Rotation: add the new key under a new version (``AES_FIELD_KEYS=2:<new>,1:<old>``), deploy, run this
command, check ``--dry-run`` reports no value left on the old version, then drop the old key.
"""

from collections import Counter

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.core.encryption import DecryptionError, generate_key, get_keyring, key_version
from apps.core.fields import encrypted_fields


class Command(BaseCommand):
    help = 'Re-encrypt encrypted model fields with the current key version (AES_FIELD_KEY_VERSION).'

    # --generate-key must work before any key exists, which the core.E002 check would refuse.
    requires_system_checks: list[str] = []

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Only report how many values use each version.')
        parser.add_argument('--generate-key', action='store_true', help='Print a new random key and exit.')

    def handle(self, *args, **options):
        if options['generate_key']:
            self.stdout.write(generate_key())
            return

        try:
            keyring = get_keyring()
        except ImproperlyConfigured as error:
            raise CommandError(str(error)) from error

        quote = connection.ops.quote_name
        failures = 0

        for model, field in encrypted_fields():
            # Raw rows: the version sits in the stored header, which the field hides once decrypted.
            with connection.cursor() as cursor:
                cursor.execute(
                    f'SELECT {quote(model._meta.pk.column)}, {quote(field.column)} '
                    f'FROM {quote(model._meta.db_table)} WHERE {quote(field.column)} IS NOT NULL'
                )
                rows = cursor.fetchall()

            versions: Counter = Counter()
            rotated = 0

            for pk, raw in rows:
                token = bytes(raw)
                try:
                    version = key_version(token)
                    versions[version] += 1
                    if version == keyring.current_version or options['dry_run']:
                        continue
                    plaintext = keyring.decrypt(token)
                except DecryptionError as error:
                    failures += 1
                    self.stderr.write(f'{model._meta.label}.{field.name} pk={pk}: {error}')
                    continue

                # Base manager: soft-deleted rows hold secrets too. update() re-encrypts with the current key.
                with transaction.atomic():
                    model._base_manager.filter(pk=pk).update(**{field.attname: plaintext})
                rotated += 1

            summary = ', '.join(f'v{version}: {count}' for version, count in sorted(versions.items())) or 'no values'
            action = 'would re-encrypt' if options['dry_run'] else 're-encrypted'
            pending = sum(count for version, count in versions.items() if version != keyring.current_version)
            self.stdout.write(
                f'{model._meta.label}.{field.name}: {summary}; '
                f'{action} {pending if options["dry_run"] else rotated} to v{keyring.current_version}'
            )

        if failures:
            raise CommandError(f'{failures} value(s) could not be decrypted with the configured keys.')
