from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from dueflow.application.message_templates import MessageRenderer
from dueflow.application.whatsapp import WhatsAppProvider
from dueflow.domain.messaging import NotificationAttemptStatus
from dueflow.domain.notifications import DecisionKind, PolicyEvaluation
from dueflow.infrastructure.db.models import Charge, Customer
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)


@dataclass(frozen=True, slots=True)
class NotificationExecution:
    attempt_id: UUID
    status: NotificationAttemptStatus
    provider_message_id: str | None
    idempotency_key: str
    deduplicated: bool
    error: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": str(self.attempt_id),
            "status": self.status.value,
            "provider_message_id": self.provider_message_id,
            "idempotency_key": self.idempotency_key,
            "deduplicated": self.deduplicated,
            "error": self.error,
        }


class NotificationService:
    def __init__(
        self,
        repository: NotificationAttemptRepository,
        provider: WhatsAppProvider,
        renderer: MessageRenderer | None = None,
    ) -> None:
        self.repository = repository
        self.provider = provider
        self.renderer = renderer or MessageRenderer()

    def execute(
        self,
        *,
        charge: Charge,
        customer: Customer,
        evaluation: PolicyEvaluation,
        trace: dict[str, Any],
        processing_job_id: UUID | None = None,
    ) -> NotificationExecution | None:
        decision = evaluation.decision
        if (
            decision.decision is not DecisionKind.NOTIFY
            or decision.notification_type is None
        ):
            return None

        message = self.renderer.render(
            decision.notification_type,
            customer_name=customer.name,
            charge_description=charge.description,
            amount=charge.amount,
            due_date=charge.due_date,
        )
        idempotency_key = (
            f"{charge.id}:{charge.due_date.isoformat()}:"
            f"{decision.notification_type.value}"
        )
        now = datetime.now(UTC)
        reservation = self.repository.reserve(
            charge_id=charge.id,
            processing_job_id=processing_job_id,
            notification_type=decision.notification_type,
            provider=self.provider.name,
            destination=customer.phone,
            message=message,
            idempotency_key=idempotency_key,
            policy_name=decision.policy_name,
            decision_reason=decision.reason,
            trace=trace,
            processed_at=now,
        )
        attempt = reservation.attempt
        if not reservation.created:
            return NotificationExecution(
                attempt_id=attempt.id,
                status=attempt.status,
                provider_message_id=attempt.provider_message_id,
                idempotency_key=attempt.idempotency_key,
                deduplicated=True,
                error=attempt.error,
            )

        try:
            result = self.provider.send_text(
                customer.phone,
                message,
                correlation_id=str(attempt.id),
            )
        except Exception as exc:
            safe_error = f"{type(exc).__name__}: {exc}"
            attempt = self.repository.fail(
                attempt,
                error=safe_error,
                processed_at=datetime.now(UTC),
            )
            return NotificationExecution(
                attempt_id=attempt.id,
                status=attempt.status,
                provider_message_id=None,
                idempotency_key=attempt.idempotency_key,
                deduplicated=False,
                error=attempt.error,
            )

        attempt = self.repository.complete(
            attempt,
            status=result.status,
            provider_message_id=result.provider_message_id,
            provider_response={
                "request": result.request_payload,
                "response": result.response_payload,
            },
            processed_at=datetime.now(UTC),
        )
        return NotificationExecution(
            attempt_id=attempt.id,
            status=attempt.status,
            provider_message_id=attempt.provider_message_id,
            idempotency_key=attempt.idempotency_key,
            deduplicated=False,
            error=None,
        )
