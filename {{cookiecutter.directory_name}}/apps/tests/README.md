# {{cookiecutter.project_name}} Tests

End-to-end and unit tests for the API, written with Django's built-in `unittest`
framework (`django.test.TestCase`). No external test dependencies.

## Structure

```
apps/tests/
├── base.py                 # Base test case: signed HTTP helpers + auth
├── fixtures.py             # UserFixture factory helpers
├── api/
│   ├── auth/               # token login / logout
│   ├── user/               # registration, list, detail, me, change password
│   ├── recovery/           # recovery code request + reset
│   └── status/             # public status endpoint
├── services/               # NotificationEmailService
└── db/                     # soft-delete, token expiry, managers, ordering
```

## Running

The suite uses the test settings and the `PG*` environment variables (see
`.env.example`). The test database is created automatically as `test_<PGDATABASE>`.

Always pass the **`apps.tests`** label (or use `make test`). Bare `manage.py test`
discovers nothing, and `manage.py test apps` fails with a "Conflicting models" error.

```bash
# Once, if you haven't generated migrations yet:
make migrations          # == python manage.py makemigrations

# Run everything:
make test                # == python manage.py test apps.tests --settings={{cookiecutter.project_name}}.settings.test

# A subset / single test, keep the DB between runs while iterating:
python manage.py test apps.tests.api.auth --keepdb --settings={{cookiecutter.project_name}}.settings.test
```

## Authentication in tests

Every endpoint extends `SecuredView`, which requires an `X-Apikey` header plus a
matching `X-Signature` (HMAC-SHA256 of `"<body>:<path>"`). `Base` provisions a
test API key and signs every request automatically, so tests just call
`self.get/post/put/patch/delete`.

For endpoints that also need a logged-in user, create one and pass the Bearer
header from `self.authenticate(user)`:

```python
from apps.tests.base import Base
from apps.tests.fixtures import UserFixture


class TestExample(Base):
    def test_me(self):
        user = UserFixture.create_user(email="someone@example.com")
        response = self.get("/api/v1/users/me", headers=self.authenticate(user))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_dict["response"]["email"], user.email)
```

`response.content_dict` holds the parsed JSON body.

## Notes

- E-mails are captured in `django.core.mail.outbox` (locmem backend).
- Tests run with `DEBUG = False` (forced by the test runner), so the API-key
  signature path is exercised exactly as in production.
