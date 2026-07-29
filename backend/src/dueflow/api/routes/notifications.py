from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from dueflow.api.schemas.notifications import NotificationAttemptResponse
from dueflow.application.notification_history import NotificationHistoryService
from dueflow.infrastructure.db.dependencies import get_session
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)
from dueflow.infrastructure.db.repositories import ChargeRepository

router = APIRouter(tags=["notifications"])
SessionDependency = Annotated[Session, Depends(get_session)]


def service(session: Session) -> NotificationHistoryService:
    return NotificationHistoryService(
        NotificationAttemptRepository(session),
        ChargeRepository(session),
    )


def responses(attempts) -> list[NotificationAttemptResponse]:
    return [
        NotificationAttemptResponse.model_validate(attempt)
        for attempt in attempts
    ]


@router.get(
    "/notifications",
    response_model=list[NotificationAttemptResponse],
)
def list_notifications(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NotificationAttemptResponse]:
    return responses(
        service(session).list(
            charge_id=None,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/charges/{charge_id}/notifications",
    response_model=list[NotificationAttemptResponse],
)
def list_charge_notifications(
    charge_id: UUID,
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NotificationAttemptResponse]:
    return responses(
        service(session).list(
            charge_id=charge_id,
            limit=limit,
            offset=offset,
        )
    )

