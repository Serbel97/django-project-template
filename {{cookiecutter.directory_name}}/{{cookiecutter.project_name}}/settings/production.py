from .base import *

TIME_ZONE = 'Europe/Bratislava'

# Comma-separated list of hostnames, e.g. ALLOWED_HOSTS="api.example.com,www.example.com"
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '').split(',') if host.strip()]

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if origin.strip()
]

# HTTPS / proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS (enable once you are sure every subdomain is served over HTTPS)
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', 60 * 60 * 24 * 30))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Misc hardening
SECURE_CONTENT_TYPE_NOSNIFF = True
