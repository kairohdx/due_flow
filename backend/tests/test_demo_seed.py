from datetime import date

from sqlalchemy import func, select

from dueflow.application.demo_seed import seed_demo
from dueflow.infrastructure.db.models import Charge, Customer


def test_demo_seed_is_deterministic_and_idempotent(database) -> None:
    with database.session() as session:
        first = seed_demo(session, reference_date=date(2026, 7, 29))
    with database.session() as session:
        second = seed_demo(session, reference_date=date(2026, 7, 29))
        customer_count = session.scalar(
            select(func.count()).select_from(Customer)
        )
        charges = list(
            session.scalars(select(Charge).order_by(Charge.due_date))
        )

    assert first.customers_created == 3
    assert first.charges_created == 3
    assert second.customers_created == 0
    assert second.charges_created == 0
    assert customer_count == 3
    assert [charge.due_date.isoformat() for charge in charges] == [
        "2026-07-27",
        "2026-07-29",
        "2026-07-31",
    ]
