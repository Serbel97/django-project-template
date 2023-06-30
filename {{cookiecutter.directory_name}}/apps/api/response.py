import json
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Type, Union, List

from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponse
from django.utils.translation import gettext as _
from porcupine.base import Serializer

from apps.api.encoders import ApiJSONEncoder
from apps.api.errors import ValidationException, ProblemDetailException


@dataclass
class Ordering:
    columns: List[str] = field(default_factory=list)

    @classmethod
    def create_from_request(cls, request, aliases: dict = None) -> 'Ordering':
        columns = []
        aliases = aliases or {}

        for column in request.GET.getlist('order_by', ['created_at']):
            column_name = column[1:] if column.startswith("-") else column
            if column_name in aliases.keys():
                alias_value = aliases[column_name]
                if isinstance(alias_value, str):
                    alias_value = [alias_value]
                for val in alias_value:
                    columns.append(
                        f"-{val}" if column.startswith("-") else val
                    )
            else:
                columns.append(column)
        return Ordering(columns)

    def __str__(self):
        return ",".join(self.columns)

    def __repr__(self):
        return self.__str__()


class GeneralResponse(HttpResponse):
    def __init__(self, request, data: Union[models.Model, dict] = None, serializer: Type[Serializer] = None, **kwargs):
        params = {}
        if data is not None:
            content_types = str(request.headers.get('accept', 'application/json'))
            content_types = content_types.split(', ')
            content_types = list(map(lambda r: r.split(';')[0], content_types))

            if any(x in ['*/*', 'application/json'] for x in content_types):
                params['content_type'] = 'application/json'
                params['content'] = json.dumps(data, cls=ApiJSONEncoder, serializer=serializer, request=request)
            else:
                params['content_type'] = 'application/json'
                params['status'] = HTTPStatus.NOT_ACCEPTABLE
                params['content'] = json.dumps({
                    'message': _("Not Acceptable"),
                    'metadata': {
                        'available': [
                            'application/json',
                        ],
                        'asked': ', '.join(content_types)
                    }
                })

        kwargs.update(params)
        super().__init__(**kwargs)


class SingleResponse(GeneralResponse):
    def __init__(self, request, data=None, metadata: dict = None, **kwargs):
        if 'status' not in kwargs and data is None:
            kwargs['status'] = HTTPStatus.NO_CONTENT
        elif 'status' not in kwargs and data:
            kwargs['status'] = HTTPStatus.OK

        if data:
            data = {
                'response': data,
            }
            if metadata:
                data['metadata'] = metadata
        super().__init__(request=request, data=data, **kwargs)


class ErrorResponse(GeneralResponse):
    def __init__(self, request, payload: dict, **kwargs):
        super().__init__(request=request, data=payload, **kwargs)

    @staticmethod
    def create_from_exception(e: ProblemDetailException) -> 'ErrorResponse':
        return ErrorResponse(e.request, e.payload, status=e.status, headers=e.extra_headers)


class ValidationResponse(GeneralResponse):
    def __init__(self, request, payload: dict, **kwargs):
        data = {
            'type': '/validation-error',
            'title': 'Invalid request parameters',
            'status': HTTPStatus.UNPROCESSABLE_ENTITY,
            'errors': payload,
        }

        super().__init__(request, data, status=HTTPStatus.UNPROCESSABLE_ENTITY, **kwargs)

    @staticmethod
    def create_from_exception(e: ValidationException) -> 'ValidationResponse':
        return ValidationResponse(e.request, e.payload, status=HTTPStatus.UNPROCESSABLE_ENTITY)


class PaginationResponse(GeneralResponse):
    def __init__(self, request, qs, ordering: Ordering = None, extras: dict = None, **kwargs):
        kwargs.setdefault('content_type', 'application/json')

        # Ordering
        if isinstance(qs, QuerySet):
            ordering = ordering if ordering else Ordering.create_from_request(request)
            qs = qs.order_by(*ordering.columns)

        paginate = request.GET.get('paginate', 'true') == 'true'

        if paginate:
            limit = int(request.GET.get('limit', settings.PAGINATION['DEFAULT_LIMIT']))
            page = int(request.GET.get('page', 1))

            paginator = Paginator(qs, limit)

            try:
                paginator.validate_number(page)
            except EmptyPage as e:
                raise ProblemDetailException(
                    request,
                    title=_('Page not found'),
                    status=HTTPStatus.NOT_FOUND,
                    previous=e,
                    detail_type='out_of_range',
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

        data = {}
        if extras:
            for key, item in extras.items():
                data[key] = item

        data['items'] = items
        data['metadata'] = {
            'page': page,
            'limit': limit,
            'pages': num_pages,
            'total': total
        }

        super().__init__(request, data, **kwargs)


__all__ = [
    'SingleResponse',
    'ErrorResponse',
    'PaginationResponse',
    'ValidationResponse',
    'Ordering'
]
