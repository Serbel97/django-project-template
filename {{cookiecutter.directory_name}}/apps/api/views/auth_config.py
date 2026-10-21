from django.conf import settings
from django.middleware.csrf import get_token

from apps.api.response import SingleResponse
from apps.api.views.base import SecuredView
from apps.core.serializers.auth import AuthSerializer


class AuthConfig(SecuredView):
    """Which login paths are switched on, so the SPA renders only those. Answered before anyone logs in."""

    # Safe method, no secret to check: the SPA reads it before it has an API key of its own.
    EXEMPT_API_KEY = ['GET']
    EXEMPT_AUTH = ['GET']

    def get(self, request):
        # Sets the CSRF cookie the SPA echoes back in X-CSRFToken on its first unsafe request.
        get_token(request)

        return SingleResponse(
            request,
            data={
                'break_glass_enabled': settings.BREAK_GLASS_ENABLED,
                'password_reset_enabled': settings.AUTH_PASSWORD_RESET_ENABLED,
                'registration_enabled': settings.AUTH_REGISTRATION_ENABLED,
            },
            serializer=AuthSerializer.Config,
        )
