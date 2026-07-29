from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict

from dueflow.api.schemas.common import NonEmptyName
from dueflow.domain.phone import normalize_phone

NormalizedPhone = Annotated[str, AfterValidator(normalize_phone)]


class CustomerWrite(BaseModel):
    name: NonEmptyName
    phone: NormalizedPhone
    active: bool = True


class CustomerCreate(CustomerWrite):
    pass


class CustomerUpdate(CustomerWrite):
    pass


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    phone: str
    active: bool
    created_at: datetime
    updated_at: datetime

