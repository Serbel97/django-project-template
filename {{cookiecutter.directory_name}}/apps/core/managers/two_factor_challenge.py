from django.utils import timezone

from apps.core.managers.base import BaseManager


class TwoFactorChallengeManager(BaseManager):
    def valid(self):
        """Challenges that are neither expired nor already answered."""
        return self.get_queryset().filter(expires_at__gt=timezone.now(), verified_at__isnull=True)
