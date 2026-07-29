from dataclasses import dataclass
from enum import Enum
from typing import Any


class NotificationProvider(str, Enum):
    FAKE = "fake"
    META = "meta"


class NotificationSubmissionStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"
    SIMULATED = "simulated"


class NotificationDeliveryStatus(str, Enum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class MessageFormat(str, Enum):
    TEXT = "text"
    TEMPLATE = "template"


@dataclass(frozen=True, slots=True)
class TemplateMessage:
    name: str
    language: str
    parameters: tuple[str, ...]
    preview: str


class ProviderSubmissionError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        title: str | None = None,
        outcome_unknown: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.title = title
        self.outcome_unknown = outcome_unknown


@dataclass(frozen=True, slots=True)
class ProviderResult:
    submission_status: NotificationSubmissionStatus
    provider_message_id: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
