from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generated_at: datetime
    window_started_at: datetime
    customers_total: int
    jobs_queued: int
    jobs_processing: int
    jobs_completed_last_24h: int
    job_retries_last_24h: int
    jobs_failed_last_24h: int
