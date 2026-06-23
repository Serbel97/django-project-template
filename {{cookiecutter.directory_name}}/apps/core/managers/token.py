from django.conf import settings
from django.utils import timezone

from apps.core.managers.base import BaseManager


class TokenManager(BaseManager):
    def create(self, **kwargs):
        # Compute the expiration at creation time so changes to settings.TOKEN_EXPIRATION
        # take effect immediately without requiring a new migration.
        kwargs.setdefault('expires_at', timezone.now() + settings.TOKEN_EXPIRATION)
        return super().create(**kwargs)
