from datetime import datetime
from uuid import UUID

from dueflow.application.errors import ResourceNotFoundError
from dueflow.infrastructure.db.models import NotificationAttempt
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)
from dueflow.infrastructure.db.repositories import ChargeRepository
from dueflow.domain.messaging import (
    NotificationAttemptStatus,
    NotificationProvider,
)
from dueflow.domain.notifications import NotificationType


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
        status: NotificationAttemptStatus | None,
        provider: NotificationProvider | None,
        notification_type: NotificationType | None,
        processed_from: datetime | None,
        processed_to: datetime | None,
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
            status=status,
            provider=provider,
            notification_type=notification_type,
            processed_from=processed_from,
            processed_to=processed_to,
            limit=limit,
            offset=offset,
        )

    def count(
        self,
        *,
        charge_id: UUID | None,
        status: NotificationAttemptStatus | None,
        provider: NotificationProvider | None,
        notification_type: NotificationType | None,
        processed_from: datetime | None,
        processed_to: datetime | None,
    ) -> int:
        return self.repository.count(
            charge_id=charge_id,
            status=status,
            provider=provider,
            notification_type=notification_type,
            processed_from=processed_from,
            processed_to=processed_to,
        )

    def get(self, attempt_id: UUID) -> NotificationAttempt:
        attempt = self.repository.get(attempt_id)
        if attempt is None:
            raise ResourceNotFoundError("notificação não encontrada")
        return attempt
