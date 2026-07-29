from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from dueflow.domain.jobs import JobStatus, JobType


class ProcessingRequest(BaseModel):
    reference_date: date | None = None


class JobAcceptedResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    created: bool


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: JobType
    status: JobStatus
    payload: dict[str, Any]
    result: dict[str, Any] | None
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
