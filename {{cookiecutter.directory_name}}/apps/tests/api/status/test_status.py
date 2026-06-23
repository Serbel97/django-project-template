"""
Tests for GET /api/v1/status — public health/status endpoint.

StatusManagement is a plain view (not a SecuredView), so it needs neither an
API key nor authentication.
"""
from http import HTTPStatus

from django.urls import reverse
from django.test import TestCase


class TestStatusEndpoint(TestCase):
    def setUp(self):
        self._url = reverse('status')

    def test_status_returns_expected_fields(self):
        response = self.client.get(self._url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        body = response.json()
        for field in ('timestamp', 'instance', 'build', 'version'):
            self.assertIn(field, body)
