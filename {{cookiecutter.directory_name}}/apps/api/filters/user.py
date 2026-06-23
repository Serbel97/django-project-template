import django_filters
from django.db.models import Q

from apps.core.models import User


class UserFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(lookup_expr='icontains', label='Email filter')
    name = django_filters.CharFilter(lookup_expr='icontains', label='Name filter')
    surname = django_filters.CharFilter(lookup_expr='icontains', label='Surname filter')
    is_active = django_filters.BooleanFilter(label='is_active filter')
    query = django_filters.CharFilter(method='filter_query', label='Full text query filter')

    class Meta:
        model = User
        fields: list[str] = []

    @staticmethod
    def filter_query(qs, name, value):
        return qs.filter(
            Q(email__unaccent__icontains=value)
            | Q(name__unaccent__icontains=value)
            | Q(surname__unaccent__icontains=value)
        ).distinct()

    @property
    def qs(self):
        qs = super().qs

        if not self.request.user.is_authenticated:
            return qs.none()

        if not self.request.user.has_perm('core.view_user'):
            qs = qs.filter(pk=self.request.user.id)

        return qs
