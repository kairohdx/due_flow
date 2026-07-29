from uuid import UUID

from dueflow.application.errors import ResourceNotFoundError
from dueflow.infrastructure.db.models import NotificationAttempt
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)
from dueflow.infrastructure.db.repositories import ChargeRepository


class NotificationHistoryService:
    def __init__(
        self,
        repository: NotificationAttemptRepository,
        charge_repository: ChargeRepository,
    ) -> None:
        self.repository = repository
        self.charge_repository = charge_repository

    def list(
        self,
        *,
        charge_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[NotificationAttempt]:
        if (
            charge_id is not None
            and self.charge_repository.get(charge_id) is None
        ):
            raise ResourceNotFoundError("cobrança não encontrada")
        return self.repository.list(
            charge_id=charge_id,
            limit=limit,
            offset=offset,
        )

