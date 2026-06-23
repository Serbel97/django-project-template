# Changelog

## 0.6.0 : 2026-06-23

### Upgrades
- Django 6 and Python 3.14
- Dependency bumps (django-filter, argon2-cffi, black 25)
- Standard PostgreSQL `PG*` environment variables (`PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`)

### Security & bug fixes
- Fixed `BasicBackend` (base64 decode of credentials)
- Added authorization to `UserDetail` (self-or-permission) and corrected the `UserChecker` logic
- `default_permissions` now include `view`/`change` so `core.view_user` exists
- `order_by` allow-list (`Model.ORDERING_FIELDS`) to prevent ordering injection
- Token expiry computed at creation via `TokenManager`
- Added CSRF middleware (API views are `csrf_exempt`) and production security settings (HSTS, secure cookies, SSL redirect, `ALLOWED_HOSTS` from env)
- `SECRET_KEY` now required (raises `ImproperlyConfigured` if missing)

### Deployment fixes
- `supervisor.conf` uses the project's WSGI module (was hard-coded)
- Aligned `supervisord` config path between Dockerfile and entrypoint
- Fixed `docker-compose.yml` database credentials, volumes and healthcheck

### Documentation
- mkdocs-material documentation site with the proposal (IP) system and `.authors.yml`
- `/ip` skill for quick proposal capture

### Testing
- Django `unittest` test suite covering API views, services and database behaviour (soft-delete, token expiry, managers, ordering)

## 0.5.0 : 2024-14-10

- Remove request from exceptions
- Change password operation to recovery-code to be declarative
- Remove BASE_URL from settings

## 0.4.0 : 2024-06-09

- Updated SecuredView
- Updated authentication
- Updated Dockerfile
- Added user CRUD
- Introduces pydantic
- Introduces black
- Removed flake8
- Django 5.0
- Added Postman template

## 0.3.0 : 2022-03-17

- Updated SecuredView
- Updated authentication
- Added Docker file

## 0.2.0 : 2022-01-28

- Model mixins merged back to the BaseModel
- Multiple column sort
- Django 4.0
- INSTANCE_NAME environment variable

## 0.1.0 : 2021-05-26

Initial release with:

- [django_api_forms](https://github.com/Sibyx/django_api_forms): Request validation
- [python-dotenv](https://github.com/theskumar/python-dotenv): `.env` handling
- [porcupine-python](https://github.com/zurek11/porcupine-python): Response serialisation
- [django-imap-backend](https://github.com/Sibyx/django-imap-backend): Custom e-mail backend for simplified testing
- [django-celery-beat](https://github.com/celery/django-celery-beat): CRON jobs
