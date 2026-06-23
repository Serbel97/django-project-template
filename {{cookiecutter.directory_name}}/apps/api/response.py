import json
from dataclasses import dataclass
from http import HTTPStatus
from typing import Optional, List, Type, TypeVar

from django.conf import settings
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext as _
from pydantic import RootModel, Field

from apps.api.encoders import ApiJSONEncoder
from apps.api.errors import ProblemDetailException, DetailType, ValidationError, ProblemDetail
from apps.core.serializers import Serializer

ResponseType = TypeVar('ResponseType')


class SingleResponseModel(Serializer):
    response: ResponseType


class PaginationModel(Serializer):
    page: int
    limit: Optional[int] = Field(default=None)
    pages: int
    total: int


class PaginationResponseModel(Serializer):
    items: RootModel[ResponseType]
    metadata: PaginationModel


@dataclass
class Ordering:
    columns: List[str]

    @classmethod
    def create_from_request(cls, request, aliases: dict = None, allowed=None) -> 'Ordering':
        """
        Build an ``Ordering`` from the ``order_by`` query parameter.

        ``aliases`` maps a public column name to the underlying ORM field. ``allowed`` is an
        iterable of ORM fields clients are permitted to sort by; when provided, any other column
        is rejected with HTTP 400 to prevent ``order_by`` injection / information disclosure.
        """
        columns = []
        aliases = aliases or {}
        allowed = set(allowed) if allowed is not None else None

        for column in request.GET.getlist('order_by', ['created_at']):
            descending = column.startswith('-')
            column_name = column[1:] if descending else column
            resolved = aliases.get(column_name, column_name)

            if allowed is not None and resolved not in allowed:
                raise ProblemDetailException(
                    title=_('Invalid ordering column'),
                    status=HTTPStatus.BAD_REQUEST,
                    detail_type=DetailType.OUT_OF_RANGE,
                    detail=_('Cannot order by "%(column)s". Allowed columns: %(allowed)s') % {
                        'column': column_name,
                        'allowed': ', '.join(sorted(allowed)),
                    },
                )

            columns.append(f'-{resolved}' if descending else resolved)

        return Ordering(columns)

    def __str__(self):
        return ','.join(self.columns)

    def __repr__(self):
        return self.__str__()


class GeneralResponse(HttpResponse):
    def __init__(self, request, data: Optional[ResponseType] = None, **kwargs):
        params = {}
        if data is not None:
            content_types = str(request.headers.get('accept', 'application/json'))
            content_types = content_types.replace(' ', '').split(',')
            content_types = list(map(lambda r: r.split(';')[0], content_types))

            if any(x in ['*/*', 'application/json'] for x in content_types):
                params['content_type'] = 'application/json'
                if isinstance(data, dict):
                    params['content'] = json.dumps(data, cls=ApiJSONEncoder)
                else:
                    params['content'] = data.model_dump_json(by_alias=True)
            else:
                params['content_type'] = 'application/json'
                params['status'] = HTTPStatus.NOT_ACCEPTABLE
                params['content'] = json.dumps(
                    {
                        'message': _('Not Acceptable'),
                        'metadata': {
                            'available': [
                                'application/json',
                            ],
                            'asked': ', '.join(content_types)
                        }
                    }
                )

        kwargs.update(params)
        super().__init__(**kwargs)


class SingleResponse(GeneralResponse):
    def __init__(self, request, data=None, serializer: Type[Serializer] = None, **kwargs):
        if 'status' not in kwargs and data is None:
            kwargs['status'] = HTTPStatus.NO_CONTENT
        elif 'status' not in kwargs and data:
            kwargs['status'] = HTTPStatus.OK

        if data and serializer:
            data = SingleResponseModel(
                response=RootModel[serializer].model_validate(
                    data,
                    from_attributes=True,
                    context={
                        'request': request
                    }
                )
            )
        super().__init__(request=request, data=data, **kwargs)


class ErrorResponse(GeneralResponse):
    def __init__(self, request, payload: ProblemDetail, **kwargs):
        kwargs.setdefault('status', HTTPStatus.INTERNAL_SERVER_ERROR)
        super().__init__(request=request, data=payload, **kwargs)


class ValidationResponse(GeneralResponse):
    def __init__(self, request, payload: ValidationError, **kwargs):
        kwargs.setdefault('content_type', 'application/problem+json')
        kwargs.setdefault('status', HTTPStatus.UNPROCESSABLE_ENTITY)
        super().__init__(request, payload, **kwargs)


class PaginationResponse(GeneralResponse):
    def __init__(self, request, qs, serializer: Type[Serializer], ordering: Ordering = None, **kwargs):
        kwargs.setdefault('content_type', 'application/json')

        # Ordering (restricted to the model's whitelisted sortable columns)
        if not ordering:
            allowed = getattr(qs.model, 'ORDERING_FIELDS', None)
            ordering = Ordering.create_from_request(request, allowed=allowed)
        qs = qs.order_by(*ordering.columns)

        # Pagination
        paginate = request.GET.get('paginate', 'true') == 'true'
        if paginate:
            limit = int(request.GET.get('limit', settings.PAGINATION['DEFAULT_LIMIT']))
            page = int(request.GET.get('page', 1))

            paginator = Paginator(qs, limit)

            try:
                paginator.validate_number(page)
            except EmptyPage as e:
                raise ProblemDetailException(
                    title=_('Page not found'),
                    status=HTTPStatus.NOT_FOUND,
                    previous=e,
                    detail_type=DetailType.OUT_OF_RANGE,
                    detail=_('That page contains no results')
                )

            items = paginator.get_page(page)
            num_pages = paginator.num_pages
            total = paginator.count
        else:
            limit = None
            page = 1
            items = qs
            num_pages = 1
            total = qs.count()

        super().__init__(
            request, PaginationResponseModel(
                items=RootModel[List[serializer]].model_validate(
                    list(items),
                    from_attributes=True,
                    context={
                        'request': request
                    }
                ),
                metadata=PaginationModel(
                    page=page,
                    limit=limit,
                    pages=num_pages,
                    total=total
                )
            ), **kwargs
        )


class SeeOtherResponse(HttpResponseRedirect):
    status_code = 303


__all__ = [
    'SingleResponse',
    'ErrorResponse',
    'PaginationResponse',
    'ValidationResponse',
    'SeeOtherResponse',
    'Ordering'
]
