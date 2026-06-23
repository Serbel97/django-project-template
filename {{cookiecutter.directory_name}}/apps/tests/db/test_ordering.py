"""
Tests for the ordering allow-list (apps.api.response.Ordering) and its
enforcement through PaginationResponse on the user list endpoint.
"""
from http import HTTPStatus

from django.test import SimpleTestCase, RequestFactory
from django.urls import reverse

from apps.api.errors import ProblemDetailException
from apps.api.response import Ordering
from apps.tests.base import Base
from apps.tests.fixtures import UserFixture


class TestOrdering(SimpleTestCase):
    def _request(self, query=''):
        return RequestFactory().get(f'/{query}')

    def test_default_ordering(self):
        ordering = Ordering.create_from_request(self._request(), allowed={'created_at'})

        self.assertEqual(ordering.columns, ['created_at'])

    def test_descending_and_alias(self):
        ordering = Ordering.create_from_request(
            self._request('?order_by=-name'),
            aliases={'name': 'surname'},
            allowed={'surname'},
        )

        self.assertEqual(ordering.columns, ['-surname'])

    def test_disallowed_column_raises(self):
        with self.assertRaises(ProblemDetailException) as ctx:
            Ordering.create_from_request(self._request('?order_by=password'), allowed={'created_at'})

        self.assertEqual(ctx.exception.status, HTTPStatus.BAD_REQUEST)


class TestOrderingEndpoint(Base):
    def test_invalid_order_by_returns_400(self):
        user = UserFixture.create_user(email='order@example.com')
        url = reverse('user-management')

        response = self.get(f'{url}?order_by=password', headers=self.authenticate(user))

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
