from datetime import date, datetime, timedelta

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

    def overdue_charges_total(self, reference_date: date) -> int:
        return self._pending_charges_in_range(due_before=reference_date)

    def charges_due_today_total(self, reference_date: date) -> int:
        return self._pending_charges_in_range(
            due_from=reference_date,
            due_to=reference_date,
        )

    def charges_due_next_7_days_total(self, reference_date: date) -> int:
        return self._pending_charges_in_range(
            due_from=reference_date + timedelta(days=1),
            due_to=reference_date + timedelta(days=7),
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

    def _pending_charges_in_range(
        self,
        *,
        due_before: date | None = None,
        due_from: date | None = None,
        due_to: date | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(Charge)
            .where(Charge.status == ChargeStatus.PENDING)
        )
        if due_before is not None:
            statement = statement.where(Charge.due_date < due_before)
        if due_from is not None:
            statement = statement.where(Charge.due_date >= due_from)
        if due_to is not None:
            statement = statement.where(Charge.due_date <= due_to)
        return self._count(statement)
