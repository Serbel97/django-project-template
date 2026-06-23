from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models.base import BaseModel


class ApiKey(BaseModel):
    class Meta:
        app_label = 'core'
        db_table = 'api_keys'
        default_permissions = ()
        verbose_name = _('api_key')
        verbose_name_plural = _('api_keys')

    class DevicePlatform(models.TextChoices):
        WEB = 'web', _('web')
        ANDROID = 'android', _('android')
        IOS = 'ios', _('ios')
        DEBUG = 'debug', _('debug')

    name = models.CharField(max_length=200, null=True, verbose_name=_('apikey_name'))
    platform = models.CharField(
        max_length=10,
        null=False,
        choices=DevicePlatform.choices,
        default=DevicePlatform.DEBUG,
        db_default=DevicePlatform.DEBUG,
        verbose_name=_('apikey_platform')
    )
    secret = models.CharField(max_length=30, null=False, verbose_name=_('apikey_secret'))
    is_active = models.BooleanField(default=False, db_default=False, verbose_name=_('apikey_is_active'))


__all__ = [
    'ApiKey'
]
