from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils.translation import gettext as _
from django.db import models

from apps.core.managers.user import UserManager

from apps.core.models.base import BaseModel


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    class Meta:
        app_label = 'core'
        db_table = 'users'
        default_permissions = ('add', 'change', 'delete', 'view')

    # Whitelist of columns clients may sort by via ``?order_by=`` (see apps.api.response.Ordering)
    ORDERING_FIELDS = ('created_at', 'updated_at', 'email', 'name', 'surname', 'last_login')

    # Basic info
    email = models.EmailField(null=False, unique=True, verbose_name=_('user_email'))
    name = models.CharField(null=False, max_length=30, verbose_name=_('user_name'))
    surname = models.CharField(null=False, max_length=150, verbose_name=_('user_surname'))
    is_active = models.BooleanField(null=False, default=True, db_default=True, verbose_name=_('user_is_active'))
    # Grants access to the Django admin (see apps/core/admin.py).
    is_staff = models.BooleanField(null=False, default=False, db_default=False, verbose_name=_('user_is_staff'))

    objects = UserManager()
    all_objects = UserManager(alive_only=False)

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'surname']

    def get_full_name(self) -> str:
        return f'{self.name} {self.surname}'


__all__ = [
    'User'
]
