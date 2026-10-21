from .base import *

TIME_ZONE = 'Europe/Bratislava'

# Comma-separated list of hostnames, e.g. ALLOWED_HOSTS="api.example.com,www.example.com"
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '').split(',') if host.strip()]

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()
]
# The SPA sends X-CSRFToken from its own origin when it swaps the SSO session for a token
if os.getenv('SPA_URL') and SPA_URL not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(SPA_URL)

# HTTPS / proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Misc hardening
SECURE_CONTENT_TYPE_NOSNIFF = True
