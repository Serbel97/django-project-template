"""
Base test class with HTTP helpers for API tests.

Every API endpoint extends ``SecuredView`` and therefore requires:

* a valid ``X-Apikey`` header, and
* a matching ``X-Signature`` HMAC-SHA256 of ``"<body>:<path>"`` signed with the
  API key secret (Django's test runner forces ``DEBUG = False``, so the signature
  check is always active — just like production).

``Base`` provisions a test API key once per class and signs every request.
Authenticated requests additionally need a Bearer token — use :meth:`authenticate`.
"""
import hashlib
import hmac
import json

from django.test import TestCase

from apps.core.models import ApiKey, Token

API_KEY_SECRET = 'test-secret'


class Base(TestCase):
    """Base test class with signed HTTP helper methods for API testing."""

    _content_type = 'application/json'

    @classmethod
    def setUpTestData(cls):
        cls.api_key = ApiKey.objects.create(
            name='test',
            platform=ApiKey.DevicePlatform.WEB,
            secret=API_KEY_SECRET,
            is_active=True,
        )

    def setUp(self):
        self.base_headers = {
            'Accept': 'application/json',
            'X-Apikey': str(self.api_key.pk),
        }

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def authenticate(user) -> dict:
        """Create a Bearer token for ``user`` and return the auth header."""
        token = Token.objects.create(user=user)
        return {'Authorization': f'Bearer {token.pk}'}

    @staticmethod
    def _sign(body: str, url: str) -> str:
        # The view signs over request.path (query string excluded).
        path = url.split('?', 1)[0]
        message = f'{body}:{path}'
        return hmac.new(API_KEY_SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

    def _headers(self, body: str, url: str, extra: dict | None) -> dict:
        headers = {**self.base_headers, 'X-Signature': self._sign(body, url)}
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def check_response(response):
        """Attach ``response.content_dict`` with the parsed JSON body (if any)."""
        if 'application/json' in response.get('Content-Type', '') and response.content:
            try:
                response.content_dict = json.loads(response.content.decode('utf-8'))
            except json.JSONDecodeError:
                response.content_dict = {}
        else:
            response.content_dict = {}
        return response

    # -- verbs -----------------------------------------------------------------

    def get(self, url, headers=None):
        return self.check_response(self.client.get(url, headers=self._headers('', url, headers)))

    def post(self, url, data=None, headers=None):
        body = json.dumps(data) if isinstance(data, dict) else (data or '')
        response = self.client.post(
            url, data=body, content_type=self._content_type, headers=self._headers(body, url, headers)
        )
        return self.check_response(response)

    def put(self, url, data=None, headers=None):
        body = json.dumps(data) if isinstance(data, dict) else (data or '')
        response = self.client.put(
            url, data=body, content_type=self._content_type, headers=self._headers(body, url, headers)
        )
        return self.check_response(response)

    def patch(self, url, data=None, headers=None):
        body = json.dumps(data) if isinstance(data, dict) else (data or '')
        response = self.client.patch(
            url, data=body, content_type=self._content_type, headers=self._headers(body, url, headers)
        )
        return self.check_response(response)

    def delete(self, url, headers=None):
        return self.check_response(self.client.delete(url, headers=self._headers('', url, headers)))
