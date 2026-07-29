from dataclasses import dataclass
from enum import Enum
from typing import Any


class NotificationProvider(str, Enum):
    FAKE = "fake"
    META = "meta"


class NotificationAttemptStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SIMULATED = "simulated"


@dataclass(frozen=True, slots=True)
class ProviderResult:
    status: NotificationAttemptStatus
    provider_message_id: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]

