from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dueflow.domain.messaging import (
    NotificationAttemptStatus,
    NotificationProvider,
)
from dueflow.domain.notifications import NotificationType
from dueflow.infrastructure.db.models import NotificationAttempt


@dataclass(frozen=True, slots=True)
class AttemptReservation:
    attempt: NotificationAttempt
    created: bool


class NotificationAttemptRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def reserve(
        self,
        *,
        charge_id: UUID,
        processing_job_id: UUID | None,
        notification_type: NotificationType,
        provider: NotificationProvider,
        destination: str,
        message: str,
        idempotency_key: str,
        policy_name: str,
        decision_reason: str,
        trace: dict[str, Any],
        processed_at: datetime,
    ) -> AttemptReservation:
        existing = self.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return AttemptReservation(existing, created=False)

        attempt = NotificationAttempt(
            charge_id=charge_id,
            processing_job_id=processing_job_id,
            notification_type=notification_type,
            provider=provider,
            destination=destination,
            message=message,
            status=NotificationAttemptStatus.PENDING,
            idempotency_key=idempotency_key,
            policy_name=policy_name,
            decision_reason=decision_reason,
            trace=dict(trace),
            processed_at=processed_at,
        )
        self.session.add(attempt)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self.get_by_idempotency_key(idempotency_key)
            if existing is None:
                raise
            return AttemptReservation(existing, created=False)
        self.session.refresh(attempt)
        return AttemptReservation(attempt, created=True)

    def complete(
        self,
        attempt: NotificationAttempt,
        *,
        status: NotificationAttemptStatus,
        provider_message_id: str,
        provider_response: dict[str, Any],
        processed_at: datetime,
    ) -> NotificationAttempt:
        attempt.status = status
        attempt.provider_message_id = provider_message_id
        attempt.provider_response = dict(provider_response)
        attempt.error = None
        attempt.processed_at = processed_at
        self.session.commit()
        self.session.refresh(attempt)
        return attempt

    def fail(
        self,
        attempt: NotificationAttempt,
        *,
        error: str,
        processed_at: datetime,
    ) -> NotificationAttempt:
        attempt.status = NotificationAttemptStatus.FAILED
        attempt.error = error[:2000]
        attempt.processed_at = processed_at
        self.session.commit()
        self.session.refresh(attempt)
        return attempt

    def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> NotificationAttempt | None:
        return self.session.scalar(
            select(NotificationAttempt).where(
                NotificationAttempt.idempotency_key == idempotency_key
            )
        )

    def get(self, attempt_id: UUID) -> NotificationAttempt | None:
        return self.session.get(NotificationAttempt, attempt_id)

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
        statement = select(NotificationAttempt)
        if charge_id is not None:
            statement = statement.where(
                NotificationAttempt.charge_id == charge_id
            )
        statement = self._apply_filters(
            statement,
            status=status,
            provider=provider,
            notification_type=notification_type,
            processed_from=processed_from,
            processed_to=processed_to,
        )
        statement = (
            statement.order_by(
                NotificationAttempt.processed_at.desc(),
                NotificationAttempt.id,
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

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
        statement = select(func.count()).select_from(NotificationAttempt)
        if charge_id is not None:
            statement = statement.where(
                NotificationAttempt.charge_id == charge_id
            )
        statement = self._apply_filters(
            statement,
            status=status,
            provider=provider,
            notification_type=notification_type,
            processed_from=processed_from,
            processed_to=processed_to,
        )
        return int(self.session.scalar(statement) or 0)

    @staticmethod
    def _apply_filters(
        statement,
        *,
        status: NotificationAttemptStatus | None,
        provider: NotificationProvider | None,
        notification_type: NotificationType | None,
        processed_from: datetime | None,
        processed_to: datetime | None,
    ):
        if status is not None:
            statement = statement.where(NotificationAttempt.status == status)
        if provider is not None:
            statement = statement.where(NotificationAttempt.provider == provider)
        if notification_type is not None:
            statement = statement.where(
                NotificationAttempt.notification_type == notification_type
            )
        if processed_from is not None:
            statement = statement.where(
                NotificationAttempt.processed_at >= processed_from
            )
        if processed_to is not None:
            statement = statement.where(
                NotificationAttempt.processed_at <= processed_to
            )
        return statement
