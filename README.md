# Django project template

Simple quickstart for [Django](https://www.djangoproject.com/)-based projects created as
[cookiecutter](https://github.com/cookiecutter/cookiecutter) template.

## What's inside?

- Exception handling (`ProblemDetailException`, `ValidationException`
  prepared for [django_api_forms](https://github.com/Sibyx/django_api_forms))
- Basic security (signature middleware, Argon password hasher)
- Hard/soft delete for models
- Custom `User` model
- Response objects (`SingleResponse`, `ValidationResponse`)
- [pydantic](https://github.com/pydantic/pydantic) response serialisation
- Custom JSON encoder
- Configuration using `.env` files
- [Sentry](https://sentry.io/welcome) integration
- Dependency management using [poetry](https://python-poetry.org/)
- Multi-environment settings
- E-mail testing using [django-imap-backend](https://github.com/Sibyx/django-imap-backend) in `development` environment

### Bundled dependencies

- [django_api_forms](https://github.com/Sibyx/django_api_forms): Request validation
- [python-dotenv](https://github.com/theskumar/python-dotenv): `.env` handling
- [pydantic](https://github.com/pydantic/pydantic): Response serialisation
- [django-imap-backend](https://github.com/Sibyx/django-imap-backend): Custom e-mail backend for simplified testing

## Usage

You need to have installed [cookiecutter](https://github.com/cookiecutter/cookiecutter) in your system, then you can
call. You will be asked a few questions about the new project (name, target directory):

```shell
cookiecutter gh:backbonesk/django-project-template
```

## Next steps

1. Check `pyproject.toml` and change the `authors` list
2. `cd <directory_name>`
3. `poetry install && poetry update`
4. Remove stuff you don't need (template is feature rich on purpose, it's easier to delete than create)
5. Copy `.env.example` to `.env` and fill it in — in particular set a `SECRET_KEY`
   (generate one at <https://djecrety.ir/>) and the `PG*` database variables.
   **`SECRET_KEY` is required: every `manage.py` command fails without it.**
6. Create the PostgreSQL database matching `PGDATABASE` (e.g. `createdb <name>`)
7. Call `python manage.py makemigrations && python manage.py migrate`
8. Create a superuser: `python manage.py createsuperuser` (prompts for email, name, surname, password)
9. Start the server with `make run` (or `python manage.py runserver 0.0.0.0:8000`), then call
   `curl http://localhost:8000/api/v1/status` to check everything is up and running
10. (optional) Run the test suite with `make test`
11. Take a coffee and celebrate life, you saved a plenty of time!
---
Made with ❤️ and ☕️ BACKBONE, s.r.o. (c) 2026
