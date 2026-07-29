from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from dueflow.api.schemas.charges import ChargeCreate, ChargeResponse, ChargeUpdate
from dueflow.api.schemas.common import Page
from dueflow.api.query_validation import validate_range
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


@router.get("", response_model=Page[ChargeResponse])
def list_charges(
    session: SessionDependency,
    request: Request,
    charge_status: Annotated[ChargeStatus | None, Query(alias="status")] = None,
    customer_id: UUID | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=25)] = 25,
) -> Page[ChargeResponse]:
    validate_range(due_from, due_to)
    target = service(session, request)
    charges = target.list(
        status=charge_status,
        customer_id=customer_id,
        due_from=due_from,
        due_to=due_to,
        search=search,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return Page[ChargeResponse].create(
        items=[ChargeResponse.model_validate(charge) for charge in charges],
        page=page,
        page_size=page_size,
        total=target.count(
            status=charge_status,
            customer_id=customer_id,
            due_from=due_from,
            due_to=due_to,
            search=search,
        ),
    )


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
