"""
Tests for the authentication system checks (IP-003 Q3, Q6).
"""

from django.test import SimpleTestCase, override_settings

from apps.core.checks import break_glass_in_production, registration_needs_password_reset


class TestBreakGlassProductionCheck(SimpleTestCase):
    @override_settings(BREAK_GLASS_ENABLED=True, DEPLOYMENT_ENVIRONMENT='prod')
    def test_warns_when_break_glass_is_on_in_production(self):
        errors = break_glass_in_production(None)

        self.assertEqual([error.id for error in errors], ['core.W001'])

    @override_settings(BREAK_GLASS_ENABLED=True, DEPLOYMENT_ENVIRONMENT='dev')
    def test_silent_outside_production(self):
        self.assertEqual(break_glass_in_production(None), [])

    @override_settings(BREAK_GLASS_ENABLED=False, DEPLOYMENT_ENVIRONMENT='prod')
    def test_silent_when_break_glass_is_off(self):
        self.assertEqual(break_glass_in_production(None), [])


class TestRegistrationDependencyCheck(SimpleTestCase):
    @override_settings(AUTH_REGISTRATION_ENABLED=True, AUTH_PASSWORD_RESET_ENABLED=False)
    def test_registration_without_password_reset_is_an_error(self):
        errors = registration_needs_password_reset(None)

        self.assertEqual([error.id for error in errors], ['core.E001'])

    @override_settings(AUTH_REGISTRATION_ENABLED=True, AUTH_PASSWORD_RESET_ENABLED=True)
    def test_registration_with_password_reset_passes(self):
        self.assertEqual(registration_needs_password_reset(None), [])
