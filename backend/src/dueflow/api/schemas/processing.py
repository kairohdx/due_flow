from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from dueflow.domain.jobs import JobRecord, JobStatus, JobType
from dueflow.domain.messaging import NotificationSubmissionStatus
from dueflow.domain.notifications import (
    DecisionKind,
    NotificationAction,
    NotificationType,
)


class ProcessingRequest(BaseModel):
    reference_date: date | None = None


class JobAcceptedResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    created: bool


class JobDecisionResponse(BaseModel):
    decision: DecisionKind
    notification_type: NotificationType | None
    template_key: str | None
    reason: str
    eligible: bool
    recommended_action: NotificationAction
    policy_name: str
    metadata: dict[str, Any]


class JobTraceEntryResponse(BaseModel):
    policy_name: str
    matched: bool
    outcome: str
    reason: str | None
    duration_ms: float | None


class JobTraceResponse(BaseModel):
    trace_id: str
    execution_id: str
    pipeline: str
    strategy: str
    status: str
    duration_ms: float
    selected_policy: str
    evaluated: list[JobTraceEntryResponse]
    not_evaluated: list[str]


class JobNotificationResponse(BaseModel):
    attempt_id: UUID
    submission_status: NotificationSubmissionStatus
    provider_message_id: str | None
    idempotency_key: str
    deduplicated: bool
    error: str | None


class JobEvaluationResponse(BaseModel):
    charge_id: UUID
    decision: JobDecisionResponse
    trace: JobTraceResponse
    notification: JobNotificationResponse | None


class JobResultResponse(BaseModel):
    reference_date: date
    evaluated: int
    eligible: int
    skipped: int
    simulated: int
    deduplicated: int
    notification_failed: int
    evaluations: list[JobEvaluationResponse]


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: JobType
    status: JobStatus
    payload: dict[str, Any]
    result: JobResultResponse | None
    origin: str
    charge_id: UUID | None
    terminal: bool
    duration_ms: float | None
    scheduled_for: datetime
    attempts: int
    max_attempts: int
    locked_at: datetime | None
    locked_by: str | None
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    retain_deduplication_key: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, job: JobRecord) -> "JobResponse":
        charge_id_raw = job.payload.get("charge_id")
        duration_ms = None
        if job.started_at is not None and job.finished_at is not None:
            duration_ms = (
                job.finished_at - job.started_at
            ).total_seconds() * 1000
        return cls(
            **{
                field: getattr(job, field)
                for field in (
                    "id",
                    "type",
                    "status",
                    "payload",
                    "result",
                    "scheduled_for",
                    "attempts",
                    "max_attempts",
                    "locked_at",
                    "locked_by",
                    "started_at",
                    "finished_at",
                    "error",
                    "retain_deduplication_key",
                    "created_at",
                    "updated_at",
                )
            },
            origin=str(job.payload.get("origin", "unknown")),
            charge_id=UUID(str(charge_id_raw)) if charge_id_raw else None,
            terminal=job.status in {JobStatus.COMPLETED, JobStatus.FAILED},
            duration_ms=duration_ms,
        )
