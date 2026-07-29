from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from dueflow.api.schemas.processing import (
    JobAcceptedResponse,
    JobResponse,
    ProcessingRequest,
)
from dueflow.application.processing import ProcessingService
from dueflow.infrastructure.db.dependencies import get_session
from dueflow.infrastructure.db.job_queue import DatabaseJobQueue
from dueflow.infrastructure.db.repositories import ChargeRepository
from dueflow.domain.jobs import JobStatus

router = APIRouter(tags=["processing"])
SessionDependency = Annotated[Session, Depends(get_session)]


def service(session: Session, request: Request) -> ProcessingService:
    return ProcessingService(
        DatabaseJobQueue(request.app.state.database),
        ChargeRepository(session),
        max_attempts=request.app.state.settings.worker_max_attempts,
    )


def validate_reference_date(
    payload: ProcessingRequest,
    request: Request,
) -> None:
    if (
        payload.reference_date is not None
        and request.app.state.settings.app_env == "production"
    ):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="reference_date não é permitida em produção",
        )


def accepted(result) -> JobAcceptedResponse:
    return JobAcceptedResponse(
        job_id=result.job.id,
        status=result.job.status,
        created=result.created,
    )


@router.post(
    "/processing/run",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_processing(
    payload: ProcessingRequest,
    session: SessionDependency,
    request: Request,
) -> JobAcceptedResponse:
    validate_reference_date(payload, request)
    result = service(session, request).enqueue_due_charges(
        reference_date=payload.reference_date
    )
    return accepted(result)


@router.post(
    "/charges/{charge_id}/process",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_charge_processing(
    charge_id: UUID,
    payload: ProcessingRequest,
    session: SessionDependency,
    request: Request,
) -> JobAcceptedResponse:
    validate_reference_date(payload, request)
    result = service(session, request).enqueue_charge(
        charge_id,
        reference_date=payload.reference_date,
    )
    return accepted(result)


@router.get(
    "/processing/jobs",
    response_model=list[JobResponse],
)
def list_processing_jobs(
    session: SessionDependency,
    request: Request,
    job_status: Annotated[JobStatus | None, Query(alias="status")] = None,
    origin: Literal["manual", "automatic"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[JobResponse]:
    jobs = service(session, request).list_jobs(
        status=job_status,
        origin=origin,
        limit=limit,
        offset=offset,
    )
    return [JobResponse.model_validate(job) for job in jobs]


@router.get(
    "/processing/jobs/{job_id}",
    response_model=JobResponse,
)
def get_processing_job(
    job_id: UUID,
    session: SessionDependency,
    request: Request,
) -> JobResponse:
    job = service(session, request).get_job(job_id)
    return JobResponse.model_validate(job)
