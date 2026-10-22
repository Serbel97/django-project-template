from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'apps.core'

    def ready(self):
        from apps.core import checks  # noqa: F401  (registers the system checks)
