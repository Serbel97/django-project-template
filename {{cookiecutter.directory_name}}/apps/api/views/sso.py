from http import HTTPStatus

from django.contrib.auth import BACKEND_SESSION_KEY, get_user, logout
from django.db import transaction
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.translation import gettext as _

from apps.api.errors import ProblemDetailException, UnauthorizedException
from apps.api.response import SingleResponse
from apps.api.views.base import SecuredView
from apps.core.models import Token
from apps.core.serializers.token import TokenSerializer

# Backend allauth records in the session of an SSO login (settings.AUTHENTICATION_BACKENDS)
SSO_SESSION_BACKEND = 'apps.core.auth.SSOSessionBackend'


class SSOTokenExchange(SecuredView):
    """
    Swap the session an SSO login opened for a Bearer token (IP-003).

    allauth ends the login with a session cookie; every other endpoint authenticates with Bearer, so the
    SPA calls this once after the IdP redirect and the session is ended here.
    """

    EXEMPT_AUTH = ['POST']

    @transaction.atomic
    def post(self, request):
        # The session cookie authenticates this one call, so it must carry the CSRF token as well.
        if CsrfViewMiddleware(lambda req: None).process_view(request, None, (), {}) is not None:
            raise ProblemDetailException(_('CSRF verification failed.'), status=HTTPStatus.FORBIDDEN)

        # SecuredView replaced request.user (no Authorization header); the session still holds the SSO user.
        user = get_user(request)
        if not user.is_authenticated or request.session.get(BACKEND_SESSION_KEY) != SSO_SESSION_BACKEND:
            raise UnauthorizedException(detail=_('No single sign-on session.'))

        token = Token.objects.create(user=user)
        logout(request)

        return SingleResponse(request, data=token, serializer=TokenSerializer.Base, status=HTTPStatus.CREATED)
