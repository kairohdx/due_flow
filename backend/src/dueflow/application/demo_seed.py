from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from dueflow.domain.charges import ChargeStatus
from dueflow.infrastructure.db.models import Charge, Customer


@dataclass(frozen=True, slots=True)
class DemoSeedResult:
    customers_created: int
    charges_created: int


CUSTOMERS = (
    (
        UUID("10000000-0000-0000-0000-000000000001"),
        "Padaria Pão Dourado",
        "+5511999990001",
    ),
    (
        UUID("10000000-0000-0000-0000-000000000002"),
        "Mercado Boa Compra",
        "+5511999990002",
    ),
    (
        UUID("10000000-0000-0000-0000-000000000003"),
        "Café da Praça",
        "+5511999990003",
    ),
)


def seed_demo(session: Session, *, reference_date: date) -> DemoSeedResult:
    customers_created = 0
    for customer_id, name, phone in CUSTOMERS:
        if session.get(Customer, customer_id) is None:
            session.add(
                Customer(
                    id=customer_id,
                    name=name,
                    phone=phone,
                    active=True,
                )
            )
            customers_created += 1
    session.flush()

    charges = (
        (
            UUID("20000000-0000-0000-0000-000000000001"),
            CUSTOMERS[0][0],
            "Fornecimento de julho",
            Decimal("189.90"),
            reference_date - timedelta(days=2),
        ),
        (
            UUID("20000000-0000-0000-0000-000000000002"),
            CUSTOMERS[1][0],
            "Pedido 1048",
            Decimal("249.90"),
            reference_date,
        ),
        (
            UUID("20000000-0000-0000-0000-000000000003"),
            CUSTOMERS[2][0],
            "Mensalidade de agosto",
            Decimal("79.90"),
            reference_date + timedelta(days=2),
        ),
    )
    charges_created = 0
    for charge_id, customer_id, description, amount, due_date in charges:
        if session.get(Charge, charge_id) is None:
            session.add(
                Charge(
                    id=charge_id,
                    customer_id=customer_id,
                    description=description,
                    amount=amount,
                    due_date=due_date,
                    status=ChargeStatus.PENDING,
                    reminder_days_before=3,
                )
            )
            charges_created += 1
    session.commit()
    return DemoSeedResult(customers_created, charges_created)
