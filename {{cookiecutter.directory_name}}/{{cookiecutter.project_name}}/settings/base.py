"""
Django settings for the {{cookiecutter.project_name}} project.

For more information on this file, see
https://docs.djangoproject.com/en/stable/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/stable/ref/settings/
"""
import os
import datetime
import tomllib
from pathlib import Path

import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
ENV_FILE = os.path.join(BASE_DIR, '.env')
PRIVATE_DIR = os.path.join(BASE_DIR, 'private')
BUILD_FILE = Path(f"{BASE_DIR}/BUILD.txt")

# .env
if os.path.exists(ENV_FILE):
    load_dotenv(dotenv_path=ENV_FILE, verbose=True)

INSTANCE_NAME = os.getenv('INSTANCE_NAME', '{{cookiecutter.project_name}}')

if BUILD_FILE.exists():
    with open(BUILD_FILE) as f:
        BUILD = f.readline().replace('\n', '')
else:
    BUILD = datetime.datetime.now().isoformat()

with open(BASE_DIR / "pyproject.toml", "rb") as f:
    _META = tomllib.load(f)

VERSION = _META["tool"]["poetry"]["version"]

# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("The SECRET_KEY environment variable must be set.")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

IS_ENABLED_ANONYMOUS_USER = False


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',

    'django_api_forms',

    'apps.core',
    'apps.api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'apps.api.middleware.exceptions.ExceptionMiddleware',
]

ROOT_URLCONF = '{{cookiecutter.project_name}}.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = '{{cookiecutter.project_name}}.wsgi.application'


# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': os.getenv('PGHOST'),
        'PORT': os.getenv('PGPORT', 5432),
        'NAME': os.getenv('PGDATABASE'),
        'USER': os.getenv('PGUSER'),
        'PASSWORD': os.getenv('PGPASSWORD', None)
    }
}


# Django object checker

OBJECT_CHECKERS_MODULE = 'apps.core.checkers'


# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

SECURED_VIEW_AUTHENTICATION_SCHEMAS = {
    'Basic': 'apps.core.auth.BasicBackend',
    'Bearer': 'apps.core.auth.BearerBackend'
}

TOKEN_EXPIRATION = datetime.timedelta(days=7)

RECOVERY_TIME_EXPIRATION = 1

AUTH_USER_MODEL = "core.User"

# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = 'en'

TIME_ZONE = 'UTC'

DATETIME_INPUT_FORMATS = ('%Y-%m-%dT%H:%M:%S%z',)

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 50  # 50MB


# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        # Avoid SQL query spam when the root level is DEBUG.
        'django.db.backends': {
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Sentry
if os.getenv('SENTRY_DSN', False):
    def before_send(event, hint):
        if 'exc_info' in hint:
            exc_type, exc_value, tb = hint['exc_info']
            if exc_type.__name__ in ['ValidationException']:
                return None
        if 'extra' in event and not event['extra'].get('to_sentry', True):
            return None

        return event

    sentry_sdk.init(
        integrations=[DjangoIntegration()],
        attach_stacktrace=True,
        # Avoid shipping request bodies, cookies and user PII to Sentry by default.
        # send_default_pii=False,
        before_send=before_send,
    )

# Pagination
PAGINATION = {
    'DEFAULT_LIMIT': 10
}


# Notifications
EMAIL_SENDER_NAME = os.getenv('EMAIL_SENDER_NAME')
EMAIL_IMAP_USER = os.getenv('EMAIL_IMAP_USER')


# Templates
EMAIL_REGISTRATION_PATH = '_emails/registration.html'
EMAIL_RECOVERY_PATH = '_emails/password_recovery.html'
