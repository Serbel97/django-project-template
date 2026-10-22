from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import Field

from apps.core.serializers import Serializer


class UserSerializer:
    class Base(Serializer):
        id: UUID
        email: str
        name: str
        surname: str
        last_login: Optional[datetime] = Field(default=None)
        created_at: datetime

    class Detail(Base):
        is_active: bool

    class Me(Detail):
        idp_groups: List[str] = Field(default_factory=list)
