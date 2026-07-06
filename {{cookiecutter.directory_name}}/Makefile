SETTINGS = {{cookiecutter.project_name}}.settings.test
DEV_SETTINGS = {{cookiecutter.project_name}}.settings.development

.PHONY: run test test-keepdb migrations migrate format lint typecheck

run:  ## Start the development server on port 8000
	python manage.py runserver 0.0.0.0:8000 --settings=$(DEV_SETTINGS)

test:  ## Run the test suite
	python manage.py test apps.tests --settings=$(SETTINGS)

test-keepdb:  ## Run the test suite, keeping the test database between runs
	python manage.py test apps.tests --keepdb --settings=$(SETTINGS)

migrations:  ## Generate migrations (required once before the first test run)
	python manage.py makemigrations

migrate:  ## Apply migrations to the development database
	python manage.py migrate --settings=$(DEV_SETTINGS)

format:  ## Format code with Black
	black .

lint:  ## Lint with flake8
	flake8 apps/

typecheck:  ## Type-check with mypy
	mypy apps/