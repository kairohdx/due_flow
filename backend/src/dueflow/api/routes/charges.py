from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from dueflow.api.schemas.charges import ChargeCreate, ChargeResponse, ChargeUpdate
from dueflow.application.charges import ChargeService
from dueflow.domain.charges import ChargeStatus
from dueflow.infrastructure.db.dependencies import get_session
from dueflow.infrastructure.db.repositories import ChargeRepository, CustomerRepository

router = APIRouter(prefix="/charges", tags=["charges"])
SessionDependency = Annotated[Session, Depends(get_session)]


def service(session: Session, request: Request) -> ChargeService:
    return ChargeService(
        ChargeRepository(session),
        CustomerRepository(session),
        default_reminder_days_before=(
            request.app.state.settings.default_reminder_days_before
        ),
    )


@router.post(
    "",
    response_model=ChargeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_charge(
    payload: ChargeCreate,
    session: SessionDependency,
    request: Request,
) -> ChargeResponse:
    charge = service(session, request).create(**payload.model_dump())
    return ChargeResponse.model_validate(charge)


@router.get("", response_model=list[ChargeResponse])
def list_charges(
    session: SessionDependency,
    request: Request,
    charge_status: Annotated[ChargeStatus | None, Query(alias="status")] = None,
    customer_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ChargeResponse]:
    charges = service(session, request).list(
        status=charge_status,
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )
    return [ChargeResponse.model_validate(charge) for charge in charges]


@router.get("/{charge_id}", response_model=ChargeResponse)
def get_charge(
    charge_id: UUID,
    session: SessionDependency,
    request: Request,
) -> ChargeResponse:
    charge = service(session, request).get(charge_id)
    return ChargeResponse.model_validate(charge)


@router.put("/{charge_id}", response_model=ChargeResponse)
def update_charge(
    charge_id: UUID,
    payload: ChargeUpdate,
    session: SessionDependency,
    request: Request,
) -> ChargeResponse:
    charge = service(session, request).update(
        charge_id,
        **payload.model_dump(),
    )
    return ChargeResponse.model_validate(charge)


@router.post("/{charge_id}/mark-paid", response_model=ChargeResponse)
def mark_charge_paid(
    charge_id: UUID,
    session: SessionDependency,
    request: Request,
) -> ChargeResponse:
    charge = service(session, request).mark_paid(charge_id)
    return ChargeResponse.model_validate(charge)


@router.post("/{charge_id}/cancel", response_model=ChargeResponse)
def cancel_charge(
    charge_id: UUID,
    session: SessionDependency,
    request: Request,
) -> ChargeResponse:
    charge = service(session, request).cancel(charge_id)
    return ChargeResponse.model_validate(charge)
