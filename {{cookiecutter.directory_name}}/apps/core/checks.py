from django.conf import settings
from django.core.checks import Error, Tags, register


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
