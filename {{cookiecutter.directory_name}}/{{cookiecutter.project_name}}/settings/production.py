from .base import *

TIME_ZONE = 'Europe/Bratislava'

# Read by the production system check (core.W001); the environment variable cannot change it here
DEPLOYMENT_ENVIRONMENT = 'prod'

# Comma-separated list of hostnames, e.g. ALLOWED_HOSTS="api.example.com,www.example.com"
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '').split(',') if host.strip()]

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()
]

# HTTPS / proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Misc hardening
SECURE_CONTENT_TYPE_NOSNIFF = True
