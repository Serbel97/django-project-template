"""
Tests for the recovery-code endpoints:
  POST /api/v1/recovery_code            (request a recovery code by e-mail)
  POST /api/v1/recovery_code/<id>       (set a new password using a recovery code)
"""
from http import HTTPStatus

from django.core import mail
from django.urls import reverse

from apps.core.models import RecoveryCode
from apps.tests.base import Base
from apps.tests.fixtures import UserFixture


class TestRecoveryCodeRequest(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._url = reverse('recovery-code')

    def test_request_for_existing_user_creates_code_and_emails(self):
        user = UserFixture.create_user(email='recover@example.com')
        response = self.post(self._url, {'email': user.email})

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertTrue(RecoveryCode.objects.filter(user=user).exists())
        self.assertEqual(len(mail.outbox), 1)

    def test_request_for_unknown_user_is_silent(self):
        """Unknown e-mails return the same 204 and send nothing (no enumeration)."""
        response = self.post(self._url, {'email': 'ghost@example.com'})

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(len(mail.outbox), 0)


class TestRecoveryCodeReset(Base):
    def setUp(self):
        super().setUp()
        self.user = UserFixture.create_user(email='reset@example.com', is_active=False)
        self.recovery_code = RecoveryCode.objects.create(user=self.user)

    def _url(self, recovery_code_id):
        return reverse('recovery-code-id', kwargs={'recovery_code_id': recovery_code_id})

    def test_reset_sets_password_and_activates(self):
        response = self.post(self._url(self.recovery_code.pk), {'password': 'FreshPassword123!'})

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('FreshPassword123!'))
        self.assertTrue(self.user.is_active)
        # The used recovery code is consumed.
        self.assertFalse(RecoveryCode.objects.filter(pk=self.recovery_code.pk).exists())

    def test_reset_with_unknown_code_returns_404(self):
        response = self.post(
            self._url('00000000-0000-0000-0000-000000000000'),
            {'password': 'FreshPassword123!'},
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
