from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dueflow.api.schemas.common import NonEmptyDescription
from dueflow.domain.charges import ChargeStatus

Money = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2),
]
ReminderDays = Annotated[int, Field(ge=0, le=365)]


class ChargeCreate(BaseModel):
    customer_id: UUID
    description: NonEmptyDescription
    amount: Money
    due_date: date
    reminder_days_before: ReminderDays | None = None


class ChargeUpdate(BaseModel):
    customer_id: UUID
    description: NonEmptyDescription
    amount: Money
    due_date: date
    reminder_days_before: ReminderDays


class ChargeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    description: str
    amount: Decimal
    due_date: date
    status: ChargeStatus
    reminder_days_before: int
    created_at: datetime
    updated_at: datetime
