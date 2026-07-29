from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from dueflow.application.errors import InvalidStateError, ResourceNotFoundError
from dueflow.application.job_queue import EnqueueResult, JobQueue
from dueflow.application.whatsapp import WhatsAppProvider
from dueflow.application.message_delivery import TemplateConfiguration
from dueflow.domain.jobs import JobRecord, JobType
from dueflow.domain.meta_errors import describe_meta_error
from dueflow.domain.messaging import ProviderSubmissionError, TemplateMessage
from dueflow.domain.notification_recovery import (
    NotificationRecoveryEvaluator,
    RecoveryAction,
    RecoveryContext,
    RecoveryDecision,
)
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)
from dueflow.infrastructure.db.repositories import ChargeRepository, CustomerRepository


@dataclass(frozen=True, slots=True)
class RecoveryAssessment:
    attempt_id: UUID
    decision: RecoveryDecision
    trace: dict[str, Any]
    template_available: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": str(self.attempt_id),
            "eligible": self.decision.eligible,
            "action": self.decision.action.value,
            "reason": self.decision.reason,
            "policy_name": self.decision.policy_name,
            "trace": self.trace,
            "template_eligible": (
                self.decision.action is RecoveryAction.TEMPLATE
                and self.template_available
            ),
        }


class NotificationRetryService:
    def __init__(
        self,
        repository: NotificationAttemptRepository,
        charge_repository: ChargeRepository,
        customer_repository: CustomerRepository,
        *,
        queue: JobQueue | None = None,
        provider: WhatsAppProvider | None = None,
        max_attempts: int = 3,
        template_configuration: TemplateConfiguration | None = None,
    ) -> None:
        self.repository = repository
        self.charge_repository = charge_repository
        self.customer_repository = customer_repository
        self.queue = queue
        self.provider = provider
        self.max_attempts = max_attempts
        self.template_configuration = (
            template_configuration or TemplateConfiguration(name="")
        )
        self.evaluator = NotificationRecoveryEvaluator()

    def assess(self, attempt_id: UUID) -> RecoveryAssessment:
        attempt = self.repository.get(attempt_id)
        if attempt is None:
            raise ResourceNotFoundError("tentativa de notificação não encontrada")
        charge = self.charge_repository.get(attempt.charge_id)
        if charge is None:
            raise ResourceNotFoundError("cobrança da tentativa não encontrada")
        customer = self.customer_repository.get(charge.customer_id)
        if customer is None:
            raise ResourceNotFoundError("cliente da tentativa não encontrado")
        error_code = (
            attempt.delivery_error_code
            if attempt.delivery_status.value == "failed"
            else attempt.submission_error_code
        )
        error = describe_meta_error(error_code)
        decision, trace = self.evaluator.evaluate(
            RecoveryContext(
                submission_status=attempt.submission_status,
                delivery_status=attempt.delivery_status,
                error_action=error.action_type,
                charge_status=charge.status,
                customer_active=customer.active,
                customer_phone=customer.phone,
                newer_attempt_exists=self.repository.has_newer_attempt(attempt),
            )
        )
        return RecoveryAssessment(
            attempt.id,
            decision,
            trace,
            template_available=self.template_configuration.available,
        )

    def enqueue(
        self,
        attempt_id: UUID,
        *,
        requested_by_user_id: UUID,
        now: datetime | None = None,
    ) -> EnqueueResult:
        if self.queue is None:
            raise RuntimeError("fila não configurada para retentativa")
        assessment = self.assess(attempt_id)
        if not assessment.decision.eligible:
            raise InvalidStateError(
                "retentativa não permitida: "
                f"{assessment.decision.reason}"
            )
        attempt = self.repository.get(attempt_id)
        if attempt is None:
            raise ResourceNotFoundError("tentativa de notificação não encontrada")
        moment = now or datetime.now(UTC)
        return self.queue.enqueue(
            job_type=JobType.RETRY_NOTIFICATION,
            payload={
                "origin": "manual",
                "charge_id": str(attempt.charge_id),
                "source_attempt_id": str(attempt_id),
                "requested_by_user_id": str(requested_by_user_id),
                "requested_at": moment.isoformat(),
                "recovery": assessment.as_dict(),
                "send_mode": "text",
            },
            scheduled_for=moment,
            max_attempts=self.max_attempts,
            deduplication_key=f"notification_retry:{attempt_id}",
        )

    def enqueue_template(
        self,
        attempt_id: UUID,
        *,
        requested_by_user_id: UUID,
        now: datetime | None = None,
    ) -> EnqueueResult:
        if self.queue is None:
            raise RuntimeError("fila não configurada para retentativa")
        assessment = self.assess(attempt_id)
        if (
            assessment.decision.action is not RecoveryAction.TEMPLATE
            or not assessment.template_available
        ):
            raise InvalidStateError(
                "reenvio com template não permitido: "
                f"{assessment.decision.reason}"
            )
        attempt = self.repository.get(attempt_id)
        if attempt is None:
            raise ResourceNotFoundError("tentativa de notificação não encontrada")
        moment = now or datetime.now(UTC)
        return self.queue.enqueue(
            job_type=JobType.RETRY_NOTIFICATION,
            payload={
                "origin": "manual",
                "charge_id": str(attempt.charge_id),
                "source_attempt_id": str(attempt_id),
                "requested_by_user_id": str(requested_by_user_id),
                "requested_at": moment.isoformat(),
                "recovery": assessment.as_dict(),
                "send_mode": "template",
            },
            scheduled_for=moment,
            max_attempts=self.max_attempts,
            deduplication_key=f"notification_template_retry:{attempt_id}",
        )

    def process(self, job: JobRecord) -> dict[str, Any]:
        if self.provider is None:
            raise RuntimeError("provider não configurado para retentativa")
        source_id = UUID(str(job.payload["source_attempt_id"]))
        assessment = self.assess(source_id)
        send_mode = str(job.payload.get("send_mode", "text"))
        template_retry = send_mode == "template"
        allowed = (
            assessment.decision.action is RecoveryAction.TEMPLATE
            and assessment.template_available
            if template_retry
            else assessment.decision.eligible
        )
        if not allowed:
            return {
                "reference_date": datetime.now(UTC).date().isoformat(),
                "evaluated": 0,
                "eligible": 0,
                "skipped": 0,
                "simulated": 0,
                "deduplicated": 0,
                "notification_failed": 0,
                "evaluations": [],
                "retried": False,
                "cancelled": True,
                "source_attempt_id": str(source_id),
                "recovery": assessment.as_dict(),
            }
        source = self.repository.get(source_id)
        if source is None:
            raise ResourceNotFoundError("tentativa de origem não encontrada")
        charge = self.charge_repository.get(source.charge_id)
        if charge is None:
            raise ResourceNotFoundError("cobrança da tentativa não encontrada")
        customer = self.customer_repository.get(charge.customer_id)
        if customer is None:
            raise ResourceNotFoundError("cliente da tentativa não encontrado")
        root_id = source.root_attempt_id or source.id
        number = self.repository.next_attempt_number(root_id)
        requested_by = UUID(str(job.payload["requested_by_user_id"]))
        trace = {
            **assessment.trace,
            "source_attempt_id": str(source.id),
            "root_attempt_id": str(root_id),
            "attempt_number": number,
        }
        template = (
            self.template_configuration.render(
                customer=customer,
                charge=charge,
            )
            if template_retry
            else None
        )
        message = template.preview if template is not None else source.message
        trace["message_format"] = (
            "template" if template is not None else "text"
        )
        if template is not None:
            trace["template"] = {
                "name": template.name,
                "language": template.language,
                "parameters": list(template.parameters),
            }
        reservation = self.repository.reserve(
            charge_id=source.charge_id,
            processing_job_id=job.id,
            notification_type=source.notification_type,
            provider=self.provider.name,
            destination=customer.phone,
            message=message,
            idempotency_key=(
                f"{source.idempotency_key}:"
                f"{'template-retry' if template_retry else 'retry'}:{number}"
            ),
            policy_name=assessment.decision.policy_name,
            decision_reason=assessment.decision.reason,
            trace=trace,
            processed_at=datetime.now(UTC),
            root_attempt_id=root_id,
            retry_of_attempt_id=source.id,
            retry_requested_by_user_id=requested_by,
            attempt_number=number,
        )
        attempt = reservation.attempt
        if reservation.created:
            self._send(
                attempt,
                customer.phone,
                message,
                template=template,
            )
        return {
            "reference_date": datetime.now(UTC).date().isoformat(),
            "evaluated": 0,
            "eligible": 1,
            "skipped": 0,
            "simulated": int(
                attempt.submission_status.value == "simulated"
            ),
            "notification_failed": int(
                attempt.submission_status.value in {"failed", "unknown"}
            ),
            "evaluations": [],
            "retried": True,
            "cancelled": False,
            "deduplicated": int(not reservation.created),
            "source_attempt_id": str(source.id),
            "attempt_id": str(attempt.id),
            "attempt_number": attempt.attempt_number,
            "submission_status": attempt.submission_status.value,
            "send_mode": send_mode,
            "recovery": assessment.as_dict(),
        }

    def _send(
        self,
        attempt,
        destination: str,
        message: str,
        *,
        template: TemplateMessage | None = None,
    ) -> None:
        try:
            if template is not None:
                result = self.provider.send_template(
                    destination,
                    template,
                    correlation_id=str(attempt.id),
                )
            else:
                result = self.provider.send_text(
                    destination,
                    message,
                    correlation_id=str(attempt.id),
                )
        except Exception as exc:
            provider_error = (
                exc if isinstance(exc, ProviderSubmissionError) else None
            )
            self.repository.fail(
                attempt,
                error=f"{type(exc).__name__}: {exc}",
                error_code=provider_error.code if provider_error else None,
                error_title=provider_error.title if provider_error else None,
                outcome_unknown=(
                    provider_error.outcome_unknown
                    if provider_error
                    else False
                ),
                processed_at=datetime.now(UTC),
            )
            return
        self.repository.complete(
            attempt,
            submission_status=result.submission_status,
            provider_message_id=result.provider_message_id,
            provider_response={
                "request": result.request_payload,
                "response": result.response_payload,
            },
            processed_at=datetime.now(UTC),
        )
