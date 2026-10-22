from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from apps.core.serializers import Serializer


class AuthSerializer:
    class TwoFactorRequired(Serializer):
        challenge_id: UUID
        method: str
        expires_at: datetime

    class TotpProvision(Serializer):
        secret: str
        otpauth_uri: str

    class BackupCodes(Serializer):
        backup_codes: List[str] = Field(default_factory=list)

    class Config(Serializer):
        password_login_enabled: bool
        password_reset_enabled: bool
        registration_enabled: bool
        sso_enabled: bool
        sso_provider_id: Optional[str] = Field(default=None)
