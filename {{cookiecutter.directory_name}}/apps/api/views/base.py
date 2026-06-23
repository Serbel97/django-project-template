import hashlib
import hmac
from http import HTTPStatus
from typing import Dict, Union

from django.conf import settings
from django.contrib.auth import load_backend
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from sentry_sdk import set_tag

from apps.api.errors import ProblemDetailException, DetailType
from apps.api.errors import UnauthorizedException
from apps.core.models import ApiKey


class SecuredView(View):
    EXEMPT_AUTH: list[str] = []
    EXEMPT_API_KEY: list[str] = []
    REQUIRE_SUPERUSER: list[str] = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._backends: Dict[str, BaseBackend] = {}
        for schema, backend in settings.SECURED_VIEW_AUTHENTICATION_SCHEMAS.items():
            self._backends[schema.lower()] = load_backend(backend)

    def _authenticate(self, request) -> Union[AnonymousUser, AbstractBaseUser]:
        if request.method in self.EXEMPT_AUTH:
            return AnonymousUser()

        auth_header = request.headers.get('Authorization', '')

        if not auth_header:
            raise UnauthorizedException(detail=_("Invalid or missing Authorization header"))

        auth_header = str(auth_header).split(' ')

        if len(auth_header) != 2:
            raise UnauthorizedException(detail=_("Invalid or missing Authorization header"))

        if not auth_header[0] in settings.SECURED_VIEW_AUTHENTICATION_SCHEMAS.keys():
            raise UnauthorizedException(detail=_('Unsupported authentication schema'))

        auth_params = {
            auth_header[0].lower(): auth_header[1]
        }

        user = self._backends[auth_header[0].lower()].authenticate(request, **auth_params)

        if not settings.IS_ENABLED_ANONYMOUS_USER:
            if user.is_anonymous:
                raise UnauthorizedException(detail=_("Invalid or missing Authorization header"))

        return user

    def _check_api_key(self, request):
        api_key = request.headers.get('X-Apikey')

        try:
            api_key_model = ApiKey.objects.get(pk=api_key, is_active=True)
        except ApiKey.DoesNotExist:
            raise ProblemDetailException(
                _('Invalid api key.'), status=HTTPStatus.UNAUTHORIZED,
                detail_type=DetailType.INVALID_APIKEY
            )

        request.api_key = api_key_model
        set_tag('apikey.platform', request.api_key.platform)

        if api_key_model.platform == ApiKey.DevicePlatform.DEBUG and not settings.DEBUG:
            raise ProblemDetailException(
                title=_('Invalid api key.'),
                status=HTTPStatus.UNAUTHORIZED,
                detail_type=DetailType.INVALID_APIKEY
            )
        else:
            self._check_signature(request, api_key_model)

        return None

    @staticmethod
    def _check_signature(request: HttpRequest, api_key: ApiKey):
        signature = request.headers.get('X-Signature', '')

        # Do not check signature for DEBUG API keys and DEBUG environment
        if api_key.platform in [ApiKey.DevicePlatform.DEBUG] or settings.DEBUG:
            return None

        message = f"{request.body.decode('utf-8')}:{request.path}"
        signature_check = hmac.new(
            api_key.secret.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()

        if signature != signature_check:
            raise ProblemDetailException(
                _('Invalid signature.'),
                status=HTTPStatus.BAD_REQUEST,
                to_sentry=True,
                additional_data={
                    'received': signature,
                    'expected': signature_check,
                    'message': message,
                    'path': request.path,
                },
                detail_type=DetailType.INVALID_SIGNATURE
            )

        return None

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if request.method not in self.EXEMPT_API_KEY:
            self._check_api_key(request)

        request.user = self._authenticate(request)
        if request.user.is_authenticated:
            set_tag('user.id', request.user.id)

        if request.method in self.REQUIRE_SUPERUSER:
            if not request.user.is_superuser:
                raise ProblemDetailException(
                    _('Insufficient permissions'), status=HTTPStatus.FORBIDDEN,
                )

        return super().dispatch(request, *args, **kwargs)
