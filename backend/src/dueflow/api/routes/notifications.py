from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from dueflow.api.schemas.notifications import NotificationAttemptResponse
from dueflow.api.schemas.common import Page
from dueflow.api.query_validation import validate_range
from dueflow.application.notification_history import NotificationHistoryService
from dueflow.infrastructure.db.dependencies import get_session
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)
from dueflow.infrastructure.db.repositories import ChargeRepository
from dueflow.domain.messaging import (
    NotificationSubmissionStatus,
    NotificationProvider,
)
from dueflow.domain.notifications import NotificationType

router = APIRouter(tags=["notifications"])
SessionDependency = Annotated[Session, Depends(get_session)]


def service(session: Session) -> NotificationHistoryService:
    return NotificationHistoryService(
        NotificationAttemptRepository(session),
        ChargeRepository(session),
    )


def response(attempt) -> NotificationAttemptResponse:
    return NotificationAttemptResponse.model_validate(attempt)


@router.get(
    "/notifications",
    response_model=Page[NotificationAttemptResponse],
)
def list_notifications(
    session: SessionDependency,
    attempt_status: Annotated[
        NotificationSubmissionStatus | None,
        Query(alias="status"),
    ] = None,
    provider: NotificationProvider | None = None,
    notification_type: NotificationType | None = None,
    processed_from: datetime | None = None,
    processed_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=25)] = 25,
) -> Page[NotificationAttemptResponse]:
    validate_range(processed_from, processed_to)
    target = service(session)
    filters = {
        "charge_id": None,
        "status": attempt_status,
        "provider": provider,
        "notification_type": notification_type,
        "processed_from": processed_from,
        "processed_to": processed_to,
    }
    attempts = target.list(
        **filters,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return Page[NotificationAttemptResponse].create(
        items=[response(attempt) for attempt in attempts],
        page=page,
        page_size=page_size,
        total=target.count(**filters),
    )


@router.get(
    "/notifications/{attempt_id}",
    response_model=NotificationAttemptResponse,
)
def get_notification(
    attempt_id: UUID,
    session: SessionDependency,
) -> NotificationAttemptResponse:
    return response(service(session).get(attempt_id))


@router.get(
    "/charges/{charge_id}/notifications",
    response_model=Page[NotificationAttemptResponse],
)
def list_charge_notifications(
    charge_id: UUID,
    session: SessionDependency,
    attempt_status: Annotated[
        NotificationSubmissionStatus | None,
        Query(alias="status"),
    ] = None,
    provider: NotificationProvider | None = None,
    notification_type: NotificationType | None = None,
    processed_from: datetime | None = None,
    processed_to: datetime | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=25)] = 25,
) -> Page[NotificationAttemptResponse]:
    validate_range(processed_from, processed_to)
    target = service(session)
    filters = {
        "charge_id": charge_id,
        "status": attempt_status,
        "provider": provider,
        "notification_type": notification_type,
        "processed_from": processed_from,
        "processed_to": processed_to,
    }
    attempts = target.list(
        **filters,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return Page[NotificationAttemptResponse].create(
        items=[response(attempt) for attempt in attempts],
        page=page,
        page_size=page_size,
        total=target.count(**filters),
    )
