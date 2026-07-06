from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.forms import fields
from django.utils.translation import gettext as _
from django_api_forms import Form

from apps.core.models.user import User


class UserForm:
    class Update(Form):
        name = fields.CharField(required=True, max_length=30, label="Name")
        surname = fields.CharField(required=True, max_length=150, label="Surname")
        email = fields.EmailField(required=True, label="Email")

        def clean_email(self):
            email = self.cleaned_data['email'].strip().lower()
            return email

    class Create(Update):
        def clean_email(self):
            email = self.cleaned_data['email'].strip().lower()
            if User.all_objects.filter(email__iexact=email).exists():
                self.add_error(
                    ('email',),
                    ValidationError(_('User with the same email already exists.'), code='email-already-exists')
                )

            return email

    class ChangePasswordForm(Form):
        old_password = fields.CharField(required=True, label="Old Password")
        new_password = fields.CharField(required=True, validators=[validate_password], label="New Password")

        def clean_old_password(self):
            old_password = self.cleaned_data['old_password']
            if not self._request.user.check_password(old_password):
                self.add_error(
                    ('old_password',), ValidationError(_('Current password do not match with old password.'))
                )

            return old_password
