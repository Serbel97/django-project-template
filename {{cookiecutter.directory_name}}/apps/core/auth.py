from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.core.models.token import Token
from apps.api.errors import UnauthorizedException

User = get_user_model()


class BearerBackend(ModelBackend):
    def authenticate(self, request, **kwargs):
        try:
            token = Token.objects.get(pk=kwargs['bearer'], expires_at__gte=timezone.now())
        except (Token.DoesNotExist, ValidationError):
            raise UnauthorizedException(detail=_('Invalid Bearer Token'))

        if not self.user_can_authenticate(token.user):
            raise UnauthorizedException(_('Inactive user.'), status=HTTPStatus.FORBIDDEN)

        token.user.last_login = timezone.now()
        token.user.save(update_fields=['last_login'])

        request.token = token

        return token.user


class BasicBackend(ModelBackend):
    def authenticate(self, request, **kwargs):
        user = super().authenticate(request, **kwargs)

        if not user:
            raise UnauthorizedException()
        return user
