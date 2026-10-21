"""
Tests for the authentication system checks (IP-003 Q6).
"""
from django.test import SimpleTestCase, override_settings

from apps.core.checks import registration_needs_password_reset


class TestRegistrationDependencyCheck(SimpleTestCase):
    @override_settings(AUTH_REGISTRATION_ENABLED=True, AUTH_PASSWORD_RESET_ENABLED=False)
    def test_registration_without_password_reset_is_an_error(self):
        errors = registration_needs_password_reset(None)

        self.assertEqual([error.id for error in errors], ['core.E001'])

    @override_settings(AUTH_REGISTRATION_ENABLED=True, AUTH_PASSWORD_RESET_ENABLED=True)
    def test_registration_with_password_reset_passes(self):
        self.assertEqual(registration_needs_password_reset(None), [])
