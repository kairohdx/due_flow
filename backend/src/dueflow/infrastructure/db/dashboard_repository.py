from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dueflow.domain.jobs import JobStatus
from dueflow.infrastructure.db.models import Customer, ProcessingJob


class DashboardRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def customers_total(self) -> int:
        return self._count(select(func.count()).select_from(Customer))

    def jobs_with_status(self, status: JobStatus) -> int:
        return self._count(
            select(func.count())
            .select_from(ProcessingJob)
            .where(ProcessingJob.status == status)
        )

    def completed_since(self, since: datetime) -> int:
        return self._count(
            select(func.count())
            .select_from(ProcessingJob)
            .where(
                ProcessingJob.status == JobStatus.COMPLETED,
                ProcessingJob.finished_at >= since,
            )
        )

    def retries_since(self, since: datetime) -> int:
        return self._count(
            select(func.count())
            .select_from(ProcessingJob)
            .where(
                ProcessingJob.attempts > 1,
                ProcessingJob.started_at >= since,
            )
        )

    def failures_since(self, since: datetime) -> int:
        return self._count(
            select(func.count())
            .select_from(ProcessingJob)
            .where(
                ProcessingJob.status == JobStatus.FAILED,
                ProcessingJob.finished_at >= since,
            )
        )

    def _count(self, statement) -> int:
        return int(self.session.scalar(statement) or 0)
