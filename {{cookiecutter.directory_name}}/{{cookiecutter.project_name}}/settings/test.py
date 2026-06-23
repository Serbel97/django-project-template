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

# Collect e-mails in django.core.mail.outbox instead of sending them.
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Fast, deterministic password hashing for tests.
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
