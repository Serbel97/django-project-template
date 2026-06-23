"""
Tests for PATCH /api/v1/users/<id>/password — change password.
"""
from http import HTTPStatus

from django.urls import reverse

from apps.tests.base import Base
from apps.tests.fixtures import UserFixture


class TestChangePassword(Base):
    def setUp(self):
        super().setUp()
        self.user = UserFixture.create_user(email='pwd@example.com', password='OldPassword123!')

    def _url(self, user_id):
        return reverse('change-password', kwargs={'user_id': user_id})

    def test_change_own_password(self):
        response = self.patch(
            self._url(self.user.pk),
            {'old_password': 'OldPassword123!', 'new_password': 'BrandNewPass456!'},
            headers=self.authenticate(self.user),
        )

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNewPass456!'))

    def test_wrong_old_password_rejected(self):
        response = self.patch(
            self._url(self.user.pk),
            {'old_password': 'WrongOld123!', 'new_password': 'BrandNewPass456!'},
            headers=self.authenticate(self.user),
        )

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)

    def test_cannot_change_another_users_password(self):
        other = UserFixture.create_user(email='victim@example.com', password='VictimPass123!')
        response = self.patch(
            self._url(other.pk),
            {'old_password': 'OldPassword123!', 'new_password': 'BrandNewPass456!'},
            headers=self.authenticate(self.user),
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
