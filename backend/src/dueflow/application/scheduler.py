from datetime import datetime
from zoneinfo import ZoneInfo

from dueflow.application.job_queue import EnqueueResult, JobQueue
from dueflow.domain.jobs import JobType
from dueflow.infrastructure.db.automation_repository import (
    AutomationRepository,
)


class AutomationScheduler:
    def __init__(
        self,
        repository: AutomationRepository,
        queue: JobQueue,
        *,
        timezone: str,
        max_attempts: int,
    ) -> None:
        self.repository = repository
        self.queue = queue
        self.timezone = ZoneInfo(timezone)
        self.max_attempts = max_attempts

    def tick(self, *, now: datetime) -> EnqueueResult | None:
        tick = self.repository.claim_due(now=now)
        if tick is None:
            return None

        window = tick.enqueued_at.isoformat()
        return self.queue.enqueue(
            job_type=JobType.PROCESS_DUE_CHARGES,
            payload={
                "origin": "automatic",
                "automation_window": window,
                "reference_date": tick.enqueued_at.astimezone(
                    self.timezone
                ).date().isoformat(),
            },
            scheduled_for=now,
            max_attempts=self.max_attempts,
            deduplication_key=f"automation:{window}",
            retain_deduplication_key=True,
        )

