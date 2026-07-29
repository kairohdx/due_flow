from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generated_at: datetime
    window_started_at: datetime
    customers_total: int
    charges_pending: int
    charges_evaluated_last_24h: int
    notifications_processed_last_24h: int
    notification_failures_last_24h: int
    jobs_queued: int
    jobs_processing: int
    jobs_completed_last_24h: int
    job_retries_last_24h: int
    jobs_failed_last_24h: int
