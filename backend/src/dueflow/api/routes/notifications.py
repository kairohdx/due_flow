from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from dueflow.api.schemas.notifications import (
    NotificationAttemptResponse,
    RecoveryAssessmentResponse,
)
from dueflow.api.schemas.processing import JobAcceptedResponse
from dueflow.api.auth_dependencies import CurrentUser
from dueflow.api.schemas.common import Page
from dueflow.api.query_validation import validate_range
from dueflow.application.notification_history import NotificationHistoryService
from dueflow.application.notification_retries import NotificationRetryService
from dueflow.application.message_delivery import TemplateConfiguration
from dueflow.infrastructure.db.dependencies import get_session
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)
from dueflow.infrastructure.db.repositories import (
    ChargeRepository,
    CustomerRepository,
)
from dueflow.infrastructure.db.job_queue import DatabaseJobQueue
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


def retry_service(
    session: Session,
    request: Request,
) -> NotificationRetryService:
    return NotificationRetryService(
        NotificationAttemptRepository(session),
        ChargeRepository(session),
        CustomerRepository(session),
        queue=DatabaseJobQueue(request.app.state.database),
        max_attempts=request.app.state.settings.worker_max_attempts,
        template_configuration=TemplateConfiguration(
            mode=request.app.state.settings.meta_template_mode,
            name=request.app.state.settings.meta_template_name,
            language=request.app.state.settings.meta_template_language,
        ),
    )


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
    "/notifications/{attempt_id}/recovery",
    response_model=RecoveryAssessmentResponse,
)
def get_notification_recovery(
    attempt_id: UUID,
    session: SessionDependency,
    request: Request,
) -> RecoveryAssessmentResponse:
    assessment = retry_service(session, request).assess(attempt_id)
    return RecoveryAssessmentResponse.model_validate(assessment.as_dict())


@router.post(
    "/notifications/{attempt_id}/retry",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_notification(
    attempt_id: UUID,
    session: SessionDependency,
    request: Request,
    current_user: CurrentUser,
) -> JobAcceptedResponse:
    result = retry_service(session, request).enqueue(
        attempt_id,
        requested_by_user_id=current_user.id,
    )
    return JobAcceptedResponse(
        job_id=result.job.id,
        status=result.job.status,
        created=result.created,
    )


@router.post(
    "/notifications/{attempt_id}/retry-template",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_notification_with_template(
    attempt_id: UUID,
    session: SessionDependency,
    request: Request,
    current_user: CurrentUser,
) -> JobAcceptedResponse:
    result = retry_service(session, request).enqueue_template(
        attempt_id,
        requested_by_user_id=current_user.id,
    )
    return JobAcceptedResponse(
        job_id=result.job.id,
        status=result.job.status,
        created=result.created,
    )


@router.get(
    "/notifications/{attempt_id}/attempts",
    response_model=list[NotificationAttemptResponse],
)
def list_notification_attempts(
    attempt_id: UUID,
    session: SessionDependency,
) -> list[NotificationAttemptResponse]:
    repository = NotificationAttemptRepository(session)
    attempt = service(session).get(attempt_id)
    return [response(item) for item in repository.family(attempt)]


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
