"""
SSO claim mapping and the allauth adapters (IP-003 Key Components 3–5).

The adapters are driven the way allauth 65 drives them, without any network:
first login  = populate_user() on a fresh User, then save_user();
next login   = lookup() found the SocialAccount (simulated: stored account with new extra_data),
               then pre_social_login().
"""
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from apps.core.models import User
from apps.core.services.auth.sso import (
    NoSignupAccountAdapter,
    SSOSocialAccountAdapter,
    claims_from_extra_data,
    identity_from_claims,
    normalise_groups,
)
from apps.tests.fixtures import UserFixture

PROVIDER = 'test-idp'


def claims(sub='sub-1', **overrides) -> dict:
    data = {
        'sub': sub,
        'email': 'Carol@Example.com',
        'given_name': 'Carol',
        'family_name': 'Example',
        'name': 'Carol Example',
        'groups': ['staff', 'admins'],
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


class SSOAdapterTestCase(TestCase):
    def setUp(self):
        self.request = RequestFactory().get(f'/accounts/oidc/{PROVIDER}/login/callback/')
        SessionMiddleware(lambda request: HttpResponse()).process_request(self.request)
        self.adapter = SSOSocialAccountAdapter(self.request)

    def first_login(self, extra_data: dict) -> User:
        account = SocialAccount(provider=PROVIDER, uid=extra_data['sub'], extra_data=extra_data)
        sociallogin = SocialLogin(account=account, user=User())
        self.adapter.populate_user(self.request, sociallogin, {})
        return self.adapter.save_user(self.request, sociallogin)

    def next_login(self, extra_data: dict) -> User:
        account = SocialAccount.objects.get(provider=PROVIDER, uid=extra_data['sub'])
        account.extra_data = extra_data
        account.save()
        sociallogin = SocialLogin(account=account, user=account.user)
        self.adapter.pre_social_login(self.request, sociallogin)
        return User.objects.get(pk=account.user_id)

    def assertRefused(self, code: str, call, *args):
        with (
            self.assertLogs('apps.core.services.auth.sso', 'WARNING'),
            self.assertRaises(ImmediateHttpResponse) as raised,
        ):
            call(*args)
        response = raised.exception.response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], f'http://spa.test/login/error?error={code}')


class TestFirstLogin(SSOAdapterTestCase):
    def test_first_login_creates_the_user(self):
        user = self.first_login(claims())

        self.assertEqual(user.email, 'carol@example.com')
        self.assertEqual((user.name, user.surname), ('Carol', 'Example'))
        self.assertEqual(user.idp_groups, ['admins', 'staff'])
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_superuser)
        self.assertTrue(SocialAccount.objects.filter(provider=PROVIDER, uid='sub-1', user=user).exists())

    def test_display_name_fills_name_and_surname_when_given_and_family_name_are_missing(self):
        user = self.first_login(claims(given_name=None, family_name=None, name='Dana Van Example'))

        self.assertEqual((user.name, user.surname), ('Dana', 'Van Example'))

    def test_overlong_name_is_cut_to_the_column(self):
        user = self.first_login(claims(given_name='X' * 50))

        self.assertEqual(user.name, 'X' * 30)

    def test_login_without_email_is_refused(self):
        self.assertRefused('email_missing', self.first_login, claims(email=None))

        self.assertFalse(User.objects.exists())

    def test_email_of_an_existing_local_account_is_refused_and_nothing_is_linked(self):
        local = UserFixture.create_user(email='carol@example.com')

        self.assertRefused('email_conflict', self.first_login, claims())

        self.assertFalse(SocialAccount.objects.exists())
        self.assertTrue(local.has_usable_password())

    def test_email_of_a_soft_deleted_account_is_refused(self):
        UserFixture.create_user(email='carol@example.com').delete()

        self.assertRefused('email_conflict', self.first_login, claims())


class TestNextLogin(SSOAdapterTestCase):
    def test_next_login_refreshes_attributes_and_groups(self):
        user = self.first_login(claims())

        refreshed = self.next_login(claims(email='carol.new@example.com', family_name='Married', groups=['staff']))

        self.assertEqual(refreshed.pk, user.pk)
        self.assertEqual(refreshed.email, 'carol.new@example.com')
        self.assertEqual(refreshed.surname, 'Married')
        self.assertEqual(refreshed.idp_groups, ['staff'])

    def test_same_subject_is_the_same_user_after_an_email_change(self):
        user = self.first_login(claims())
        self.next_login(claims(email='renamed@example.com'))

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(SocialAccount.objects.get(uid='sub-1').user_id, user.pk)

    def test_email_change_to_a_taken_address_is_refused_and_keeps_the_record(self):
        self.first_login(claims())
        UserFixture.create_user(email='taken@example.com')

        self.assertRefused('email_conflict', self.next_login, claims(email='taken@example.com'))

        self.assertTrue(User.objects.filter(email='carol@example.com').exists())


class TestClaimMapping(SimpleTestCase):
    def test_userinfo_wins_over_the_id_token(self):
        data = {'id_token': {'sub': 's', 'email': 'old@example.com'}, 'userinfo': {'email': 'new@example.com'}}

        self.assertEqual(claims_from_extra_data(data), {'sub': 's', 'email': 'new@example.com'})

    def test_groups_are_sorted_deduplicated_and_a_string_is_one_group(self):
        self.assertEqual(normalise_groups(['b', 'a', 'b', ' ', None]), ['a', 'b'])
        self.assertEqual(normalise_groups('admins'), ['admins'])
        self.assertEqual(normalise_groups({'nested': 'dict'}), [])

    def test_claims_without_subject_are_rejected(self):
        with self.assertRaises(ValueError):
            identity_from_claims({'email': 'a@example.com'}, 'groups')


class TestNoSignupAccountAdapter(TestCase):
    def test_local_signup_through_allauth_is_closed(self):
        adapter = NoSignupAccountAdapter(RequestFactory().get('/'))

        self.assertFalse(adapter.is_open_for_signup(None))

    @override_settings(ALLOWED_HOSTS=['api.test'])
    def test_redirects_are_limited_to_the_spa_and_the_api_host(self):
        adapter = NoSignupAccountAdapter(RequestFactory().get('/', HTTP_HOST='api.test'))

        self.assertTrue(adapter.is_safe_url('http://spa.test/after-login'))
        self.assertTrue(adapter.is_safe_url('http://api.test/somewhere'))
        self.assertFalse(adapter.is_safe_url('https://evil.example/'))
