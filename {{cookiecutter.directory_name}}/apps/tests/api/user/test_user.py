"""
Tests for the user endpoints:
  POST   /api/v1/users            (registration, anonymous)
  GET    /api/v1/users            (list, authenticated)
  GET    /api/v1/users/me         (current user)
  GET    /api/v1/users/<id>       (detail)
  PUT    /api/v1/users/<id>       (update)
  DELETE /api/v1/users/<id>       (soft delete)
"""
from http import HTTPStatus

from django.core import mail
from django.urls import reverse

from apps.core.models import User
from apps.tests.base import Base
from apps.tests.fixtures import UserFixture


class TestUserRegistration(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._url = reverse('user-management')

    def test_register_creates_user_and_sends_email(self):
        response = self.post(self._url, {'email': 'new@example.com', 'name': 'New', 'surname': 'User'})

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(response.content_dict['response']['email'], 'new@example.com')

        user = User.objects.get(email='new@example.com')
        # Registration leaves the account without a usable password (set via recovery code).
        self.assertFalse(user.has_usable_password())
        self.assertEqual(len(mail.outbox), 1)

    def test_register_duplicate_email_conflicts(self):
        UserFixture.create_user(email='dupe@example.com')
        response = self.post(self._url, {'email': 'dupe@example.com', 'name': 'Dupe', 'surname': 'User'})

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)

    def test_register_missing_fields(self):
        response = self.post(self._url, {'email': 'partial@example.com'})

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)


class TestUserEmailCaseInsensitive(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._url = reverse('user-management')

    def test_register_rejects_case_variant_of_existing_email(self):
        UserFixture.create_user(email='taken@example.com')
        response = self.post(self._url, {'email': 'Taken@Example.com', 'name': 'New', 'surname': 'User'})

        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)

    def test_register_strips_and_lowercases_email(self):
        response = self.post(self._url, {'email': '  Fresh@Example.COM ', 'name': 'Fr', 'surname': 'Esh'})

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertTrue(User.objects.filter(email='fresh@example.com').exists())


class TestUserList(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._url = reverse('user-management')

    def setUp(self):
        super().setUp()
        self.user = UserFixture.create_user(email='lister@example.com')

    def test_list_requires_authentication(self):
        response = self.get(self._url)

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    def test_list_without_permission_returns_only_self(self):
        UserFixture.create_user(email='other@example.com')
        response = self.get(self._url, headers=self.authenticate(self.user))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        emails = [item['email'] for item in response.content_dict['items']]
        self.assertEqual(emails, [self.user.email])


class TestUserMe(Base):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._url = reverse('user-me')

    def test_me_returns_current_user(self):
        user = UserFixture.create_user(email='me@example.com')
        response = self.get(self._url, headers=self.authenticate(user))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.content_dict['response']['email'], user.email)

    def test_me_requires_authentication(self):
        response = self.get(self._url)

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)


class TestUserDetail(Base):
    def setUp(self):
        super().setUp()
        self.user = UserFixture.create_user(email='owner@example.com')

    def _url(self, user_id):
        return reverse('user-detail', kwargs={'user_id': user_id})

    def test_get_own_detail(self):
        response = self.get(self._url(self.user.pk), headers=self.authenticate(self.user))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.content_dict['response']['email'], self.user.email)

    def test_get_other_user_forbidden(self):
        other = UserFixture.create_user(email='stranger@example.com')
        response = self.get(self._url(other.pk), headers=self.authenticate(self.user))

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_get_missing_user_returns_404(self):
        response = self.get(
            self._url('00000000-0000-0000-0000-000000000000'),
            headers=self.authenticate(self.user),
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_update_own_detail(self):
        response = self.put(
            self._url(self.user.pk),
            {'name': 'Renamed', 'surname': 'Person', 'email': self.user.email},
            headers=self.authenticate(self.user),
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, 'Renamed')

    def test_delete_soft_deletes_and_deactivates(self):
        response = self.delete(self._url(self.user.pk), headers=self.authenticate(self.user))

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        # Soft-deleted rows disappear from the default manager but remain in all_objects.
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        archived = User.all_objects.get(pk=self.user.pk)
        self.assertFalse(archived.is_active)
        self.assertIsNotNone(archived.deleted_at)
