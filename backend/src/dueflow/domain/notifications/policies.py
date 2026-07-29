from policyflow import RuleResult, rule

from dueflow.domain.charges import ChargeStatus
from dueflow.domain.notifications.types import (
    ChargeNotificationContext,
    DecisionKind,
    NotificationAction,
    NotificationDecision,
    NotificationType,
)
from dueflow.domain.phone import normalize_phone

SKIP_INACTIVE_CUSTOMER = "SkipInactiveCustomerPolicy"
SKIP_PAID = "SkipPaidPolicy"
SKIP_CANCELED = "SkipCanceledPolicy"
SKIP_INVALID_PHONE = "SkipInvalidPhonePolicy"
OVERDUE = "OverduePolicy"
DUE_TODAY = "DueTodayPolicy"
UPCOMING_REMINDER = "UpcomingReminderPolicy"
NO_NOTIFICATION = "NoNotificationPolicy"

POLICY_ORDER = (
    SKIP_INACTIVE_CUSTOMER,
    SKIP_PAID,
    SKIP_CANCELED,
    SKIP_INVALID_PHONE,
    OVERDUE,
    DUE_TODAY,
    UPCOMING_REMINDER,
    NO_NOTIFICATION,
)


def skip_decision(policy_name: str, reason: str) -> NotificationDecision:
    return NotificationDecision(
        decision=DecisionKind.SKIP,
        notification_type=None,
        template_key=None,
        reason=reason,
        eligible=False,
        recommended_action=NotificationAction.NONE,
        policy_name=policy_name,
    )


def notify_decision(
    *,
    policy_name: str,
    notification_type: NotificationType,
    template_key: str,
    reason: str,
    days_until_due: int,
) -> NotificationDecision:
    return NotificationDecision(
        decision=DecisionKind.NOTIFY,
        notification_type=notification_type,
        template_key=template_key,
        reason=reason,
        eligible=True,
        recommended_action=NotificationAction.SEND,
        policy_name=policy_name,
        metadata={"days_until_due": days_until_due},
    )


@rule(id=SKIP_INACTIVE_CUSTOMER)
def skip_inactive_customer(context: ChargeNotificationContext):
    if context.customer_active:
        return RuleResult.pass_(reason="customer_is_active")
    reason = "customer_is_inactive"
    return RuleResult.consume(
        skip_decision(SKIP_INACTIVE_CUSTOMER, reason),
        reason=reason,
    )


@rule(id=SKIP_PAID)
def skip_paid(context: ChargeNotificationContext):
    if context.status is not ChargeStatus.PAID:
        return RuleResult.pass_(reason="charge_is_not_paid")
    reason = "charge_is_paid"
    return RuleResult.consume(skip_decision(SKIP_PAID, reason), reason=reason)


@rule(id=SKIP_CANCELED)
def skip_canceled(context: ChargeNotificationContext):
    if context.status is not ChargeStatus.CANCELED:
        return RuleResult.pass_(reason="charge_is_not_canceled")
    reason = "charge_is_canceled"
    return RuleResult.consume(skip_decision(SKIP_CANCELED, reason), reason=reason)


@rule(id=SKIP_INVALID_PHONE)
def skip_invalid_phone(context: ChargeNotificationContext):
    try:
        normalize_phone(context.customer_phone)
    except ValueError:
        reason = "customer_phone_is_invalid"
        return RuleResult.consume(
            skip_decision(SKIP_INVALID_PHONE, reason),
            reason=reason,
        )
    return RuleResult.pass_(reason="customer_phone_is_valid")


@rule(id=OVERDUE)
def overdue(context: ChargeNotificationContext):
    if context.days_until_due >= 0:
        return RuleResult.pass_(reason="charge_is_not_overdue")
    reason = "charge_is_overdue"
    return RuleResult.consume(
        notify_decision(
            policy_name=OVERDUE,
            notification_type=NotificationType.OVERDUE,
            template_key="charge_overdue",
            reason=reason,
            days_until_due=context.days_until_due,
        ),
        reason=reason,
    )


@rule(id=DUE_TODAY)
def due_today(context: ChargeNotificationContext):
    if context.days_until_due != 0:
        return RuleResult.pass_(reason="charge_is_not_due_today")
    reason = "charge_is_due_today"
    return RuleResult.consume(
        notify_decision(
            policy_name=DUE_TODAY,
            notification_type=NotificationType.DUE_TODAY,
            template_key="charge_due_today",
            reason=reason,
            days_until_due=0,
        ),
        reason=reason,
    )


@rule(id=UPCOMING_REMINDER)
def upcoming_reminder(context: ChargeNotificationContext):
    if not 0 < context.days_until_due <= context.reminder_days_before:
        return RuleResult.pass_(reason="charge_is_outside_reminder_window")
    reason = "charge_is_within_reminder_window"
    return RuleResult.consume(
        notify_decision(
            policy_name=UPCOMING_REMINDER,
            notification_type=NotificationType.UPCOMING,
            template_key="charge_upcoming",
            reason=reason,
            days_until_due=context.days_until_due,
        ),
        reason=reason,
    )


@rule(id=NO_NOTIFICATION)
def no_notification(_: ChargeNotificationContext):
    reason = "no_notification_rule_matched"
    return RuleResult.consume(
        skip_decision(NO_NOTIFICATION, reason),
        reason=reason,
    )


RULES = (
    skip_inactive_customer,
    skip_paid,
    skip_canceled,
    skip_invalid_phone,
    overdue,
    due_today,
    upcoming_reminder,
    no_notification,
)

