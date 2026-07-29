from datetime import datetime

from pydantic import BaseModel, Field


class AutomationEnableRequest(BaseModel):
    interval_seconds: int | None = Field(
        default=None,
        ge=1,
        le=86_400,
    )


class AutomationResponse(BaseModel):
    enabled: bool
    interval_seconds: int
    last_enqueued_at: datetime | None
    next_run_at: datetime | None
    updated_at: datetime

