from datetime import date
from decimal import Decimal
from uuid import UUID

from dueflow.application.errors import InvalidStateError, ResourceNotFoundError
from dueflow.domain.charges import ChargeStatus
from dueflow.infrastructure.db.models import Charge
from dueflow.infrastructure.db.repositories import ChargeRepository, CustomerRepository


class ChargeService:
    def __init__(
        self,
        repository: ChargeRepository,
        customer_repository: CustomerRepository,
        *,
        default_reminder_days_before: int,
    ) -> None:
        self.repository = repository
        self.customer_repository = customer_repository
        self.default_reminder_days_before = default_reminder_days_before

    def create(
        self,
        *,
        customer_id: UUID,
        description: str,
        amount: Decimal,
        due_date: date,
        reminder_days_before: int | None,
    ) -> Charge:
        self._ensure_customer_exists(customer_id)
        charge = Charge(
            customer_id=customer_id,
            description=description,
            amount=amount,
            due_date=due_date,
            reminder_days_before=(
                reminder_days_before
                if reminder_days_before is not None
                else self.default_reminder_days_before
            ),
        )
        return self.repository.add(charge)

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
        return self.repository.list(
            status=status,
            customer_id=customer_id,
            due_from=due_from,
            due_to=due_to,
            search=search,
            limit=limit,
            offset=offset,
        )

    def count(
        self,
        *,
        status: ChargeStatus | None,
        customer_id: UUID | None,
        due_from: date | None,
        due_to: date | None,
        search: str | None,
    ) -> int:
        return self.repository.count(
            status=status,
            customer_id=customer_id,
            due_from=due_from,
            due_to=due_to,
            search=search,
        )

    def get(self, charge_id: UUID) -> Charge:
        charge = self.repository.get(charge_id)
        if charge is None:
            raise ResourceNotFoundError("cobrança não encontrada")
        return charge

    def update(
        self,
        charge_id: UUID,
        *,
        customer_id: UUID,
        description: str,
        amount: Decimal,
        due_date: date,
        reminder_days_before: int,
    ) -> Charge:
        charge = self.get(charge_id)
        if charge.status is not ChargeStatus.PENDING:
            raise InvalidStateError(
                "somente cobranças pendentes podem ser editadas"
            )
        self._ensure_customer_exists(customer_id)
        charge.customer_id = customer_id
        charge.description = description
        charge.amount = amount
        charge.due_date = due_date
        charge.reminder_days_before = reminder_days_before
        return self.repository.save(charge)

    def mark_paid(self, charge_id: UUID) -> Charge:
        charge = self.get(charge_id)
        if charge.status is ChargeStatus.PAID:
            return charge
        if charge.status is ChargeStatus.CANCELED:
            raise InvalidStateError(
                "uma cobrança cancelada não pode ser marcada como paga"
            )
        charge.status = ChargeStatus.PAID
        return self.repository.save(charge)

    def cancel(self, charge_id: UUID) -> Charge:
        charge = self.get(charge_id)
        if charge.status is ChargeStatus.CANCELED:
            return charge
        if charge.status is ChargeStatus.PAID:
            raise InvalidStateError("uma cobrança paga não pode ser cancelada")
        charge.status = ChargeStatus.CANCELED
        return self.repository.save(charge)

    def _ensure_customer_exists(self, customer_id: UUID) -> None:
        if self.customer_repository.get(customer_id) is None:
            raise ResourceNotFoundError("cliente não encontrado")
