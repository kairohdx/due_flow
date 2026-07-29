from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from dueflow.domain.jobs import JobRecord, JobStatus, JobType


@dataclass(frozen=True, slots=True)
class EnqueueResult:
    job: JobRecord
    created: bool


class JobQueue(Protocol):
    def enqueue(
        self,
        *,
        job_type: JobType,
        payload: dict[str, Any],
        scheduled_for: datetime,
        max_attempts: int,
        deduplication_key: str | None = None,
        retain_deduplication_key: bool = False,
    ) -> EnqueueResult: ...

    def get(self, job_id: UUID) -> JobRecord | None: ...

    def list(
        self,
        *,
        status: JobStatus | None,
        origin: str | None,
        limit: int,
        offset: int,
    ) -> list[JobRecord]: ...

    def claim(self, *, worker_id: str, now: datetime) -> JobRecord | None: ...

    def complete(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        result: dict[str, Any],
        now: datetime,
    ) -> None: ...

    def fail(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        error: str,
        now: datetime,
        retry_delay: timedelta,
    ) -> None: ...

    def recover_stale(
        self,
        *,
        now: datetime,
        lock_ttl: timedelta,
    ) -> int: ...
