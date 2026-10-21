from http import HTTPStatus

from django.contrib.auth import logout

from apps.api.errors import ValidationException
from apps.api.forms.break_glass import BreakGlassForm
from apps.api.response import SingleResponse
from apps.api.views.base import SecuredView
from apps.core.serializers.auth import AuthSerializer
from apps.core.serializers.user import UserSerializer
from apps.core.services.auth import BreakGlassService


class BreakGlassLogin(SecuredView):
    # Called by the SPA before anyone is logged in: no API key. SecuredView enforces CSRF on these instead.
    EXEMPT_API_KEY = ['POST']
    EXEMPT_AUTH = ['POST']

    # Deliberately not @transaction.atomic: the failure counter of a refused attempt must survive.
    def post(self, request):
        """Start a break-glass login with email and password; answers with a TOTP challenge."""
        form = BreakGlassForm.Login.create_from_request(request)

        if not form.is_valid():
            raise ValidationException(form)

        challenge = BreakGlassService.start(form.cleaned_data['email'], form.cleaned_data['password'])

        return SingleResponse(
            request,
            data={'challenge_id': challenge.pk, 'method': challenge.method, 'expires_at': challenge.expires_at},
            serializer=AuthSerializer.TwoFactorRequired,
            status=HTTPStatus.ACCEPTED,
        )


class BreakGlassVerify(SecuredView):
    EXEMPT_API_KEY = ['POST']
    EXEMPT_AUTH = ['POST']

    # Deliberately not @transaction.atomic: the attempt counter and the lockout must survive a refusal.
    def post(self, request):
        """Complete the break-glass login with a TOTP or backup code; opens a Django session."""
        form = BreakGlassForm.Verify.create_from_request(request)

        if not form.is_valid():
            raise ValidationException(form)

        user = BreakGlassService.verify(request, form.cleaned_data['challenge_id'], form.cleaned_data['code'])

        return SingleResponse(request, data=user, serializer=UserSerializer.Me)


class SessionLogout(SecuredView):
    """End the browser session. Bearer tokens are ended with DELETE /token instead."""

    def delete(self, request):
        logout(request)

        return SingleResponse(request)
