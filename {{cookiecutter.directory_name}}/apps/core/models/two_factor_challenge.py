from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.managers.two_factor_challenge import TwoFactorChallengeManager
from apps.core.models.base import BaseModel
from apps.core.models.user import User


class TwoFactorChallenge(BaseModel):
    """
    A second factor awaiting proof, opened once the first factor succeeded.

    The challenge id is handed to the client and is the only thing tying the eventual
    verify call back to the half-authenticated user — no token exists yet.
    """

    class Meta:
        app_label = 'core'
        db_table = 'two_factor_challenges'
        default_permissions = ()

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='two_factor_challenges',
        verbose_name=_('User'),
    )
    # Salted hash of the e-mail one-time code; NULL for TOTP challenges, which are checked against the secret.
    code_hash = models.CharField(null=True, max_length=128, verbose_name=_('Code hash'))
    method = models.CharField(
        null=False, max_length=10, choices=User.TwoFactorMethod.choices, verbose_name=_('Method')
    )
    expires_at = models.DateTimeField(null=False, verbose_name=_('Expires at'))
    verified_at = models.DateTimeField(null=True, verbose_name=_('Verified at'))
    attempts = models.PositiveSmallIntegerField(null=False, default=0, verbose_name=_('Attempts'))

    objects = TwoFactorChallengeManager()
    all_objects = TwoFactorChallengeManager(alive_only=False)

    def __repr__(self):
        return f"<TwoFactorChallenge {self.pk} ({self.method})>"

    __str__ = __repr__


__all__ = ['TwoFactorChallenge']
