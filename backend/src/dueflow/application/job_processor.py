from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from dueflow.application.errors import ResourceNotFoundError
from dueflow.application.notification_evaluation import EvaluateChargeNotification
from dueflow.application.notifications import NotificationService
from dueflow.application.whatsapp import WhatsAppProvider
from dueflow.domain.jobs import JobRecord, JobType
from dueflow.domain.notifications import (
    ChargeNotificationContext,
    DecisionKind,
    PolicyEvaluation,
)
from dueflow.infrastructure.db.models import Charge, Customer
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)
from dueflow.infrastructure.db.repositories import ChargeRepository, CustomerRepository


class ProcessingJobHandler:
    def __init__(
        self,
        charge_repository: ChargeRepository,
        customer_repository: CustomerRepository,
        notification_repository: NotificationAttemptRepository,
        provider: WhatsAppProvider,
        *,
        timezone: str,
        today_provider: Callable[[ZoneInfo], date] | None = None,
    ) -> None:
        self.charge_repository = charge_repository
        self.customer_repository = customer_repository
        self.notification_service = NotificationService(
            notification_repository,
            provider,
        )
        self.timezone = ZoneInfo(timezone)
        self.today_provider = today_provider or self._system_today
        self.evaluator = EvaluateChargeNotification()

    def process(self, job: JobRecord) -> dict[str, Any]:
        reference_date = self._reference_date(job.payload)
        if job.type is JobType.PROCESS_CHARGE:
            charge_id = UUID(str(job.payload["charge_id"]))
            charge = self.charge_repository.get(charge_id)
            if charge is None:
                raise ResourceNotFoundError("cobrança não encontrada")
            evaluations = [self._evaluate(charge, reference_date)]
        elif job.type is JobType.PROCESS_DUE_CHARGES:
            evaluations = [
                self._evaluate(charge, reference_date)
                for charge in self.charge_repository.list_pending()
            ]
        else:
            raise ValueError(f"tipo de job não suportado: {job.type}")

        eligible = sum(
            item["decision"]["decision"] == DecisionKind.NOTIFY.value
            for item in evaluations
        )
        simulated = sum(
            item["notification"] is not None
            and item["notification"]["status"] == "simulated"
            and not item["notification"]["deduplicated"]
            for item in evaluations
        )
        deduplicated = sum(
            item["notification"] is not None
            and item["notification"]["deduplicated"]
            for item in evaluations
        )
        notification_failed = sum(
            item["notification"] is not None
            and item["notification"]["status"] == "failed"
            for item in evaluations
        )
        return {
            "reference_date": reference_date.isoformat(),
            "evaluated": len(evaluations),
            "eligible": eligible,
            "skipped": len(evaluations) - eligible,
            "simulated": simulated,
            "deduplicated": deduplicated,
            "notification_failed": notification_failed,
            "evaluations": evaluations,
        }

    def _evaluate(self, charge: Charge, reference_date: date) -> dict[str, Any]:
        customer = self.customer_repository.get(charge.customer_id)
        if customer is None:
            raise ResourceNotFoundError("cliente da cobrança não encontrado")
        context = self._context(charge, customer, reference_date)
        evaluation = self.evaluator.execute(context)
        serialized = self._serialize_evaluation(charge, evaluation)
        notification = self.notification_service.execute(
            charge=charge,
            customer=customer,
            evaluation=evaluation,
            trace=serialized["trace"],
        )
        serialized["notification"] = (
            notification.as_dict() if notification is not None else None
        )
        return serialized

    @staticmethod
    def _context(
        charge: Charge,
        customer: Customer,
        reference_date: date,
    ) -> ChargeNotificationContext:
        return ChargeNotificationContext(
            charge_id=str(charge.id),
            status=charge.status,
            due_date=charge.due_date,
            reference_date=reference_date,
            reminder_days_before=charge.reminder_days_before,
            customer_active=customer.active,
            customer_phone=customer.phone,
        )

    @staticmethod
    def _serialize_evaluation(
        charge: Charge,
        evaluation: PolicyEvaluation,
    ) -> dict[str, Any]:
        decision = evaluation.decision
        trace = evaluation.trace
        return {
            "charge_id": str(charge.id),
            "decision": {
                "decision": decision.decision.value,
                "notification_type": (
                    decision.notification_type.value
                    if decision.notification_type is not None
                    else None
                ),
                "template_key": decision.template_key,
                "reason": decision.reason,
                "eligible": decision.eligible,
                "recommended_action": decision.recommended_action.value,
                "policy_name": decision.policy_name,
                "metadata": dict(decision.metadata),
            },
            "trace": {
                "trace_id": trace.trace_id,
                "execution_id": trace.execution_id,
                "pipeline": trace.pipeline,
                "strategy": trace.strategy,
                "status": trace.status,
                "duration_ms": trace.duration_ms,
                "selected_policy": trace.selected_policy,
                "evaluated": [
                    {
                        "policy_name": entry.policy_name,
                        "matched": entry.matched,
                        "outcome": entry.outcome,
                        "reason": entry.reason,
                        "duration_ms": entry.duration_ms,
                    }
                    for entry in trace.evaluated
                ],
                "not_evaluated": list(trace.not_evaluated),
            },
        }

    def _reference_date(self, payload: dict[str, Any]) -> date:
        value = payload.get("reference_date")
        if value is None:
            return self.today_provider(self.timezone)
        return date.fromisoformat(str(value))

    @staticmethod
    def _system_today(timezone: ZoneInfo) -> date:
        from datetime import datetime

        return datetime.now(timezone).date()
