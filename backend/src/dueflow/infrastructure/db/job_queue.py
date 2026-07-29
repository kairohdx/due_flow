from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Select, case, select, update
from sqlalchemy.exc import IntegrityError

from dueflow.application.job_queue import EnqueueResult
from dueflow.domain.jobs import JobRecord, JobStatus, JobType
from dueflow.infrastructure.db.database import Database
from dueflow.infrastructure.db.models import ProcessingJob


class DatabaseJobQueue:
    def __init__(self, database: Database) -> None:
        self.database = database

    def enqueue(
        self,
        *,
        job_type: JobType,
        payload: dict[str, Any],
        scheduled_for: datetime,
        max_attempts: int,
        deduplication_key: str | None = None,
        retain_deduplication_key: bool = False,
    ) -> EnqueueResult:
        with self.database.session() as session:
            if deduplication_key is not None:
                existing = session.scalar(
                    select(ProcessingJob).where(
                        ProcessingJob.deduplication_key == deduplication_key
                    )
                )
                if existing is not None:
                    return EnqueueResult(self._record(existing), created=False)

            job = ProcessingJob(
                type=job_type,
                status=JobStatus.QUEUED,
                payload=dict(payload),
                scheduled_for=scheduled_for,
                max_attempts=max_attempts,
                deduplication_key=deduplication_key,
                retain_deduplication_key=retain_deduplication_key,
            )
            session.add(job)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                if deduplication_key is None:
                    raise
                existing = session.scalar(
                    select(ProcessingJob).where(
                        ProcessingJob.deduplication_key == deduplication_key
                    )
                )
                if existing is None:
                    raise
                return EnqueueResult(self._record(existing), created=False)
            session.refresh(job)
            return EnqueueResult(self._record(job), created=True)

    def get(self, job_id: UUID) -> JobRecord | None:
        with self.database.session() as session:
            job = session.get(ProcessingJob, job_id)
            return self._record(job) if job is not None else None

    def list(
        self,
        *,
        status: JobStatus | None,
        origin: str | None,
        limit: int,
        offset: int,
    ) -> list[JobRecord]:
        with self.database.session() as session:
            statement = select(ProcessingJob)
            if status is not None:
                statement = statement.where(ProcessingJob.status == status)
            if origin is not None:
                statement = statement.where(
                    ProcessingJob.payload["origin"].as_string() == origin
                )
            statement = (
                statement.order_by(
                    ProcessingJob.created_at.desc(),
                    ProcessingJob.id,
                )
                .limit(limit)
                .offset(offset)
            )
            return [
                self._record(job)
                for job in session.scalars(statement)
            ]

    def claim(self, *, worker_id: str, now: datetime) -> JobRecord | None:
        with self.database.session() as session:
            candidate: Select[tuple[UUID]] = (
                select(ProcessingJob.id)
                .where(
                    ProcessingJob.status == JobStatus.QUEUED,
                    ProcessingJob.scheduled_for <= now,
                    ProcessingJob.attempts < ProcessingJob.max_attempts,
                )
                .order_by(
                    ProcessingJob.scheduled_for,
                    ProcessingJob.created_at,
                    ProcessingJob.id,
                )
                .limit(1)
            )
            statement = (
                update(ProcessingJob)
                .where(
                    ProcessingJob.id == candidate.scalar_subquery(),
                    ProcessingJob.status == JobStatus.QUEUED,
                )
                .values(
                    status=JobStatus.PROCESSING,
                    attempts=ProcessingJob.attempts + 1,
                    locked_at=now,
                    locked_by=worker_id,
                    started_at=now,
                    error=None,
                    updated_at=now,
                )
                .returning(ProcessingJob.id)
            )
            job_id = session.execute(statement).scalar_one_or_none()
            session.commit()
            if job_id is None:
                return None
            job = session.get(ProcessingJob, job_id)
            if job is None:
                return None
            return self._record(job)

    def complete(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        result: dict[str, Any],
        now: datetime,
    ) -> None:
        with self.database.session() as session:
            statement = (
                update(ProcessingJob)
                .where(
                    ProcessingJob.id == job_id,
                    ProcessingJob.status == JobStatus.PROCESSING,
                    ProcessingJob.locked_by == worker_id,
                )
                .values(
                    status=JobStatus.COMPLETED,
                    result=dict(result),
                    error=None,
                    locked_at=None,
                    locked_by=None,
                    finished_at=now,
                    deduplication_key=case(
                        (
                            ProcessingJob.retain_deduplication_key.is_(True),
                            ProcessingJob.deduplication_key,
                        ),
                        else_=None,
                    ),
                    updated_at=now,
                )
            )
            result_proxy = session.execute(statement)
            if result_proxy.rowcount != 1:
                session.rollback()
                raise RuntimeError("o worker não possui o lock do job")
            session.commit()

    def fail(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        error: str,
        now: datetime,
        retry_delay: timedelta,
    ) -> None:
        with self.database.session() as session:
            job = session.scalar(
                select(ProcessingJob).where(
                    ProcessingJob.id == job_id,
                    ProcessingJob.status == JobStatus.PROCESSING,
                    ProcessingJob.locked_by == worker_id,
                )
            )
            if job is None:
                raise RuntimeError("o worker não possui o lock do job")

            job.error = error[:2000]
            job.locked_at = None
            job.locked_by = None
            job.updated_at = now
            if job.attempts >= job.max_attempts:
                job.status = JobStatus.FAILED
                job.finished_at = now
                if not job.retain_deduplication_key:
                    job.deduplication_key = None
            else:
                job.status = JobStatus.QUEUED
                job.scheduled_for = now + retry_delay
            session.commit()

    def recover_stale(
        self,
        *,
        now: datetime,
        lock_ttl: timedelta,
    ) -> int:
        expired_before = now - lock_ttl
        with self.database.session() as session:
            retryable = session.execute(
                update(ProcessingJob)
                .where(
                    ProcessingJob.status == JobStatus.PROCESSING,
                    ProcessingJob.locked_at < expired_before,
                    ProcessingJob.attempts < ProcessingJob.max_attempts,
                )
                .values(
                    status=JobStatus.QUEUED,
                    scheduled_for=now,
                    locked_at=None,
                    locked_by=None,
                    error="lock do worker expirou; job reenfileirado",
                    updated_at=now,
                )
            ).rowcount
            exhausted = session.execute(
                update(ProcessingJob)
                .where(
                    ProcessingJob.status == JobStatus.PROCESSING,
                    ProcessingJob.locked_at < expired_before,
                    ProcessingJob.attempts >= ProcessingJob.max_attempts,
                )
                .values(
                    status=JobStatus.FAILED,
                    locked_at=None,
                    locked_by=None,
                    error="lock do worker expirou; tentativas esgotadas",
                    finished_at=now,
                    deduplication_key=case(
                        (
                            ProcessingJob.retain_deduplication_key.is_(True),
                            ProcessingJob.deduplication_key,
                        ),
                        else_=None,
                    ),
                    updated_at=now,
                )
            ).rowcount
            session.commit()
            return retryable + exhausted

    @staticmethod
    def _record(job: ProcessingJob) -> JobRecord:
        return JobRecord(
            id=job.id,
            type=job.type,
            status=job.status,
            payload=dict(job.payload),
            result=dict(job.result) if job.result is not None else None,
            scheduled_for=job.scheduled_for,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            locked_at=job.locked_at,
            locked_by=job.locked_by,
            started_at=job.started_at,
            finished_at=job.finished_at,
            error=job.error,
            retain_deduplication_key=job.retain_deduplication_key,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
