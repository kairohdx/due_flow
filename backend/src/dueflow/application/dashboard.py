from dataclasses import dataclass
from datetime import date, datetime, timedelta

from dueflow.domain.jobs import JobStatus
from dueflow.domain.messaging import (
    NotificationDeliveryStatus,
    NotificationSubmissionStatus,
)
from dueflow.infrastructure.db.dashboard_repository import DashboardRepository


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    generated_at: datetime
    window_started_at: datetime
    customers_total: int
    charges_pending: int
    charges_overdue: int
    charges_due_today: int
    charges_due_next_7_days: int
    charges_evaluated_last_24h: int
    submissions_succeeded_last_24h: int
    submissions_failed_last_24h: int
    submissions_unknown_last_24h: int
    deliveries_confirmed_last_24h: int
    deliveries_read_last_24h: int
    deliveries_failed_last_24h: int
    deliveries_awaiting: int
    jobs_queued: int
    jobs_processing: int
    jobs_completed_last_24h: int
    job_retries_last_24h: int
    jobs_failed_last_24h: int


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self.repository = repository

    def summary(
        self,
        *,
        now: datetime,
        reference_date: date | None = None,
    ) -> DashboardSummary:
        window_started_at = now - timedelta(hours=24)
        business_date = reference_date or now.date()
        completed_results = self.repository.completed_results_since(
            window_started_at
        )
        return DashboardSummary(
            generated_at=now,
            window_started_at=window_started_at,
            customers_total=self.repository.customers_total(),
            charges_pending=self.repository.pending_charges_total(),
            charges_overdue=self.repository.overdue_charges_total(business_date),
            charges_due_today=self.repository.charges_due_today_total(business_date),
            charges_due_next_7_days=(
                self.repository.charges_due_next_7_days_total(business_date)
            ),
            charges_evaluated_last_24h=sum(
                int(result.get("evaluated", 0))
                for result in completed_results
            ),
            submissions_succeeded_last_24h=self.repository.submissions_since(
                window_started_at,
                NotificationSubmissionStatus.SUCCEEDED,
            ),
            submissions_failed_last_24h=self.repository.submissions_since(
                window_started_at,
                NotificationSubmissionStatus.FAILED,
            ),
            submissions_unknown_last_24h=self.repository.submissions_since(
                window_started_at,
                NotificationSubmissionStatus.UNKNOWN,
            ),
            deliveries_confirmed_last_24h=self.repository.deliveries_since(
                window_started_at,
                NotificationDeliveryStatus.DELIVERED,
                NotificationDeliveryStatus.READ,
            ),
            deliveries_read_last_24h=self.repository.deliveries_since(
                window_started_at,
                NotificationDeliveryStatus.READ,
            ),
            deliveries_failed_last_24h=self.repository.deliveries_since(
                window_started_at,
                NotificationDeliveryStatus.FAILED,
            ),
            deliveries_awaiting=self.repository.deliveries_awaiting(),
            jobs_queued=self.repository.jobs_with_status(JobStatus.QUEUED),
            jobs_processing=self.repository.jobs_with_status(
                JobStatus.PROCESSING
            ),
            jobs_completed_last_24h=self.repository.completed_since(
                window_started_at
            ),
            job_retries_last_24h=self.repository.retries_since(
                window_started_at
            ),
            jobs_failed_last_24h=self.repository.failures_since(
                window_started_at
            ),
        )
