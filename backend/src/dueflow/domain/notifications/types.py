from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from dueflow.domain.charges import ChargeStatus


class DecisionKind(str, Enum):
    SKIP = "skip"
    NOTIFY = "notify"


class NotificationType(str, Enum):
    UPCOMING = "upcoming"
    DUE_TODAY = "due_today"
    OVERDUE = "overdue"


class NotificationAction(str, Enum):
    NONE = "none"
    SEND = "send"


@dataclass(frozen=True, slots=True)
class ChargeNotificationContext:
    charge_id: str
    status: ChargeStatus
    due_date: date
    reference_date: date
    reminder_days_before: int
    customer_active: bool
    customer_phone: str

    def __post_init__(self) -> None:
        if not self.charge_id.strip():
            raise ValueError("charge_id não pode ser vazio")
        if self.reminder_days_before < 0:
            raise ValueError("reminder_days_before não pode ser negativo")

    @property
    def days_until_due(self) -> int:
        return (self.due_date - self.reference_date).days


@dataclass(frozen=True, slots=True)
class NotificationDecision:
    decision: DecisionKind
    notification_type: NotificationType | None
    template_key: str | None
    reason: str
    eligible: bool
    recommended_action: NotificationAction
    policy_name: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "metadata",
            MappingProxyType(dict(self.metadata)),
        )


@dataclass(frozen=True, slots=True)
class PolicyTraceEntry:
    policy_name: str
    matched: bool
    outcome: str
    reason: str | None
    duration_ms: float | None


@dataclass(frozen=True, slots=True)
class PolicyTrace:
    trace_id: str
    execution_id: str
    pipeline: str
    strategy: str
    status: str
    duration_ms: float
    evaluated: tuple[PolicyTraceEntry, ...]
    not_evaluated: tuple[str, ...]
    selected_policy: str


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    decision: NotificationDecision
    trace: PolicyTrace

