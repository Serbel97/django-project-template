# {{cookiecutter.directory_name}}

{{cookiecutter.description}}


### Information

- Using [PEP8](https://peps.python.org/pep-0008/) code style.
- Using **Semantic Commit Messages** described [here](https://gist.github.com/joshbuchea/6f47e86d2510bce28f8e7f42ae84c716) or in more detail [here](https://www.freecodecamp.org/news/how-to-write-better-git-commit-messages/).


## Database basic setup

### Load data from fixtures to DB:
`python manage.py loaddata [fixture ...]`

### Dump data from DB to fixtures:
`python manage.py dumpdata core.<ModelClassName> --indent 4 > apps/core/fixtures/<TableName>.json`

### Dump data from DB to fixtures:
`python manage.py dumpdata core.<ModelClassName> --indent 4 > apps/core/fixtures/<TableName>.json`

### Dump schema
MAC OS

`PGPASSWORD="PWD" pg_dump --file "/Users/<USER>/<PATH>/<FILE_NAME>.sql" --host "<HOST>" --port "<PORT>" --username "<USERNAME>" --verbose --format=c --blobs --no-owner --section=pre-data --section=data --section=post-data --no-privileges --no-tablespaces --no-unlogged-table-data --no-comments "<DB_NAME>"`

### Restore schema
MAC OS

`pg_restore --host "<HOST>" --port "<PORT>" --username "<USERNAME>" --no-password --dbname "<DB_NAME>" --verbose "/Users/<USER>/<PATH>/<FILE_NAME>.sql"`

`psql -U <USERNAME> -d <DB_NAME> -f <FILE_NAME>.sql`


## Translations
- make .po file
```BASH
python manage.py makemessages -l <language:sk>
```
- compie translations | do not push
```BASH
python manage.py compilemessages -l <language:sk>
```
- set the default language in settings base
```python
LANGUAGE_CODE = '<language:sk>'
```

## Email notifications

To send email notifications in views, you need to import `NotificationEmailService`.
However, you need to check email template in `templates/_emails/`.

All email IMAP settings are loaded from environment variables, so go  check `.env.example` and change your `.env` accordingly.

```python
from apps.core.services.email_notification import NotificationEmailService


NotificationEmailService.create(
    recipients=['adamzurek14@gmail.com'],
    subject='Test',
    content={
        'title': 'Welcome 🥰',
        'content': 'Welcome to template project.',
        'sub_content': "It ain't much, but it's honest work! 💀"
    },
    template='_emails/base.html',
).send_email()
```


### Filters

Filtering is performed using a library [django_filter](https://github.com/carltongibson/django-filter).
Access control is performed to limit objects in the `queryset` according to the specific user right in
property `qs`.

### ObjectChecker

[django-object-checker](https://github.com/zurek11/django-object-checker) is used to check if the user has
the right to access the object.

The individual `ObjectCheckers` are located in the folder according to the settings:

`OBJECT_CHECKERS_MODULE = 'apps.core.checkers'`

Implementation of `ObjectCheckers` and their use is explained in detail in the `README.md` file.


## Usage

### Class-based Views

> To deny checking process in the class-based view, you need to specify, which method you want to mark.
> There are two levels of skipping auth check:
> 1. **EXEMPT_AUTH**: skips user authentication (auth header is no longer needed).
> 2. **EXEMPT_API_KEY**: skips request authentication (signature, api_key).

```python
from apps.api.views.base import SecuredView


class ExampleClassBasedView(SecuredView):
    EXEMPT_AUTH = ['GET']
    EXEMPT_API_KEY = ['GET', 'POST']
    REQUIRE_SUPERUSER = ['POST']

    def post(self, request):
        pass

    def get(self, request):
        pass
```

## Authentication

Users log in with their e-mail and password (`POST /token`) and get a Bearer token. With two-factor authentication
enabled, the login answers `202` with a challenge, and `POST /auth/2fa/verify` returns the token. Two factors are
supported: an authenticator app (TOTP, enrolled with `POST /auth/2fa` and confirmed with `POST /auth/2fa/confirm`)
and an e-mailed one-time code. Backup codes are issued on enrolment and can be regenerated.

Three switches in `settings/base.py` (environment variables of the same name, default `true`) turn paths off.
A disabled path is not registered at all:

| Switch                        | Routes                                                                  |
|-------------------------------|-------------------------------------------------------------------------|
| `PASSWORD_LOGIN_ENABLED`      | `/token`, `/auth/2fa*`                                                  |
| `AUTH_PASSWORD_RESET_ENABLED` | `/recovery_code*`, `/users/<id>/password`                              |
| `AUTH_REGISTRATION_ENABLED`   | `POST /users` (the path stays for `GET`, and the POST answers 404)     |

`GET /auth/config` reports the switches so a client can render only the enabled login paths.

### Single sign-on (OpenID Connect)

Set `OIDC_PROVIDER_ID` (plus `OIDC_SERVER_URL`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`) and users can log in at
any OIDC identity provider (Keycloak, Microsoft Entra ID, ...) through
[django-allauth](https://docs.allauth.org/) in headless mode. Without `OIDC_PROVIDER_ID` the SSO routes do
not exist. The flow for the SPA:

1. `POST /_allauth/browser/v1/auth/provider/redirect` (form post: `provider=<OIDC_PROVIDER_ID>`,
   `process=login`, `callback_url=<SPA page>`) sends the browser to the IdP.
2. The IdP calls back `/accounts/oidc/<OIDC_PROVIDER_ID>/login/callback/`; the API creates or refreshes the
   user and redirects to `callback_url` with a session cookie.
3. The SPA calls `POST /api/v1/auth/sso/token` once (API key + signature as usual, plus the `X-CSRFToken`
   header from the `csrftoken` cookie). The answer is a Bearer token and the session ends, so the rest of
   the API works exactly as after `POST /token`.

The user is keyed by the IdP's subject (`sub`); e-mail, name and surname are refreshed at every login, and
the groups claim (`OIDC_GROUPS_CLAIM`, default `groups`) is stored on `User.idp_groups`. There is no account
linking by e-mail: an IdP that asserts the e-mail of an existing account is refused. Refused logins land on
`<SPA_URL>/login/error?error=<code>` (`email_missing`, `email_conflict`). Logout ends the API token only, not
the IdP session. Second factors are left to the IdP.

IdP onboarding checklist:

- issuer URL with `.well-known/openid-configuration` discovery → `OIDC_SERVER_URL`
- a confidential client → `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`
- redirect URI `https://<api-host>/accounts/oidc/<OIDC_PROVIDER_ID>/login/callback/`
- scopes `openid email profile` (`OIDC_SCOPES`), plus whatever releases the groups claim
- the SPA origin in `SPA_URL`; it is trusted for CSRF. A SPA on another site also needs CORS with credentials.

Future option (not implemented): an account lockout after repeated failed logins. Today the only limit is the
per-challenge cap of wrong two-factor codes (`TWO_FACTOR_MAX_ATTEMPTS`). A lockout would count failed password and
code attempts per account and refuse logins for a set time.


## Cron jobs

- `crontab -l` list all cron jobs
- `crontab -e` create new cron jobs

Rules generated by [crontab.guru](https://crontab.guru/).

| Active | Name                           | Rule          | Description                                               |
|--------|--------------------------------|---------------|-----------------------------------------------------------|
| True   | `example_job`                  | `30 * * * *`  | Example CRON job                                          |

---
Made with ❤️ and ☕️ BACKBONE, s.r.o. (c) {% now 'utc', '%Y' %}
