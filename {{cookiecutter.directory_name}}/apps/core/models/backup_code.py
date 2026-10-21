from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models.base import BaseModel
from apps.core.models.user import User


class BackupCode(BaseModel):
    """One single-use recovery code for the second factor. Only the hash is stored."""

    class Meta:
        app_label = 'core'
        db_table = 'backup_codes'
        default_permissions = ()

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='backup_codes', verbose_name=_('User'))
    code_hash = models.CharField(null=False, max_length=128, verbose_name=_('Code hash'))
    used_at = models.DateTimeField(null=True, verbose_name=_('Used at'))


__all__ = ['BackupCode']
