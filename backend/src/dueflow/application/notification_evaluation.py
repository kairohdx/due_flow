from dueflow.domain.notifications import (
    ChargeNotificationContext,
    NotificationPolicyEvaluator,
    PolicyEvaluation,
)


class EvaluateChargeNotification:
    def __init__(
        self,
        evaluator: NotificationPolicyEvaluator | None = None,
    ) -> None:
        self.evaluator = evaluator or NotificationPolicyEvaluator()

    def execute(
        self,
        context: ChargeNotificationContext,
    ) -> PolicyEvaluation:
        return self.evaluator.evaluate(context)

