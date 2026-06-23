from django.urls import path

from apps.api.views import status, user, token, recovery_code

urlpatterns = [
    # Authentication
    path('token', token.TokenManagement.as_view(), name='token'),

    # User
    path('users', user.UserManagement.as_view(), name='user-management'),
    path('users/me', user.UserMe.as_view(), name='user-me'),
    path('users/<uuid:user_id>', user.UserDetail.as_view(), name='user-detail'),
    path('users/<uuid:user_id>/password', user.ChangePasswordDetail.as_view(), name='change-password'),

    # Recovery Code
    path('recovery_code', recovery_code.RecoveryCodeManagement.as_view(), name='recovery-code'),
    path('recovery_code/<uuid:recovery_code_id>', recovery_code.RecoveryCodeDetail.as_view(), name='recovery-code-id'),

    # Status
    path("status", status.StatusManagement.as_view(), name='status'),
]
