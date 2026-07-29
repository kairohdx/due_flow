from policyflow import FirstMatch, PolicyEngine

from dueflow.domain.notifications.policies import POLICY_ORDER, RULES
from dueflow.domain.notifications.types import (
    ChargeNotificationContext,
    NotificationDecision,
    PolicyEvaluation,
    PolicyTrace,
    PolicyTraceEntry,
)

PIPELINE_NAME = "dueflow.charge_notification"
SCOPE_NAME = "charge.notification"
STRATEGY_NAME = "first_match"


class NotificationPolicyEvaluator:
    def __init__(self) -> None:
        self._engine = PolicyEngine[
            ChargeNotificationContext,
            NotificationDecision,
        ](name=PIPELINE_NAME)
        self._engine.add_scope(
            SCOPE_NAME,
            rules=list(RULES),
            strategy=FirstMatch(),
        )

    def evaluate(
        self,
        context: ChargeNotificationContext,
    ) -> PolicyEvaluation:
        execution = self._engine.run(
            context,
            scopes=[SCOPE_NAME],
            trace_attributes={
                "charge_id": context.charge_id,
                "charge_status": context.status.value,
                "due_date": context.due_date.isoformat(),
                "reference_date": context.reference_date.isoformat(),
            },
        )
        selected = execution.decision
        if selected is None or selected.effect is None:
            raise RuntimeError("o fluxo de notificação terminou sem decisão")

        evaluated = tuple(
            PolicyTraceEntry(
                policy_name=str(event.attributes["rule_id"]),
                matched=bool(event.attributes["matched"]),
                outcome=str(event.attributes["outcome"]),
                reason=(
                    str(event.attributes["reason"])
                    if event.attributes.get("reason") is not None
                    else None
                ),
                duration_ms=event.duration_ms,
            )
            for event in execution.trace.events
            if event.name == "rule.evaluated"
        )
        evaluated_names = {entry.policy_name for entry in evaluated}
        trace = PolicyTrace(
            trace_id=execution.trace.trace_id,
            execution_id=execution.trace.execution_id,
            pipeline=execution.trace.pipeline,
            strategy=STRATEGY_NAME,
            status=execution.trace.status,
            duration_ms=execution.trace.duration_ms,
            evaluated=evaluated,
            not_evaluated=tuple(
                policy_name
                for policy_name in POLICY_ORDER
                if policy_name not in evaluated_names
            ),
            selected_policy=selected.rule_id,
        )
        return PolicyEvaluation(decision=selected.effect, trace=trace)

