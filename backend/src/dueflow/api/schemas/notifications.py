from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from dueflow.domain.messaging import (
    NotificationSubmissionStatus,
    NotificationDeliveryStatus,
    NotificationProvider,
)
from dueflow.domain.meta_errors import MetaErrorAction
from dueflow.domain.notification_recovery import RecoveryAction
from dueflow.domain.notifications import NotificationType


class MetaErrorResponse(BaseModel):
    code: int | None
    title: str
    message: str
    action: str
    action_type: MetaErrorAction
    known: bool
    technical_title: str | None
    technical_details: str | None


class NotificationAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    charge_id: UUID
    processing_job_id: UUID | None
    root_attempt_id: UUID | None
    retry_of_attempt_id: UUID | None
    retry_requested_by_user_id: UUID | None
    attempt_number: int
    notification_type: NotificationType
    provider: NotificationProvider
    destination: str
    message: str
    message_format: str
    template_info: dict[str, Any] | None
    submission_status: NotificationSubmissionStatus
    provider_message_id: str | None
    submission_error_code: int | None
    submission_error_title: str | None
    submission_error_details: str | None
    submission_error_info: MetaErrorResponse | None
    idempotency_key: str
    policy_name: str
    decision_reason: str
    trace: dict[str, Any] | None
    provider_response: dict[str, Any] | None
    delivery_status: NotificationDeliveryStatus
    delivery_event_at: datetime | None
    delivery_updated_at: datetime | None
    delivery_error_code: int | None
    delivery_error_title: str | None
    delivery_error_details: str | None
    delivery_error_info: MetaErrorResponse | None
    delivery_response: dict[str, Any] | None
    processed_at: datetime


class RecoveryAssessmentResponse(BaseModel):
    attempt_id: UUID
    eligible: bool
    action: RecoveryAction
    reason: str
    policy_name: str
    trace: dict[str, Any]
    template_eligible: bool
