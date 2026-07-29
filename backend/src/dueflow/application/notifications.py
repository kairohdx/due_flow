from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from dueflow.application.message_templates import MessageRenderer
from dueflow.application.message_delivery import TemplateConfiguration
from dueflow.application.whatsapp import WhatsAppProvider
from dueflow.domain.messaging import (
    NotificationSubmissionStatus,
    ProviderSubmissionError,
)
from dueflow.domain.notifications import DecisionKind, PolicyEvaluation
from dueflow.infrastructure.db.models import Charge, Customer
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)


@dataclass(frozen=True, slots=True)
class NotificationExecution:
    attempt_id: UUID
    submission_status: NotificationSubmissionStatus
    provider_message_id: str | None
    idempotency_key: str
    deduplicated: bool
    error: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": str(self.attempt_id),
            "submission_status": self.submission_status.value,
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
        template_configuration: TemplateConfiguration | None = None,
    ) -> None:
        self.repository = repository
        self.provider = provider
        self.renderer = renderer or MessageRenderer()
        self.template_configuration = (
            template_configuration or TemplateConfiguration(name="")
        )

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

        text_message = self.renderer.render(
            decision.notification_type,
            customer_name=customer.name,
            charge_description=charge.description,
            amount=charge.amount,
            due_date=charge.due_date,
        )
        template = None
        if self.template_configuration.use_by_default:
            template = self.template_configuration.render(
                customer=customer,
                charge=charge,
            )
        message = template.preview if template is not None else text_message
        attempt_trace = {
            **trace,
            "message_format": "template" if template is not None else "text",
        }
        if template is not None:
            attempt_trace["template"] = {
                "name": template.name,
                "language": template.language,
                "parameters": list(template.parameters),
            }
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
            trace=attempt_trace,
            processed_at=now,
        )
        attempt = reservation.attempt
        if not reservation.created:
            return NotificationExecution(
                attempt_id=attempt.id,
                submission_status=attempt.submission_status,
                provider_message_id=attempt.provider_message_id,
                idempotency_key=attempt.idempotency_key,
                deduplicated=True,
                error=attempt.submission_error_details,
            )

        try:
            if template is not None:
                result = self.provider.send_template(
                    customer.phone,
                    template,
                    correlation_id=str(attempt.id),
                )
            else:
                result = self.provider.send_text(
                    customer.phone,
                    message,
                    correlation_id=str(attempt.id),
                )
        except Exception as exc:
            safe_error = f"{type(exc).__name__}: {exc}"
            provider_error = (
                exc if isinstance(exc, ProviderSubmissionError) else None
            )
            attempt = self.repository.fail(
                attempt,
                error=safe_error,
                error_code=provider_error.code if provider_error else None,
                error_title=provider_error.title if provider_error else None,
                outcome_unknown=(
                    provider_error.outcome_unknown
                    if provider_error
                    else False
                ),
                processed_at=datetime.now(UTC),
            )
            return NotificationExecution(
                attempt_id=attempt.id,
                submission_status=attempt.submission_status,
                provider_message_id=None,
                idempotency_key=attempt.idempotency_key,
                deduplicated=False,
                error=attempt.submission_error_details,
            )

        attempt = self.repository.complete(
            attempt,
            submission_status=result.submission_status,
            provider_message_id=result.provider_message_id,
            provider_response={
                "request": result.request_payload,
                "response": result.response_payload,
            },
            processed_at=datetime.now(UTC),
        )
        return NotificationExecution(
            attempt_id=attempt.id,
            submission_status=attempt.submission_status,
            provider_message_id=attempt.provider_message_id,
            idempotency_key=attempt.idempotency_key,
            deduplicated=False,
            error=None,
        )
