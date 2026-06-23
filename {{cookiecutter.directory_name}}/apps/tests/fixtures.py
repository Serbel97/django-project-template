"""
Test fixtures and factory helpers.

Lightweight factories (no factory_boy dependency) that build valid objects for
this template's models. ``create_user`` stashes the plain password on the
returned instance as ``plain_password`` so login tests can reuse it.
"""
from apps.core.models import User


class UserFixture:
    """Helper class to create test users with predefined data."""

    @staticmethod
    def create_user(
        email='test@example.com',
        password='SecurePassword123!',
        name='Test',
        surname='User',
        is_active=True,
        is_superuser=False,
        **extra_fields,
    ) -> User:
        """Create and persist a ``User`` and remember the plain password."""
        user = User(
            email=email,
            name=name,
            surname=surname,
            is_active=is_active,
            is_superuser=is_superuser,
            **extra_fields,
        )
        user.set_password(password)
        user.save()
        user.plain_password = password
        return user

    @staticmethod
    def create_superuser(email='admin@example.com', password='AdminPassword123!', **kwargs) -> User:
        return UserFixture.create_user(email=email, password=password, is_superuser=True, **kwargs)

    @staticmethod
    def create_inactive_user(email='inactive@example.com', password='InactivePassword123!', **kwargs) -> User:
        return UserFixture.create_user(email=email, password=password, is_active=False, **kwargs)
