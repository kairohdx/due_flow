from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from dueflow.domain.messaging import (
    NotificationAttemptStatus,
    NotificationProvider,
)
from dueflow.domain.notifications import NotificationType


class NotificationAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    charge_id: UUID
    processing_job_id: UUID | None
    notification_type: NotificationType
    provider: NotificationProvider
    destination: str
    message: str
    status: NotificationAttemptStatus
    provider_message_id: str | None
    error: str | None
    idempotency_key: str
    policy_name: str
    decision_reason: str
    trace: dict[str, Any] | None
    provider_response: dict[str, Any] | None
    processed_at: datetime
