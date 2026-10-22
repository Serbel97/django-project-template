"""
Test settings for {{cookiecutter.project_name}}.

Run the suite with:

    python manage.py makemigrations          # once, if you haven't generated migrations yet
    python manage.py test --settings={{cookiecutter.project_name}}.settings.test
"""

import os

from .base import *  # noqa: F401,F403

# NOTE: Django's test runner forces DEBUG = False, so view tests authenticate with
# a real API key + HMAC X-Signature (see apps/tests/base.py), exercising the
# production security path.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.getenv('PGHOST'),
        'PORT': os.getenv('PGPORT', 5432),
        'NAME': os.getenv('PGDATABASE'),
        'USER': os.getenv('PGUSER'),
        'PASSWORD': os.getenv('PGPASSWORD', None),
        'TEST': {
            'NAME': f"test_{os.getenv('PGDATABASE', 'app')}",
        },
    }
}

# SSO switched on against a fictitious IdP; no test talks to it.
OIDC_PROVIDER_ID = 'test-idp'
OIDC_SERVER_URL = 'https://idp.invalid/realms/test'
OIDC_CLIENT_ID = 'test-client'
OIDC_CLIENT_SECRET = 'test-client-secret'
SSO_ENABLED = True
SPA_URL = 'http://spa.test'
SOCIALACCOUNT_PROVIDERS = build_socialaccount_providers(  # noqa: F405
    OIDC_PROVIDER_ID, OIDC_SERVER_URL, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_SCOPES  # noqa: F405
)
HEADLESS_FRONTEND_URLS = {'socialaccount_login_error': f'{SPA_URL}/login/error'}

# Fixed key for encrypted fields; tests that rotate keys override these.
AES_FIELD_KEYS = '1:MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='
AES_FIELD_KEY_VERSION = None

# Collect e-mails in django.core.mail.outbox instead of sending them.
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Fast, deterministic password hashing for tests.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
