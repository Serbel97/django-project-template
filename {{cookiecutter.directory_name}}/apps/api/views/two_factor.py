from http import HTTPStatus

from django.db import transaction

from apps.api.errors import ValidationException
from apps.api.forms.two_factor import TwoFactorForm
from apps.api.response import SingleResponse
from apps.api.views.base import SecuredView
from apps.core.models import Token
from apps.core.models.user import User
from apps.core.serializers.auth import AuthSerializer
from apps.core.serializers.token import TokenSerializer
from apps.core.services.auth import TwoFactorService


class TwoFactorManagement(SecuredView):
    """Enrol in, or drop out of, two-factor authentication for the current user."""

    @transaction.atomic
    def post(self, request):
        """Start two-factor enrolment."""
        form = TwoFactorForm.Enable.create_from_request(request)

        if not form.is_valid():
            raise ValidationException(form)

        if form.cleaned_data['method'] == User.TwoFactorMethod.TOTP:
            # Hand back the secret only — the second factor stays off until the user proves the
            # authenticator works via POST /auth/2fa/confirm.
            provisioning = TwoFactorService.provision_totp(request.user)

            return SingleResponse(
                request, data=provisioning, serializer=AuthSerializer.TotpProvision, status=HTTPStatus.CREATED
            )

        codes = TwoFactorService.enable_email(request.user)

        return SingleResponse(
            request, data={'backup_codes': codes}, serializer=AuthSerializer.BackupCodes, status=HTTPStatus.CREATED
        )

    @transaction.atomic
    def delete(self, request):
        """Disable two-factor authentication and invalidate every backup code."""
        TwoFactorService.disable(request.user)

        return SingleResponse(request)


class TwoFactorConfirm(SecuredView):
    @transaction.atomic
    def post(self, request):
        """Confirm the authenticator application and switch the second factor on."""
        form = TwoFactorForm.Confirm.create_from_request(request)

        if not form.is_valid():
            raise ValidationException(form)

        codes = TwoFactorService.confirm_totp(request.user, form.cleaned_data['code'])

        return SingleResponse(
            request, data={'backup_codes': codes}, serializer=AuthSerializer.BackupCodes, status=HTTPStatus.CREATED
        )


class TwoFactorVerify(SecuredView):
    EXEMPT_AUTH = ['POST']

    # Deliberately not @transaction.atomic: a failed verification raises after the attempt counter is
    # incremented, and that increment must survive the rollback.
    def post(self, request):
        """Complete a two-factor challenge and issue an access token."""
        form = TwoFactorForm.Verify.create_from_request(request)

        if not form.is_valid():
            raise ValidationException(form)

        user = TwoFactorService.verify(form.cleaned_data['challenge_id'], form.cleaned_data['code'])

        token = Token.objects.create(user=user)

        return SingleResponse(request, data=token, serializer=TokenSerializer.Base, status=HTTPStatus.CREATED)


class BackupCodeManagement(SecuredView):
    @transaction.atomic
    def post(self, request):
        """Replace the current user's backup codes and return the new ones."""
        codes = TwoFactorService.generate_backup_codes(request.user)

        return SingleResponse(
            request, data={'backup_codes': codes}, serializer=AuthSerializer.BackupCodes, status=HTTPStatus.CREATED
        )
