from django.conf import settings
from django.urls import path

from apps.api.views import status, user, token, recovery_code, auth_config, two_factor

urlpatterns = [
    path('auth/config', auth_config.AuthConfig.as_view(), name='auth-config'),

    # User
    path('users', user.UserManagement.as_view(), name='user-management'),
    path('users/me', user.UserMe.as_view(), name='user-me'),
    path('users/<uuid:user_id>', user.UserDetail.as_view(), name='user-detail'),

    # Status
    path("status", status.StatusManagement.as_view(), name='status'),
]

# Password login and its second factor (IP-003 Q6). Absent while PASSWORD_LOGIN_ENABLED is off.
if settings.PASSWORD_LOGIN_ENABLED:
    urlpatterns += [
        path('token', token.TokenManagement.as_view(), name='token'),

        path('auth/2fa', two_factor.TwoFactorManagement.as_view(), name='two-factor'),
        path('auth/2fa/confirm', two_factor.TwoFactorConfirm.as_view(), name='two-factor-confirm'),
        path('auth/2fa/verify', two_factor.TwoFactorVerify.as_view(), name='two-factor-verify'),
        path('auth/2fa/backup_codes', two_factor.BackupCodeManagement.as_view(), name='two-factor-backup-codes'),
    ]

# Password recovery (IP-003 Q6). Absent while AUTH_PASSWORD_RESET_ENABLED is off.
if settings.AUTH_PASSWORD_RESET_ENABLED:
    urlpatterns += [
        path('users/<uuid:user_id>/password', user.ChangePasswordDetail.as_view(), name='change-password'),

        path('recovery_code', recovery_code.RecoveryCodeManagement.as_view(), name='recovery-code'),
        path(
            'recovery_code/<uuid:recovery_code_id>',
            recovery_code.RecoveryCodeDetail.as_view(),
            name='recovery-code-id',
        ),
    ]
