from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security, deploy=True)
def break_glass_in_production(app_configs, **kwargs):
    """Warn on every deploy while the emergency password login is switched on in production."""
    if settings.BREAK_GLASS_ENABLED and settings.DEPLOYMENT_ENVIRONMENT == 'prod':
        return [
            Warning(
                'BREAK_GLASS_ENABLED is on in production.',
                hint='Switch it off unless an emergency login is needed, then restart the service.',
                id='core.W001',
            )
        ]

    return []


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
