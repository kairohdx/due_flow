from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from dueflow.domain.messaging import (
    NotificationDeliveryStatus,
    NotificationSubmissionStatus,
)
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)
from dueflow.infrastructure.messaging.meta import mask_phone, sanitize_provider_data


@dataclass(frozen=True, slots=True)
class WebhookProcessingResult:
    received: int = 0
    updated: int = 0
    ignored: int = 0
    unknown: int = 0


class MetaWebhookService:
    _rank = {
        NotificationDeliveryStatus.NOT_STARTED: -1,
        NotificationDeliveryStatus.PENDING: 0,
        NotificationDeliveryStatus.SENT: 1,
        NotificationDeliveryStatus.DELIVERED: 2,
        NotificationDeliveryStatus.READ: 3,
    }

    def __init__(self, repository: NotificationAttemptRepository) -> None:
        self.repository = repository

    def process(
        self,
        payload: Any,
        *,
        received_at: datetime | None = None,
    ) -> WebhookProcessingResult:
        now = received_at or datetime.now(UTC)
        received = updated = ignored = unknown = 0
        for raw_status in self._statuses(payload):
            received += 1
            parsed = self._parse_status(raw_status)
            if parsed is None:
                ignored += 1
                continue
            provider_message_id, status, event_at, error, safe_response = parsed
            attempt = self.repository.get_by_provider_message_id(
                provider_message_id,
                for_update=True,
            )
            if attempt is None:
                unknown += 1
                continue
            if (
                attempt.submission_status
                != NotificationSubmissionStatus.SUCCEEDED
            ):
                ignored += 1
                continue
            if not self._can_transition(
                attempt.delivery_status,
                attempt.delivery_event_at,
                status,
                event_at,
            ):
                ignored += 1
                continue
            self.repository.update_delivery(
                attempt,
                status=status,
                event_at=event_at,
                received_at=now,
                error_code=error["code"],
                error_title=error["title"],
                error_details=error["details"],
                response=safe_response,
            )
            updated += 1
        return WebhookProcessingResult(
            received=received,
            updated=updated,
            ignored=ignored,
            unknown=unknown,
        )

    @staticmethod
    def _statuses(payload: Any):
        if not isinstance(payload, dict):
            return
        entries = payload.get("entry")
        if not isinstance(entries, list):
            return
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            changes = entry.get("changes")
            if not isinstance(changes, list):
                continue
            for change in changes:
                if not isinstance(change, dict):
                    continue
                value = change.get("value")
                if not isinstance(value, dict):
                    continue
                statuses = value.get("statuses")
                if not isinstance(statuses, list):
                    continue
                for status in statuses:
                    if isinstance(status, dict):
                        yield status

    @staticmethod
    def _parse_status(raw: dict[str, Any]):
        provider_message_id = raw.get("id")
        raw_status = raw.get("status")
        raw_timestamp = raw.get("timestamp")
        if (
            not isinstance(provider_message_id, str)
            or not isinstance(raw_status, str)
            or raw_status not in {item.value for item in NotificationDeliveryStatus}
        ):
            return None
        try:
            event_at = datetime.fromtimestamp(int(raw_timestamp), tz=UTC)
        except (TypeError, ValueError, OSError):
            return None
        status = NotificationDeliveryStatus(raw_status)
        error = MetaWebhookService._error(raw)
        recipient = raw.get("recipient_id")
        safe_response: dict[str, Any] = {
            "status": status.value,
            "timestamp": event_at.isoformat(),
        }
        if isinstance(recipient, str):
            safe_response["recipient_id"] = mask_phone(recipient)
        if any(value is not None for value in error.values()):
            safe_response["error"] = {
                key: value for key, value in error.items() if value is not None
            }
        return (
            provider_message_id[:255],
            status,
            event_at,
            error,
            safe_response,
        )

    @staticmethod
    def _error(raw: dict[str, Any]) -> dict[str, Any]:
        errors = raw.get("errors")
        first = errors[0] if isinstance(errors, list) and errors else {}
        if not isinstance(first, dict):
            first = {}
        error_data = first.get("error_data")
        details = (
            error_data.get("details")
            if isinstance(error_data, dict)
            else None
        )
        code = first.get("code")
        return {
            "code": code if isinstance(code, int) else None,
            "title": MetaWebhookService._safe_text(first.get("title"), 255),
            "details": MetaWebhookService._safe_text(details, 2000),
        }

    @staticmethod
    def _safe_text(value: Any, limit: int) -> str | None:
        if not isinstance(value, str):
            return None
        sanitized = sanitize_provider_data(value)
        return str(sanitized)[:limit]

    @classmethod
    def _can_transition(
        cls,
        current: NotificationDeliveryStatus | None,
        current_at: datetime | None,
        incoming: NotificationDeliveryStatus,
        incoming_at: datetime,
    ) -> bool:
        if current == incoming:
            return False
        if current in {
            NotificationDeliveryStatus.READ,
            NotificationDeliveryStatus.FAILED,
        }:
            return False
        normalized_current_at = cls._utc(current_at)
        if normalized_current_at is not None and incoming_at < normalized_current_at:
            return False
        if incoming == NotificationDeliveryStatus.FAILED:
            return current in {
                None,
                NotificationDeliveryStatus.NOT_STARTED,
                NotificationDeliveryStatus.PENDING,
                NotificationDeliveryStatus.SENT,
            }
        current_rank = cls._rank.get(
            current or NotificationDeliveryStatus.NOT_STARTED,
            -1,
        )
        return cls._rank[incoming] > current_rank

    @staticmethod
    def _utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
