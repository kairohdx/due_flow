from datetime import UTC, datetime

from dueflow.domain.automation import AutomationState
from dueflow.infrastructure.db.automation_repository import (
    AutomationRepository,
)


class AutomationService:
    def __init__(
        self,
        repository: AutomationRepository,
    ) -> None:
        self.repository = repository

    def get(self) -> AutomationState:
        return self.repository.get()

    def enable(
        self,
        *,
        interval_seconds: int | None,
    ) -> AutomationState:
        return self.repository.enable(
            now=datetime.now(UTC),
            interval_seconds=interval_seconds,
        )

    def disable(self) -> AutomationState:
        return self.repository.disable(now=datetime.now(UTC))

