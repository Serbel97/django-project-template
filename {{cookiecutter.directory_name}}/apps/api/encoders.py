import decimal
from enum import Enum
from uuid import UUID

from django.core.exceptions import ValidationError
from django.core.paginator import Page
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext as _


class ApiJSONEncoder(DjangoJSONEncoder):
    """
    JSON encoder for the few raw ``dict`` payloads we serialise directly (e.g. the status
    endpoint). Model instances are serialised through pydantic serializers in
    ``apps.api.response`` and must not be passed here.
    """

    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, models.Model):
            raise RuntimeError(
                _('Model instances must be serialised through a pydantic serializer, not ApiJSONEncoder.')
            )
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, Page):
            return o.object_list
        if isinstance(o, Enum):
            return o.value
        if isinstance(o, QuerySet):
            return list(o)
        if isinstance(o, set):
            return list(o)
        if isinstance(o, ValidationError):
            return o.message
        return DjangoJSONEncoder.default(self, o)


__all__ = [
    'ApiJSONEncoder'
]
