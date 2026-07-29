from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from dueflow.domain.messaging import NotificationDeliveryStatus
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)
from dueflow.infrastructure.db.database import Database


@dataclass(frozen=True, slots=True)
class FakeDeliveryResult:
    advanced: int


class FakeDeliverySimulator:
    def __init__(
        self,
        database: Database,
        *,
        outcome: Literal["delivered", "read", "failed"] = "delivered",
        delay_seconds: float = 2,
        error_code: int = 131047,
    ) -> None:
        self.database = database
        self.outcome = outcome
        self.delay = timedelta(seconds=delay_seconds)
        self.error_code = error_code

    def tick(self, *, now: datetime) -> FakeDeliveryResult:
        with self.database.session() as session:
            repository = NotificationAttemptRepository(session)
            attempts = repository.list_fake_deliveries_ready(
                ready_before=now - self.delay,
            )
            advanced = 0
            for attempt in attempts:
                status = self._next_status(attempt.delivery_status)
                if status is None:
                    continue
                failed = status == NotificationDeliveryStatus.FAILED
                repository.update_delivery(
                    attempt,
                    status=status,
                    event_at=now,
                    received_at=now,
                    error_code=self.error_code if failed else None,
                    error_title=(
                        "Simulated WhatsApp delivery failure"
                        if failed
                        else None
                    ),
                    error_details=(
                        "Falha de entrega gerada pelo simulador local."
                        if failed
                        else None
                    ),
                    response={
                        "simulated": True,
                        "status": status.value,
                        "timestamp": now.isoformat(),
                        **(
                            {"error": {"code": self.error_code}}
                            if failed
                            else {}
                        ),
                    },
                )
                advanced += 1
        return FakeDeliveryResult(advanced=advanced)

    def _next_status(
        self,
        current: NotificationDeliveryStatus,
    ) -> NotificationDeliveryStatus | None:
        if current == NotificationDeliveryStatus.PENDING:
            return NotificationDeliveryStatus.SENT
        if current == NotificationDeliveryStatus.SENT:
            if self.outcome == "failed":
                return NotificationDeliveryStatus.FAILED
            return NotificationDeliveryStatus.DELIVERED
        if (
            current == NotificationDeliveryStatus.DELIVERED
            and self.outcome == "read"
        ):
            return NotificationDeliveryStatus.READ
        return None
