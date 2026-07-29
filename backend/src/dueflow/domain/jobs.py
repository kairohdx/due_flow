from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class JobType(str, Enum):
    PROCESS_CHARGE = "process_charge"
    PROCESS_DUE_CHARGES = "process_due_charges"


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class JobRecord:
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
