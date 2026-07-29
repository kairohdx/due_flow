from dataclasses import dataclass
from enum import Enum

from policyflow import FirstMatch, PolicyEngine, RuleResult, rule

from dueflow.domain.charges import ChargeStatus
from dueflow.domain.meta_errors import MetaErrorAction
from dueflow.domain.messaging import (
    NotificationDeliveryStatus,
    NotificationSubmissionStatus,
)
from dueflow.domain.phone import normalize_phone


class RecoveryAction(str, Enum):
    RETRY = "retry"
    TEMPLATE = "template"
    FIX = "fix"
    REVIEW = "review"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class RecoveryContext:
    submission_status: NotificationSubmissionStatus
    delivery_status: NotificationDeliveryStatus
    error_action: MetaErrorAction
    charge_status: ChargeStatus
    customer_active: bool
    customer_phone: str
    newer_attempt_exists: bool


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    eligible: bool
    action: RecoveryAction
    reason: str
    policy_name: str


def decision(
    policy_name: str,
    action: RecoveryAction,
    reason: str,
) -> RecoveryDecision:
    return RecoveryDecision(
        eligible=action is RecoveryAction.RETRY,
        action=action,
        reason=reason,
        policy_name=policy_name,
    )


@rule(id="BlockNewerAttemptPolicy")
def block_newer_attempt(context: RecoveryContext):
    if not context.newer_attempt_exists:
        return RuleResult.pass_(reason="no_newer_attempt")
    reason = "newer_attempt_exists"
    return RuleResult.consume(
        decision("BlockNewerAttemptPolicy", RecoveryAction.BLOCK, reason),
        reason=reason,
    )


@rule(id="BlockUnknownSubmissionPolicy")
def block_unknown_submission(context: RecoveryContext):
    if context.submission_status is not NotificationSubmissionStatus.UNKNOWN:
        return RuleResult.pass_(reason="submission_is_not_unknown")
    reason = "submission_outcome_is_unknown"
    return RuleResult.consume(
        decision("BlockUnknownSubmissionPolicy", RecoveryAction.BLOCK, reason),
        reason=reason,
    )


@rule(id="BlockActiveOrSuccessfulDeliveryPolicy")
def block_active_or_successful_delivery(context: RecoveryContext):
    blocked = {
        NotificationDeliveryStatus.PENDING,
        NotificationDeliveryStatus.SENT,
        NotificationDeliveryStatus.DELIVERED,
        NotificationDeliveryStatus.READ,
    }
    if context.delivery_status not in blocked:
        return RuleResult.pass_(reason="delivery_is_failed_or_not_started")
    reason = f"delivery_is_{context.delivery_status.value}"
    return RuleResult.consume(
        decision(
            "BlockActiveOrSuccessfulDeliveryPolicy",
            RecoveryAction.BLOCK,
            reason,
        ),
        reason=reason,
    )


@rule(id="BlockResolvedChargePolicy")
def block_resolved_charge(context: RecoveryContext):
    if context.charge_status is ChargeStatus.PENDING:
        return RuleResult.pass_(reason="charge_is_pending")
    reason = f"charge_is_{context.charge_status.value}"
    return RuleResult.consume(
        decision("BlockResolvedChargePolicy", RecoveryAction.BLOCK, reason),
        reason=reason,
    )


@rule(id="FixCustomerPolicy")
def fix_customer(context: RecoveryContext):
    if not context.customer_active:
        reason = "customer_is_inactive"
        return RuleResult.consume(
            decision("FixCustomerPolicy", RecoveryAction.FIX, reason),
            reason=reason,
        )
    try:
        normalize_phone(context.customer_phone)
    except ValueError:
        reason = "customer_phone_is_invalid"
        return RuleResult.consume(
            decision("FixCustomerPolicy", RecoveryAction.FIX, reason),
            reason=reason,
        )
    return RuleResult.pass_(reason="customer_is_ready")


