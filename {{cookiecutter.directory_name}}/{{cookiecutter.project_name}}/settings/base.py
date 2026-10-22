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
        BUILD = f.readline().replace("\n", '')
else:
    BUILD = datetime.datetime.now().isoformat()

with open(BASE_DIR / 'pyproject.toml', 'rb') as f:
    _META = tomllib.load(f)

VERSION = _META['tool']['poetry']['version']

# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('The SECRET_KEY environment variable must be set.')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []

IS_ENABLED_ANONYMOUS_USER = False


# Application definition

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django_api_forms',
    # SSO (IP-003): headless OIDC login, see the SSO section below
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.openid_connect',
    'allauth.headless',
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
    'allauth.account.middleware.AccountMiddleware',
    'apps.api.middleware.exceptions.ExceptionMiddleware',
]

ROOT_URLCONF = '{{cookiecutter.project_name}}.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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
        'PASSWORD': os.getenv('PGPASSWORD', None),
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
    # Sessions opened by allauth after an SSO login; never authenticates credentials
    'apps.core.auth.SSOSessionBackend',
]

SECURED_VIEW_AUTHENTICATION_SCHEMAS = {
    'Basic': 'apps.core.auth.BasicBackend',
    'Bearer': 'apps.core.auth.BearerBackend',
}

TOKEN_EXPIRATION = datetime.timedelta(days=7)

RECOVERY_TIME_EXPIRATION = 1

# Authentication switches (IP-003 Q6). All on by default; set one to false to take that path away.
# A disabled switch answers 404 and its routes are not registered (apps/api/urls.py).
# PASSWORD_LOGIN_ENABLED        → POST/DELETE /token, /auth/2fa*  (password login, optional TOTP / e-mail code)
# AUTH_PASSWORD_RESET_ENABLED   → /recovery_code*, PATCH /users/<id>/password
# AUTH_REGISTRATION_ENABLED     → POST /users (self-registration)


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


PASSWORD_LOGIN_ENABLED = _env_flag('PASSWORD_LOGIN_ENABLED', default=True)
AUTH_PASSWORD_RESET_ENABLED = _env_flag('AUTH_PASSWORD_RESET_ENABLED', default=True)
AUTH_REGISTRATION_ENABLED = _env_flag('AUTH_REGISTRATION_ENABLED', default=True)

# SSO (IP-003): one OpenID Connect provider (any OIDC IdP: Keycloak, Entra ID, VIDB, ...) through
# django-allauth in headless mode. On while OIDC_PROVIDER_ID is set; its routes are absent otherwise.
# The SPA starts the login at /_allauth/browser/v1/auth/provider/redirect, the IdP calls back
# /accounts/oidc/<OIDC_PROVIDER_ID>/login/callback/, and the SPA swaps the resulting session for a
# Bearer token at POST /api/v1/auth/sso/token. The client secret is read from the environment only.
OIDC_PROVIDER_ID = os.getenv('OIDC_PROVIDER_ID', '')
OIDC_SERVER_URL = os.getenv('OIDC_SERVER_URL', '')
OIDC_CLIENT_ID = os.getenv('OIDC_CLIENT_ID', '')
OIDC_CLIENT_SECRET = os.getenv('OIDC_CLIENT_SECRET', '')
# Claim carrying the user's groups; stored on User.idp_groups at every login
OIDC_GROUPS_CLAIM = os.getenv('OIDC_GROUPS_CLAIM', 'groups')
# Space-separated scopes; override when the IdP rejects one it does not know
OIDC_SCOPES = os.getenv('OIDC_SCOPES', 'openid email profile').split()
SSO_ENABLED = bool(OIDC_PROVIDER_ID)

# The SPA: refused SSO logins are redirected to <SPA_URL>/login/error?error=<code>
SPA_URL = os.getenv('SPA_URL', 'http://localhost:3000').rstrip('/')


def build_socialaccount_providers(provider_id: str, server_url: str, client_id: str, secret: str, scopes) -> dict:
    """allauth's provider configuration: one OpenID Connect app, or none without a provider id."""
    apps = []
    if provider_id:
        apps.append(
            {
                'provider_id': provider_id,
                'name': 'Single sign-on',
                'client_id': client_id,
                'secret': secret,
                'settings': {'server_url': server_url},
            }
        )
    return {'openid_connect': {'APPS': apps, 'SCOPE': list(scopes), 'OAUTH_PKCE_ENABLED': True}}


SOCIALACCOUNT_PROVIDERS = build_socialaccount_providers(
    OIDC_PROVIDER_ID, OIDC_SERVER_URL, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_SCOPES
)

# allauth: headless only (no HTML views), browser client, social accounts only. Local login stays /token.
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ('browser',)
HEADLESS_FRONTEND_URLS = {
    'socialaccount_login_error': f'{SPA_URL}/login/error',
}
SOCIALACCOUNT_ONLY = True
SOCIALACCOUNT_AUTO_SIGNUP = True
# No account linking by e-mail: an IdP must not take over an existing local account
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False
SOCIALACCOUNT_EMAIL_REQUIRED = False
SOCIALACCOUNT_STORE_TOKENS = False
SOCIALACCOUNT_ADAPTER = 'apps.core.services.auth.sso.SSOSocialAccountAdapter'
ACCOUNT_ADAPTER = 'apps.core.services.auth.sso.NoSignupAccountAdapter'
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = 'email'
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*']
ACCOUNT_EMAIL_VERIFICATION = 'none'

# Encrypted model fields (apps.core.fields.EncryptedField, AES-256-GCM). Comma-separated
# <version>:<base64 32-byte key> pairs; new values use AES_FIELD_KEY_VERSION (the highest version when unset),
# every listed version still decrypts. Rotation: README, "Encryption keys".
AES_FIELD_KEYS = os.getenv('AES_FIELD_KEYS', '')
AES_FIELD_KEY_VERSION = os.getenv('AES_FIELD_KEY_VERSION') or None

# Two-factor authentication
TWO_FACTOR_CODE_EXPIRATION = datetime.timedelta(minutes=10)
TWO_FACTOR_MAX_ATTEMPTS = 5
TWO_FACTOR_BACKUP_CODE_COUNT = 10
EMAIL_TWO_FACTOR_PATH = '_emails/two_factor_code.html'

AUTH_USER_MODEL = 'core.User'

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

STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

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
PAGINATION = {'DEFAULT_LIMIT': 10}


# Notifications
EMAIL_SENDER_NAME = os.getenv('EMAIL_SENDER_NAME', '{{cookiecutter.project_name}}')
EMAIL_IMAP_USER = os.getenv('EMAIL_IMAP_USER')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'false').lower() == 'true'
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = os.getenv('EMAIL_PORT')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_SENDER = os.getenv('EMAIL_HOST_USER')
EMAIL_REPLY_TO = os.getenv('EMAIL_HOST_USER')
DEFAULT_FROM_EMAIL = f'{EMAIL_SENDER_NAME} <{os.getenv("EMAIL_HOST_USER")}>'


# Templates
EMAIL_REGISTRATION_PATH = '_emails/registration.html'
EMAIL_RECOVERY_PATH = '_emails/password_recovery.html'
