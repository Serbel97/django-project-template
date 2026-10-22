from django.forms import fields
from django_api_forms import Form

from apps.core.models.user import User


class TwoFactorForm:
    class Enable(Form):
        method = fields.ChoiceField(choices=User.TwoFactorMethod.choices, required=True, label='Method')

    class Confirm(Form):
        code = fields.CharField(required=True, max_length=16, label='Code')

    class Verify(Form):
        challenge_id = fields.UUIDField(required=True, label='Challenge')
        code = fields.CharField(required=True, max_length=32, label='Code')