@rule(id="RequireTemplatePolicy")
def require_template(context: RecoveryContext):
    if context.error_action is not MetaErrorAction.TEMPLATE:
        return RuleResult.pass_(reason="error_does_not_require_template")
    reason = "error_requires_template"
    return RuleResult.consume(
        decision("RequireTemplatePolicy", RecoveryAction.TEMPLATE, reason),
        reason=reason,
    )


@rule(id="RequireFixPolicy")
def require_fix(context: RecoveryContext):
    if context.error_action is not MetaErrorAction.FIX:
        return RuleResult.pass_(reason="error_does_not_require_fix")
    reason = "error_requires_fix"
    return RuleResult.consume(
        decision("RequireFixPolicy", RecoveryAction.FIX, reason),
        reason=reason,
    )


@rule(id="RequireReviewPolicy")
def require_review(context: RecoveryContext):
    if context.error_action is not MetaErrorAction.REVIEW:
        return RuleResult.pass_(reason="error_does_not_require_review")
    reason = "error_requires_review"
    return RuleResult.consume(
        decision("RequireReviewPolicy", RecoveryAction.REVIEW, reason),
        reason=reason,
    )


@rule(id="AllowRetryPolicy")
def allow_retry(context: RecoveryContext):
    confirmed_failure = (
        context.submission_status is NotificationSubmissionStatus.FAILED
        or context.delivery_status is NotificationDeliveryStatus.FAILED
    )
    if (
        confirmed_failure
        and context.error_action is MetaErrorAction.RETRY
    ):
        reason = "confirmed_retryable_failure"
        return RuleResult.consume(
            decision("AllowRetryPolicy", RecoveryAction.RETRY, reason),
            reason=reason,
        )
    reason = "failure_is_not_retryable"
    return RuleResult.consume(
        decision("AllowRetryPolicy", RecoveryAction.BLOCK, reason),
        reason=reason,
    )


RULES = (
    block_newer_attempt,
    block_unknown_submission,
    block_active_or_successful_delivery,
    block_resolved_charge,
    fix_customer,
    require_template,
    require_fix,
    require_review,
    allow_retry,
)


class NotificationRecoveryEvaluator:
    def __init__(self) -> None:
        self.engine = PolicyEngine[RecoveryContext, RecoveryDecision](
            name="dueflow.notification_recovery"
        )
        self.engine.add_scope(
            "notification.recovery",
            rules=list(RULES),
            strategy=FirstMatch(),
        )

    def evaluate(
        self,
        context: RecoveryContext,
    ) -> tuple[RecoveryDecision, dict]:
        execution = self.engine.run(
            context,
            scopes=["notification.recovery"],
            trace_attributes={
                "submission_status": context.submission_status.value,
                "delivery_status": context.delivery_status.value,
                "error_action": context.error_action.value,
            },
        )
        selected = execution.decision
        if selected is None or selected.effect is None:
            raise RuntimeError("o fluxo de recuperação terminou sem decisão")
        trace = {
            "trace_id": execution.trace.trace_id,
            "execution_id": execution.trace.execution_id,
            "pipeline": execution.trace.pipeline,
            "strategy": "first_match",
            "status": execution.trace.status,
            "duration_ms": execution.trace.duration_ms,
            "selected_policy": selected.rule_id,
            "evaluated": [
                {
                    "policy_name": str(event.attributes["rule_id"]),
                    "matched": bool(event.attributes["matched"]),
                    "outcome": str(event.attributes["outcome"]),
                    "reason": event.attributes.get("reason"),
                    "duration_ms": event.duration_ms,
                }
                for event in execution.trace.events
                if event.name == "rule.evaluated"
            ],
        }
        evaluated_names = {
            item["policy_name"] for item in trace["evaluated"]
        }
        trace["not_evaluated"] = [
            getattr(item, "rule_id", getattr(item, "id", item.__name__))
            for item in RULES
            if getattr(
                item,
                "rule_id",
                getattr(item, "id", item.__name__),
            )
            not in evaluated_names
        ]
        return selected.effect, trace
