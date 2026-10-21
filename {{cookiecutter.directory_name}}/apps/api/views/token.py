from http import HTTPStatus

from django.contrib.auth import authenticate
from django.db import transaction

from apps.api.errors import UnauthorizedException
from apps.api.errors import ValidationException
from apps.api.forms.token import TokenForm
from apps.api.response import SingleResponse
from apps.api.views.base import SecuredView
from apps.core.models import Token
from apps.core.serializers.auth import AuthSerializer
from apps.core.serializers.token import TokenSerializer
from apps.core.services.auth import TwoFactorService


class TokenManagement(SecuredView):
    EXEMPT_AUTH = ['POST']

    @transaction.atomic
    def post(self, request):
        form = TokenForm.Basic.create_from_request(request)

        if not form.is_valid():
            raise ValidationException(form)

        user = authenticate(request, email=form.cleaned_data['email'], password=form.cleaned_data['password'])

        if not user:
            raise UnauthorizedException()

        # The first factor passed: with two-factor authentication on, no token yet, only a challenge (IP-003).
        if user.two_factor_enabled:
            challenge = TwoFactorService.start_challenge(user)

            return SingleResponse(
                request,
                data={'challenge_id': challenge.pk, 'method': challenge.method, 'expires_at': challenge.expires_at},
                serializer=AuthSerializer.TwoFactorRequired,
                status=HTTPStatus.ACCEPTED,
            )

        token = Token.objects.create(user=user)

        return SingleResponse(request, data=token, serializer=TokenSerializer.Base, status=HTTPStatus.CREATED)

    @transaction.atomic
    def delete(self, request):
        token = getattr(request, 'token', None)

        if token:
            token.hard_delete()

        return SingleResponse(request)
