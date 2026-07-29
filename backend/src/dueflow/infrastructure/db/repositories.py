from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from dueflow.domain.charges import ChargeStatus
from dueflow.infrastructure.db.models import Charge, Customer


class CustomerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, customer: Customer) -> Customer:
        self.session.add(customer)
        return self._commit(customer)

    def get(self, customer_id: UUID) -> Customer | None:
        return self.session.get(Customer, customer_id)

    def list(
        self,
        *,
        active: bool | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[Customer]:
        statement = select(Customer)
        if active is not None:
            statement = statement.where(Customer.active.is_(active))
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(Customer.name.ilike(pattern), Customer.phone.ilike(pattern))
            )
        statement = (
            statement
            .order_by(Customer.created_at.desc(), Customer.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

    def count(
        self,
        *,
        active: bool | None,
        search: str | None,
    ) -> int:
        statement = select(func.count()).select_from(Customer)
        if active is not None:
            statement = statement.where(Customer.active.is_(active))
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(Customer.name.ilike(pattern), Customer.phone.ilike(pattern))
            )
        return int(self.session.scalar(statement) or 0)

    def save(self, customer: Customer) -> Customer:
        return self._commit(customer)

    def _commit(self, customer: Customer) -> Customer:
        self.session.commit()
        self.session.refresh(customer)
        return customer


class ChargeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, charge: Charge) -> Charge:
        self.session.add(charge)
        return self._commit(charge)

    def get(self, charge_id: UUID) -> Charge | None:
        return self.session.get(Charge, charge_id)

    def list(
        self,
        *,
        status: ChargeStatus | None,
        customer_id: UUID | None,
        due_from: date | None,
        due_to: date | None,
        search: str | None,
        limit: int,
        offset: int,
    ) -> list[Charge]:
        statement = select(Charge)
        if status is not None:
            statement = statement.where(Charge.status == status)
        if customer_id is not None:
            statement = statement.where(Charge.customer_id == customer_id)
        if due_from is not None:
            statement = statement.where(Charge.due_date >= due_from)
        if due_to is not None:
            statement = statement.where(Charge.due_date <= due_to)
        if search:
            statement = statement.where(
                Charge.description.ilike(f"%{search.strip()}%")
            )
        statement = (
            statement.order_by(Charge.due_date, Charge.created_at.desc(), Charge.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

    def count(
        self,
        *,
        status: ChargeStatus | None,
        customer_id: UUID | None,
        due_from: date | None,
        due_to: date | None,
        search: str | None,
    ) -> int:
        statement = select(func.count()).select_from(Charge)
        if status is not None:
            statement = statement.where(Charge.status == status)
        if customer_id is not None:
            statement = statement.where(Charge.customer_id == customer_id)
        if due_from is not None:
            statement = statement.where(Charge.due_date >= due_from)
        if due_to is not None:
            statement = statement.where(Charge.due_date <= due_to)
        if search:
            statement = statement.where(
                Charge.description.ilike(f"%{search.strip()}%")
            )
        return int(self.session.scalar(statement) or 0)

    def list_pending(self, *, limit: int = 1000) -> list[Charge]:
        statement = (
            select(Charge)
            .where(Charge.status == ChargeStatus.PENDING)
            .order_by(Charge.due_date, Charge.created_at, Charge.id)
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def save(self, charge: Charge) -> Charge:
        return self._commit(charge)

    def _commit(self, charge: Charge) -> Charge:
        self.session.commit()
        self.session.refresh(charge)
        return charge
