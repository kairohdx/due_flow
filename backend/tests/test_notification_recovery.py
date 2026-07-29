import pytest

from dueflow.domain.charges import ChargeStatus
from dueflow.domain.meta_errors import MetaErrorAction
from dueflow.domain.messaging import (
    NotificationDeliveryStatus,
    NotificationSubmissionStatus,
)
from dueflow.domain.notification_recovery import (
    NotificationRecoveryEvaluator,
    RecoveryAction,
    RecoveryContext,
)


def context(
    *,
    submission=NotificationSubmissionStatus.FAILED,
    delivery=NotificationDeliveryStatus.NOT_STARTED,
    error_action=MetaErrorAction.RETRY,
) -> RecoveryContext:
    return RecoveryContext(
        submission_status=submission,
        delivery_status=delivery,
        error_action=error_action,
        charge_status=ChargeStatus.PENDING,
        customer_active=True,
        customer_phone="+5511999990000",
        newer_attempt_exists=False,
    )


@pytest.mark.parametrize(
    "delivery",
    [
        NotificationDeliveryStatus.PENDING,
        NotificationDeliveryStatus.SENT,
        NotificationDeliveryStatus.DELIVERED,
        NotificationDeliveryStatus.READ,
    ],
)
def test_recovery_blocks_messages_in_transit_or_successful(delivery) -> None:
    decision, _ = NotificationRecoveryEvaluator().evaluate(
        context(
            submission=NotificationSubmissionStatus.SUCCEEDED,
            delivery=delivery,
        )
    )
    assert decision.action is RecoveryAction.BLOCK


def test_recovery_blocks_unknown_submission_even_for_retryable_error() -> None:
    decision, trace = NotificationRecoveryEvaluator().evaluate(
        context(submission=NotificationSubmissionStatus.UNKNOWN)
    )
    assert decision.eligible is False
    assert decision.policy_name == "BlockUnknownSubmissionPolicy"
    assert trace["strategy"] == "first_match"


@pytest.mark.parametrize(
    ("error_action", "expected"),
    [
        (MetaErrorAction.RETRY, RecoveryAction.RETRY),
        (MetaErrorAction.TEMPLATE, RecoveryAction.TEMPLATE),
        (MetaErrorAction.FIX, RecoveryAction.FIX),
        (MetaErrorAction.REVIEW, RecoveryAction.REVIEW),
    ],
)
def test_recovery_classifies_confirmed_failure(error_action, expected) -> None:
    decision, _ = NotificationRecoveryEvaluator().evaluate(
        context(error_action=error_action)
    )
    assert decision.action is expected
    assert decision.eligible is (expected is RecoveryAction.RETRY)
