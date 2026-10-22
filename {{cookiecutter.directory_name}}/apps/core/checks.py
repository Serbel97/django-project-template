from django.conf import settings
from django.core.checks import Error, Tags, register
from django.core.exceptions import ImproperlyConfigured

from apps.core.encryption import parse_keys


@register(Tags.security)
def registration_needs_password_reset(app_configs, **kwargs):
    """Registration e-mails the recovery link, so it only works with the password reset routes."""
    if settings.AUTH_REGISTRATION_ENABLED and not settings.AUTH_PASSWORD_RESET_ENABLED:
        return [
            Error(
                'AUTH_REGISTRATION_ENABLED needs AUTH_PASSWORD_RESET_ENABLED.',
                hint='Self-registration sends a recovery link to set the first password.',
                id='core.E001',
            )
        ]

    return []


@register(Tags.security)
def encryption_keys_configured(app_configs, **kwargs):
    """Encrypted fields need a valid AES_FIELD_KEYS, or every row holding one fails to load."""
    from apps.core.fields import encrypted_fields

    if not encrypted_fields():
        return []

    try:
        parse_keys(settings.AES_FIELD_KEYS, settings.AES_FIELD_KEY_VERSION)
    except ImproperlyConfigured as error:
        return [
            Error(
                str(error),
                hint='Set AES_FIELD_KEYS=<version>:<base64 32-byte key>; '
                'python manage.py rotate_encryption_keys --generate-key prints a new key.',
                id='core.E002',
            )
        ]

    return []
