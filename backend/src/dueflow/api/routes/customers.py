from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from dueflow.api.schemas.customers import (
    CustomerCreate,
    CustomerResponse,
    CustomerUpdate,
)
from dueflow.api.schemas.common import Page
from dueflow.application.customers import CustomerService
from dueflow.infrastructure.db.dependencies import get_session
from dueflow.infrastructure.db.repositories import CustomerRepository

router = APIRouter(prefix="/customers", tags=["customers"])
SessionDependency = Annotated[Session, Depends(get_session)]


def service(session: Session) -> CustomerService:
    return CustomerService(CustomerRepository(session))


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    payload: CustomerCreate,
    session: SessionDependency,
) -> CustomerResponse:
    customer = service(session).create(**payload.model_dump())
    return CustomerResponse.model_validate(customer)


@router.get("", response_model=Page[CustomerResponse])
def list_customers(
    session: SessionDependency,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=25)] = 25,
    active: bool | None = None,
    search: Annotated[str | None, Query(min_length=1, max_length=160)] = None,
) -> Page[CustomerResponse]:
    target = service(session)
    customers = target.list(
        active=active,
        search=search,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return Page[CustomerResponse].create(
        items=[
            CustomerResponse.model_validate(customer) for customer in customers
        ],
        page=page,
        page_size=page_size,
        total=target.count(active=active, search=search),
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    session: SessionDependency,
) -> CustomerResponse:
    customer = service(session).get(customer_id)
    return CustomerResponse.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    session: SessionDependency,
) -> CustomerResponse:
    customer = service(session).update(customer_id, **payload.model_dump())
    return CustomerResponse.model_validate(customer)
