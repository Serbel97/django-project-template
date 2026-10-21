"""
Tests for the authentication switches (IP-003 Q6): the config endpoint and the route gating.
"""

from http import HTTPStatus

from django.test import override_settings
from django.urls import reverse

from apps.tests.base import Base


class TestAuthConfig(Base):
    def test_config_reports_the_switches(self):
        response = self.get(reverse('auth-config'))

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.content_dict['response'],
            {'break_glass_enabled': True, 'password_reset_enabled': True, 'registration_enabled': True},
        )


class TestSwitchGating(Base):
    def test_registration_is_refused_while_its_switch_is_off(self):
        with override_settings(AUTH_REGISTRATION_ENABLED=False):
            response = self.post(
                reverse('user-management'),
                {'name': 'Eve', 'surname': 'Doe', 'email': 'eve@example.com'},
            )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_config_reflects_switches_turned_off(self):
        with override_settings(BREAK_GLASS_ENABLED=False):
            response = self.get(reverse('auth-config'))

        self.assertFalse(response.content_dict['response']['break_glass_enabled'])
