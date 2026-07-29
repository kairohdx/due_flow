from uuid import uuid4

from fastapi.testclient import TestClient


def charge_payload(customer_id: str, **overrides) -> dict:
    payload = {
        "customer_id": customer_id,
        "description": "Mensalidade de julho",
        "amount": "1234.56",
        "due_date": "2026-07-31",
    }
    payload.update(overrides)
    return payload


def test_create_charge_preserves_decimal_and_uses_default_reminder(
    client: TestClient,
    customer: dict,
) -> None:
    response = client.post("/charges", json=charge_payload(customer["id"]))

    assert response.status_code == 201
    body = response.json()
    assert body["customer_id"] == customer["id"]
    assert body["amount"] == "1234.56"
    assert body["status"] == "pending"
    assert body["reminder_days_before"] == 3


def test_create_charge_requires_existing_customer(client: TestClient) -> None:
    response = client.post("/charges", json=charge_payload(str(uuid4())))

    assert response.status_code == 404
    assert response.json() == {"detail": "cliente não encontrado"}


def test_charge_rejects_invalid_money(client: TestClient, customer: dict) -> None:
    too_precise = client.post(
        "/charges",
        json=charge_payload(customer["id"], amount="10.999"),
    )
    zero = client.post(
        "/charges",
        json=charge_payload(customer["id"], amount="0.00"),
    )

    assert too_precise.status_code == 422
    assert zero.status_code == 422


def test_list_charge_filters_by_status_and_customer(
    client: TestClient,
    customer: dict,
) -> None:
    pending = client.post("/charges", json=charge_payload(customer["id"])).json()
    paid = client.post(
        "/charges",
        json=charge_payload(
            customer["id"],
            description="Cobrança paga",
            due_date="2026-08-01",
        ),
    ).json()
    client.post(f"/charges/{paid['id']}/mark-paid")

    pending_response = client.get(
        f"/charges?status=pending&customer_id={customer['id']}"
    )
    paid_response = client.get("/charges?status=paid")

    assert pending_response.status_code == 200
    assert [item["id"] for item in pending_response.json()] == [pending["id"]]
    assert paid_response.status_code == 200
    assert [item["id"] for item in paid_response.json()] == [paid["id"]]


def test_update_pending_charge(client: TestClient, customer: dict) -> None:
    charge = client.post("/charges", json=charge_payload(customer["id"])).json()

    response = client.put(
        f"/charges/{charge['id']}",
        json=charge_payload(
            customer["id"],
            description="Descrição atualizada",
            amount="10.50",
            due_date="2026-08-10",
            reminder_days_before=5,
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Descrição atualizada"
    assert body["amount"] == "10.50"
    assert body["due_date"] == "2026-08-10"
    assert body["reminder_days_before"] == 5


def test_mark_paid_is_idempotent_and_blocks_cancel(
    client: TestClient,
    customer: dict,
) -> None:
    charge = client.post("/charges", json=charge_payload(customer["id"])).json()
    endpoint = f"/charges/{charge['id']}/mark-paid"

    first = client.post(endpoint)
    second = client.post(endpoint)
    conflicting = client.post(f"/charges/{charge['id']}/cancel")

    assert first.status_code == 200
    assert first.json()["status"] == "paid"
    assert second.status_code == 200
    assert second.json()["status"] == "paid"
    assert conflicting.status_code == 409
    assert conflicting.json() == {
        "detail": "uma cobrança paga não pode ser cancelada"
    }


def test_cancel_is_idempotent_and_blocks_editing(
    client: TestClient,
    customer: dict,
) -> None:
    charge = client.post("/charges", json=charge_payload(customer["id"])).json()
    cancel_endpoint = f"/charges/{charge['id']}/cancel"

    first = client.post(cancel_endpoint)
    second = client.post(cancel_endpoint)
    update = client.put(
        f"/charges/{charge['id']}",
        json=charge_payload(
            customer["id"],
            reminder_days_before=1,
        ),
    )

    assert first.status_code == 200
    assert first.json()["status"] == "canceled"
    assert second.status_code == 200
    assert update.status_code == 409
    assert update.json() == {
        "detail": "somente cobranças pendentes podem ser editadas"
    }


def test_charge_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/charges/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "cobrança não encontrada"}

