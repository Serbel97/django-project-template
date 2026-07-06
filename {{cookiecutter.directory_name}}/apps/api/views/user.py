from http import HTTPStatus
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils.translation import gettext as _
from object_checker.base_object_checker import has_object_permission

from apps.api.errors import ValidationException, ProblemDetailException
from apps.api.filters.user import UserFilter
from apps.api.forms.user import UserForm
from apps.api.response import SingleResponse, PaginationResponse
from apps.api.views.base import SecuredView
from apps.core.models.recovery_code import RecoveryCode
from apps.core.models.user import User
from apps.core.serializers.user import UserSerializer
from apps.core.services.email_notification import NotificationEmailService


class UserManagement(SecuredView):
    EXEMPT_AUTH = ['POST']

    @transaction.atomic
    def post(self, request):
        form = UserForm.Create.create_from_request(request)

        if not form.is_valid():
            raise ValidationException(form)

        user = User()
        form.populate(user)
        user.set_unusable_password()
        user.save()

        recovery_code = RecoveryCode.objects.create(user=user)

        NotificationEmailService.create(
            recipients=[f'{user.get_full_name()} <{user.email}>'],
            subject=_('Registration'),
            content={
                'recovery_code': recovery_code,
                'login_url': request.build_absolute_uri(
                    reverse('recovery-code-id', kwargs={'recovery_code_id': recovery_code.pk})
                ),
            },
            template=settings.EMAIL_REGISTRATION_PATH,
        ).send_email()

        return SingleResponse(request, data=user, serializer=UserSerializer.Detail, status=HTTPStatus.CREATED)

    def get(self, request):
        users = UserFilter(request.GET, queryset=User.objects.all(), request=request).qs

        return PaginationResponse(request, users, serializer=UserSerializer.Base)


class UserDetail(SecuredView):
    @staticmethod
    def _get_user(request, user_id: UUID, perm: str) -> User:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as e:
            raise ProblemDetailException(_('User not found.'), status=HTTPStatus.NOT_FOUND, previous=e)

        # A user may always act on their own record; otherwise the matching model permission is required.
        if request.user != user and not request.user.has_perm(perm):
            raise ProblemDetailException(_('Permission denied.'), status=HTTPStatus.FORBIDDEN)

        return user

    def get(self, request, user_id: UUID):
        user = self._get_user(request, user_id, 'core.view_user')

        return SingleResponse(request, data=user, serializer=UserSerializer.Detail)

    @transaction.atomic
    def put(self, request, user_id: UUID):
        form = UserForm.Update.create_from_request(request)

        if not form.is_valid():
            raise ValidationException(form)

        user = self._get_user(request, user_id, 'core.change_user')

        if User.objects.filter(email__iexact=form.cleaned_data['email']).exclude(pk=user.id).exists():
            raise ProblemDetailException(
                _('User with the same email already exists.'), status=HTTPStatus.CONFLICT
            )

        form.populate(user)
        user.save()

        return SingleResponse(request, data=user, serializer=UserSerializer.Detail)

    @transaction.atomic
    def delete(self, request, user_id: UUID):
        user = self._get_user(request, user_id, 'core.delete_user')
        user.is_active = False
        user.delete()

        return SingleResponse(request)


class UserMe(SecuredView):
    def get(self, request):
        return SingleResponse(request, data=request.user, serializer=UserSerializer.Me)


class ChangePasswordDetail(SecuredView):
    @staticmethod
    def _get_user(request, user_id: UUID) -> User:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as e:
            raise ProblemDetailException(_('User not found.'), status=HTTPStatus.NOT_FOUND, previous=e)

        if not has_object_permission('check_user_get', user=request.user, obj=user):
            raise ProblemDetailException(_('Permission denied.'), status=HTTPStatus.FORBIDDEN)

        return user

    def patch(self, request, user_id: UUID):
        form = UserForm.ChangePasswordForm.create_from_request(request)

        if not form.is_valid():
            raise ValidationException(form)

        user = self._get_user(request, user_id)

        user.set_password(form.cleaned_data['new_password'])
        user.save()

        return SingleResponse(request)
