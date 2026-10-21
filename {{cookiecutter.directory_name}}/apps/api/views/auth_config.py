from django.conf import settings

from apps.api.response import SingleResponse
from apps.api.views.base import SecuredView
from apps.core.serializers.auth import AuthSerializer


class AuthConfig(SecuredView):
    """Which login paths are switched on, so the SPA renders only those. Answered before anyone logs in."""

    EXEMPT_API_KEY = ['GET']
    EXEMPT_AUTH = ['GET']

    def get(self, request):
        return SingleResponse(
            request,
            data={
                'password_login_enabled': settings.PASSWORD_LOGIN_ENABLED,
                'password_reset_enabled': settings.AUTH_PASSWORD_RESET_ENABLED,
                'registration_enabled': settings.AUTH_REGISTRATION_ENABLED,
            },
            serializer=AuthSerializer.Config,
        )
