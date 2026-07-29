from datetime import UTC, datetime
from uuid import UUID

import pytest

from dueflow.application.fake_delivery import FakeDeliverySimulator
from dueflow.domain.messaging import (
    NotificationDeliveryStatus,
    NotificationProvider,
    NotificationSubmissionStatus,
)
from dueflow.domain.notifications import NotificationType
from dueflow.infrastructure.db.models import NotificationAttempt


def create_simulated_attempt(client, database, customer) -> tuple[str, str]:
    charge = client.post(
        "/charges",
        json={
            "customer_id": customer["id"],
            "description": "Cobrança da entrega simulada",
            "amount": "100.00",
            "due_date": "2026-07-29",
        },
    ).json()
    with database.session() as session:
        attempt = NotificationAttempt(
            charge_id=UUID(charge["id"]),
            notification_type=NotificationType.DUE_TODAY,
            provider=NotificationProvider.FAKE,
            destination="+5511999990000",
            message="Mensagem simulada",
            submission_status=NotificationSubmissionStatus.SIMULATED,
            delivery_status=NotificationDeliveryStatus.PENDING,
            provider_message_id="wamid.fake.delivery-test",
            idempotency_key=f"fake-delivery:{charge['id']}",
            policy_name="DueTodayPolicy",
            decision_reason="teste do simulador",
            processed_at=datetime.now(UTC),
        )
        session.add(attempt)
        session.commit()
        return charge["id"], str(attempt.id)


@pytest.mark.parametrize(
    ("outcome", "ticks", "expected", "error_code"),
    [
        ("delivered", 2, "delivered", None),
        ("read", 3, "read", None),
        ("failed", 2, "failed", 131047),
    ],
)
def test_fake_delivery_advances_asynchronously_through_real_states(
    client,
    database,
    customer,
    outcome,
    ticks,
    expected,
    error_code,
) -> None:
    _, attempt_id = create_simulated_attempt(client, database, customer)
    simulator = FakeDeliverySimulator(
        database,
        outcome=outcome,
        delay_seconds=0,
        error_code=131047,
    )

    states = []
    for _ in range(ticks):
        result = simulator.tick(now=datetime.now(UTC))
        assert result.advanced == 1
        states.append(
            client.get(f"/notifications/{attempt_id}").json()[
                "delivery_status"
            ]
        )

    attempt = client.get(f"/notifications/{attempt_id}").json()
    summary = client.get("/dashboard/summary").json()
    assert states[0] == "sent"
    assert attempt["submission_status"] == "simulated"
    assert attempt["delivery_status"] == expected
    assert attempt["delivery_error_code"] == error_code
    assert attempt["delivery_response"]["simulated"] is True
    assert summary["submissions_simulated_last_24h"] == 1
    assert summary["deliveries_awaiting"] == 0
    assert summary["deliveries_confirmed_last_24h"] == (
        1 if expected in {"delivered", "read"} else 0
    )
    assert summary["deliveries_read_last_24h"] == (
        1 if expected == "read" else 0
    )
    assert summary["deliveries_failed_last_24h"] == (
        1 if expected == "failed" else 0
    )
    if expected == "failed":
        assert attempt["delivery_error_info"]["action_type"] == "template"
