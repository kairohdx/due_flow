from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
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

    def list(self, *, limit: int, offset: int) -> list[Customer]:
        statement = (
            select(Customer)
            .order_by(Customer.created_at.desc(), Customer.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

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
        limit: int,
        offset: int,
    ) -> list[Charge]:
        statement = select(Charge)
        if status is not None:
            statement = statement.where(Charge.status == status)
        if customer_id is not None:
            statement = statement.where(Charge.customer_id == customer_id)
        statement = (
            statement.order_by(Charge.due_date, Charge.created_at.desc(), Charge.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

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
