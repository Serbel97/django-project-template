from enum import Enum
from http import HTTPStatus
from typing import Tuple, Optional, List, Any

import sentry_sdk
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django_api_forms.forms import Form
from pydantic import Field

from apps.core.serializers import Serializer


class DetailType(Enum):
    OUT_OF_RANGE = '/out-of-range'
    NOT_FOUND = '/not-found'
    VALIDATION_ERROR = '/validation-error'
    CONFLICT = '/conflict'
    INVALID_APIKEY = '/invalid-api-key'
    INVALID_SIGNATURE = '/invalid-signature'
    REQUEST_PAYLOAD_TOO_BIG = '/request-payload-too-big'


class ProblemDetail(Serializer):
    title: str
    type: Optional[DetailType] = Field(default=None)
    detail: Optional[str] = Field(default=None)


class ValidationErrorItem(Serializer):
    code: Optional[str] = Field(default=None)
    message: str
    path: Optional[List[Any]] = Field(default=None)


class ValidationError(ProblemDetail):
    validation_errors: List[ValidationErrorItem]


class ProblemDetailException(Exception):
    def __init__(
        self,
        title: str,
        status: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        previous: Optional[BaseException] = None,
        to_sentry: Optional[bool] = False,
        additional_data: Optional[dict] = None,
        detail_type: Optional[DetailType] = None,
        detail: Optional[str] = None,
        extra_headers: Optional[Tuple[Tuple]] = ()
    ):
        super().__init__(title)

        self._title = title
        self._status_code = status
        self._previous = previous
        self._type = detail_type
        self._detail = detail
        self._extra_headers = extra_headers

        if additional_data:
            self._additional_data = additional_data
        else:
            self._additional_data = {}

        if to_sentry:
            with sentry_sdk.push_scope() as scope:
                for key, value in self.__dict__.items():
                    scope.set_extra(key, value)
                sentry_sdk.capture_exception(self)

    @property
    def title(self) -> str:
        return self._title

    @property
    def status(self) -> int:
        return self._status_code

    @property
    def previous(self) -> BaseException:
        return self._previous

    @property
    def type(self) -> DetailType:
        return self._type

    @property
    def detail(self) -> str:
        return self._detail

    @property
    def extra_headers(self) -> Tuple[Tuple]:
        return self._extra_headers

    @property
    def payload(self) -> ProblemDetail:
        return ProblemDetail(
            title=self.title,
            type=self.type,
            detail=self.detail,
        )


class UnauthorizedException(ProblemDetailException):
    def __init__(self, detail: Optional[str] = None, status=HTTPStatus.UNAUTHORIZED):
        super().__init__(
            _('Unauthorized'),
            status=status,
            extra_headers=(
                ('WWW-Authenticate', f'Bearer realm="{slugify(settings.INSTANCE_NAME)}"'),
            ),
            detail=detail
        )


class ValidationException(ProblemDetailException):
    def __init__(self, form: Form):
        super().__init__(_('Validation error!'), status=HTTPStatus.UNPROCESSABLE_ENTITY)
        self._form = form

    @property
    def payload(self) -> ValidationError:
        return ValidationError(
            title=_('Invalid request parameters'),
            type=DetailType.VALIDATION_ERROR,
            validation_errors=[
                ValidationErrorItem(
                    code=item.code,
                    message=item.message % (item.params or ()),
                    path=getattr(item, 'path', ['$body'])
                ) for item in self._form.errors
            ],
        )
