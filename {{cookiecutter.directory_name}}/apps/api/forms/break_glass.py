from django.forms import fields
from django_api_forms import Form


class BreakGlassForm:
    class Login(Form):
        email = fields.EmailField(required=True, label='Email')
        password = fields.CharField(required=True, max_length=128, label='Password')

    class Verify(Form):
        challenge_id = fields.UUIDField(required=True, label='Challenge')
        code = fields.CharField(required=True, max_length=32, label='Code')
