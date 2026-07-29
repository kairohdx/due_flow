from dataclasses import dataclass
from datetime import datetime, timedelta

from dueflow.domain.jobs import JobStatus
from dueflow.infrastructure.db.dashboard_repository import DashboardRepository


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    generated_at: datetime
    window_started_at: datetime
    customers_total: int
    jobs_queued: int
    jobs_processing: int
    jobs_completed_last_24h: int
    job_retries_last_24h: int
    jobs_failed_last_24h: int


class DashboardService:
    def __init__(self, repository: DashboardRepository) -> None:
        self.repository = repository

    def summary(self, *, now: datetime) -> DashboardSummary:
        window_started_at = now - timedelta(hours=24)
        return DashboardSummary(
            generated_at=now,
            window_started_at=window_started_at,
            customers_total=self.repository.customers_total(),
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
