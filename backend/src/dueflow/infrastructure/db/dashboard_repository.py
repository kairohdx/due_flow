from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dueflow.domain.jobs import JobStatus
from dueflow.domain.charges import ChargeStatus
from dueflow.domain.messaging import NotificationAttemptStatus
from dueflow.infrastructure.db.models import (
    Charge,
    Customer,
    NotificationAttempt,
    ProcessingJob,
)


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

    def pending_charges_total(self) -> int:
        return self._count(
            select(func.count())
            .select_from(Charge)
            .where(Charge.status == ChargeStatus.PENDING)
        )

    def completed_results_since(self, since: datetime) -> list[dict]:
        statement = (
            select(ProcessingJob.result)
            .where(
                ProcessingJob.status == JobStatus.COMPLETED,
                ProcessingJob.finished_at >= since,
                ProcessingJob.result.is_not(None),
            )
        )
        return [
            dict(result)
            for result in self.session.scalars(statement)
            if result is not None
        ]

    def processed_notifications_since(self, since: datetime) -> int:
        return self._count(
            select(func.count())
            .select_from(NotificationAttempt)
            .where(
                NotificationAttempt.status.in_(
                    [
                        NotificationAttemptStatus.SENT,
                        NotificationAttemptStatus.SIMULATED,
                    ]
                ),
                NotificationAttempt.processed_at >= since,
            )
        )

    def failed_notifications_since(self, since: datetime) -> int:
        return self._count(
            select(func.count())
            .select_from(NotificationAttempt)
            .where(
                NotificationAttempt.status
                == NotificationAttemptStatus.FAILED,
                NotificationAttempt.processed_at >= since,
            )
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
