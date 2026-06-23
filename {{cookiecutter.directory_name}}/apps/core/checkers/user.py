from object_checker.base_object_checker import AbacChecker

from apps.core.models import User


class UserChecker(AbacChecker):
    @staticmethod
    def check_user_get(request_user: User, user: User) -> bool:
        # A user may always act on their own record; superusers may act on anyone.
        return request_user == user or request_user.is_superuser
