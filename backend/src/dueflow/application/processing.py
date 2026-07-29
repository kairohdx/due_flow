from datetime import UTC, date, datetime
from uuid import UUID

from dueflow.application.errors import ResourceNotFoundError
from dueflow.application.job_queue import EnqueueResult, JobQueue
from dueflow.domain.jobs import JobRecord, JobStatus, JobType
from dueflow.infrastructure.db.repositories import ChargeRepository


class ProcessingService:
    def __init__(
        self,
        queue: JobQueue,
        charge_repository: ChargeRepository,
        *,
        max_attempts: int,
    ) -> None:
        self.queue = queue
        self.charge_repository = charge_repository
        self.max_attempts = max_attempts

    def enqueue_charge(
        self,
        charge_id: UUID,
        *,
        reference_date: date | None,
    ) -> EnqueueResult:
        if self.charge_repository.get(charge_id) is None:
            raise ResourceNotFoundError("cobrança não encontrada")
        payload = {
            "charge_id": str(charge_id),
            "origin": "manual",
        }
        if reference_date is not None:
            payload["reference_date"] = reference_date.isoformat()
        return self.queue.enqueue(
            job_type=JobType.PROCESS_CHARGE,
            payload=payload,
            scheduled_for=datetime.now(UTC),
            max_attempts=self.max_attempts,
            deduplication_key=f"process_charge:{charge_id}",
        )

    def enqueue_due_charges(
        self,
        *,
        reference_date: date | None,
    ) -> EnqueueResult:
        payload = {"origin": "manual"}
        if reference_date is not None:
            payload["reference_date"] = reference_date.isoformat()
        return self.queue.enqueue(
            job_type=JobType.PROCESS_DUE_CHARGES,
            payload=payload,
            scheduled_for=datetime.now(UTC),
            max_attempts=self.max_attempts,
            deduplication_key="process_due_charges:manual",
        )

    def get_job(self, job_id: UUID) -> JobRecord:
        job = self.queue.get(job_id)
        if job is None:
            raise ResourceNotFoundError("job não encontrado")
        return job

    def list_jobs(
        self,
        *,
        status: JobStatus | None,
        origin: str | None,
        limit: int,
        offset: int,
    ) -> list[JobRecord]:
        return self.queue.list(
            status=status,
            origin=origin,
            limit=limit,
            offset=offset,
        )
