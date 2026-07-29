from datetime import date, timedelta

import pytest

from dueflow.application.notification_evaluation import EvaluateChargeNotification
from dueflow.domain.charges import ChargeStatus
from dueflow.domain.notifications import (
    ChargeNotificationContext,
    DecisionKind,
    NotificationAction,
    NotificationType,
)
from dueflow.domain.notifications.policies import (
    DUE_TODAY,
    NO_NOTIFICATION,
    OVERDUE,
    SKIP_CANCELED,
    SKIP_INACTIVE_CUSTOMER,
    SKIP_INVALID_PHONE,
    SKIP_PAID,
    UPCOMING_REMINDER,
)

REFERENCE_DATE = date(2026, 7, 29)


def context(**overrides) -> ChargeNotificationContext:
    values = {
        "charge_id": "charge-001",
        "status": ChargeStatus.PENDING,
        "due_date": REFERENCE_DATE,
        "reference_date": REFERENCE_DATE,
        "reminder_days_before": 3,
        "customer_active": True,
        "customer_phone": "+5511999990000",
    }
    values.update(overrides)
    return ChargeNotificationContext(**values)


def evaluate(**overrides):
    return EvaluateChargeNotification().execute(context(**overrides))


@pytest.mark.parametrize(
    ("overrides", "policy_name", "reason"),
    [
        (
            {"customer_active": False},
            SKIP_INACTIVE_CUSTOMER,
            "customer_is_inactive",
        ),
        (
            {
                "status": ChargeStatus.PAID,
                "due_date": REFERENCE_DATE - timedelta(days=5),
            },
            SKIP_PAID,
            "charge_is_paid",
        ),
        (
            {"status": ChargeStatus.CANCELED},
            SKIP_CANCELED,
            "charge_is_canceled",
        ),
        (
            {"customer_phone": "11999990000"},
            SKIP_INVALID_PHONE,
            "customer_phone_is_invalid",
        ),
    ],
)
def test_skip_policies(
    overrides: dict,
    policy_name: str,
    reason: str,
) -> None:
    evaluation = evaluate(**overrides)

    assert evaluation.decision.decision is DecisionKind.SKIP
    assert evaluation.decision.eligible is False
    assert evaluation.decision.recommended_action is NotificationAction.NONE
    assert evaluation.decision.notification_type is None
    assert evaluation.decision.template_key is None
    assert evaluation.decision.policy_name == policy_name
    assert evaluation.decision.reason == reason
    assert evaluation.trace.selected_policy == policy_name


def test_overdue_charge_selects_overdue_policy() -> None:
    evaluation = evaluate(due_date=REFERENCE_DATE - timedelta(days=2))

    assert evaluation.decision.decision is DecisionKind.NOTIFY
    assert evaluation.decision.notification_type is NotificationType.OVERDUE
    assert evaluation.decision.template_key == "charge_overdue"
    assert evaluation.decision.recommended_action is NotificationAction.SEND
    assert evaluation.decision.metadata == {"days_until_due": -2}
    assert evaluation.trace.selected_policy == OVERDUE


def test_charge_due_today_selects_due_today_policy() -> None:
    evaluation = evaluate()

    assert evaluation.decision.notification_type is NotificationType.DUE_TODAY
    assert evaluation.decision.template_key == "charge_due_today"
    assert evaluation.trace.selected_policy == DUE_TODAY


@pytest.mark.parametrize("days_until_due", [1, 3])
def test_charge_inside_reminder_window_selects_upcoming_policy(
    days_until_due: int,
) -> None:
    evaluation = evaluate(
        due_date=REFERENCE_DATE + timedelta(days=days_until_due)
    )

    assert evaluation.decision.notification_type is NotificationType.UPCOMING
    assert evaluation.decision.template_key == "charge_upcoming"
    assert evaluation.decision.metadata == {
        "days_until_due": days_until_due
    }
    assert evaluation.trace.selected_policy == UPCOMING_REMINDER


def test_charge_outside_reminder_window_does_not_notify() -> None:
    evaluation = evaluate(due_date=REFERENCE_DATE + timedelta(days=4))

    assert evaluation.decision.decision is DecisionKind.SKIP
    assert evaluation.decision.eligible is False
    assert evaluation.decision.reason == "no_notification_rule_matched"
    assert evaluation.trace.selected_policy == NO_NOTIFICATION


def test_zero_day_reminder_only_allows_due_today() -> None:
    evaluation = evaluate(
        due_date=REFERENCE_DATE + timedelta(days=1),
        reminder_days_before=0,
    )

    assert evaluation.trace.selected_policy == NO_NOTIFICATION


def test_trace_explains_first_match_without_exposing_phone() -> None:
    evaluation = evaluate(
        status=ChargeStatus.PAID,
        due_date=REFERENCE_DATE - timedelta(days=10),
    )

    assert evaluation.trace.pipeline == "dueflow.charge_notification"
    assert evaluation.trace.strategy == "first_match"
    assert evaluation.trace.status == "completed"
    assert [entry.policy_name for entry in evaluation.trace.evaluated] == [
        SKIP_INACTIVE_CUSTOMER,
        SKIP_PAID,
    ]
    assert evaluation.trace.not_evaluated == (
        SKIP_CANCELED,
        SKIP_INVALID_PHONE,
        OVERDUE,
        DUE_TODAY,
        UPCOMING_REMINDER,
        NO_NOTIFICATION,
    )
    assert all(
        "+5511999990000" not in str(entry)
        for entry in evaluation.trace.evaluated
    )


def test_context_rejects_negative_reminder_window() -> None:
    with pytest.raises(
        ValueError,
        match="reminder_days_before não pode ser negativo",
    ):
        context(reminder_days_before=-1)

