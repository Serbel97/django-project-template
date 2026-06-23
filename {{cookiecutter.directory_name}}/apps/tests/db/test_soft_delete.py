"""
Tests for the soft-delete behaviour provided by BaseModel / BaseQuerySet / BaseManager.
"""
from django.test import TestCase

from apps.core.models import User
from apps.tests.fixtures import UserFixture


class TestSoftDelete(TestCase):
    def test_instance_delete_is_soft(self):
        user = UserFixture.create_user(email='soft@example.com')

        user.delete()

        # Hidden from the default manager, still present via all_objects.
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        archived = User.all_objects.get(pk=user.pk)
        self.assertIsNotNone(archived.deleted_at)

    def test_hard_delete_removes_row(self):
        user = UserFixture.create_user(email='hard@example.com')

        user.hard_delete()

        self.assertFalse(User.all_objects.filter(pk=user.pk).exists())

    def test_queryset_delete_is_soft(self):
        UserFixture.create_user(email='qs1@example.com')
        UserFixture.create_user(email='qs2@example.com')

        User.objects.all().delete()

        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(User.all_objects.count(), 2)

    def test_alive_and_dead_querysets(self):
        alive = UserFixture.create_user(email='alive@example.com')
        dead = UserFixture.create_user(email='dead@example.com')
        dead.delete()

        alive_pks = set(User.all_objects.all().alive().values_list('pk', flat=True))
        dead_pks = set(User.all_objects.all().dead().values_list('pk', flat=True))

        self.assertEqual(alive_pks, {alive.pk})
        self.assertEqual(dead_pks, {dead.pk})
