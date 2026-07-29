from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AutomationState:
    enabled: bool
    interval_seconds: int
    last_enqueued_at: datetime | None
    next_run_at: datetime | None
    updated_at: datetime

