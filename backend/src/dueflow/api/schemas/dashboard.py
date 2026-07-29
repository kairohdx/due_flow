from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
