from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dueflow.domain.messaging import (
    NotificationSubmissionStatus,
    NotificationDeliveryStatus,
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
            submission_status=NotificationSubmissionStatus.PENDING,
            delivery_status=NotificationDeliveryStatus.NOT_STARTED,
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
        submission_status: NotificationSubmissionStatus,
        provider_message_id: str,
        provider_response: dict[str, Any],
        processed_at: datetime,
    ) -> NotificationAttempt:
        attempt.submission_status = submission_status
        attempt.provider_message_id = provider_message_id
        attempt.provider_response = dict(provider_response)
        if (
            submission_status == NotificationSubmissionStatus.SUCCEEDED
            and attempt.provider == NotificationProvider.META
        ):
            attempt.delivery_status = NotificationDeliveryStatus.PENDING
        attempt.submission_error_code = None
        attempt.submission_error_title = None
        attempt.submission_error_details = None
        attempt.processed_at = processed_at
        self.session.commit()
        self.session.refresh(attempt)
        return attempt

    def fail(
        self,
        attempt: NotificationAttempt,
        *,
        error: str,
        error_code: int | None = None,
        error_title: str | None = None,
        outcome_unknown: bool = False,
        processed_at: datetime,
    ) -> NotificationAttempt:
        attempt.submission_status = (
            NotificationSubmissionStatus.UNKNOWN
            if outcome_unknown
            else NotificationSubmissionStatus.FAILED
        )
        attempt.delivery_status = NotificationDeliveryStatus.NOT_STARTED
        attempt.submission_error_code = error_code
        attempt.submission_error_title = (
            error_title[:255] if error_title is not None else None
        )
        attempt.submission_error_details = error[:2000]
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

    def get_by_provider_message_id(
        self,
        provider_message_id: str,
        *,
        for_update: bool = False,
    ) -> NotificationAttempt | None:
        statement = select(NotificationAttempt).where(
            NotificationAttempt.provider_message_id == provider_message_id
        )
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def update_delivery(
        self,
        attempt: NotificationAttempt,
        *,
        status: NotificationDeliveryStatus,
        event_at: datetime,
        received_at: datetime,
        error_code: int | None,
        error_title: str | None,
        error_details: str | None,
        response: dict[str, Any],
    ) -> NotificationAttempt:
        attempt.delivery_status = status
        attempt.delivery_event_at = event_at
        attempt.delivery_updated_at = received_at
        attempt.delivery_error_code = error_code
        attempt.delivery_error_title = (
            error_title[:255] if error_title is not None else None
        )
        attempt.delivery_error_details = (
            error_details[:2000] if error_details is not None else None
        )
        attempt.delivery_response = dict(response)
        self.session.commit()
        self.session.refresh(attempt)
        return attempt

    def list(
        self,
        *,
        charge_id: UUID | None,
        status: NotificationSubmissionStatus | None,
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
        status: NotificationSubmissionStatus | None,
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
        status: NotificationSubmissionStatus | None,
        provider: NotificationProvider | None,
        notification_type: NotificationType | None,
        processed_from: datetime | None,
        processed_to: datetime | None,
    ):
        if status is not None:
            statement = statement.where(
                NotificationAttempt.submission_status == status
            )
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
