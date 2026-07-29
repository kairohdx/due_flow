from uuid import uuid4

from fastapi.testclient import TestClient


def test_create_customer_normalizes_phone(
    client: TestClient,
    customer_payload: dict[str, object],
) -> None:
    response = client.post("/customers", json=customer_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Empresa Exemplo"
    assert body["phone"] == "+5511999990000"
    assert body["active"] is True
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]


def test_list_get_and_update_customer(
    client: TestClient,
    customer: dict,
) -> None:
    customer_id = customer["id"]

    listed = client.get("/customers")
    fetched = client.get(f"/customers/{customer_id}")
    updated = client.put(
        f"/customers/{customer_id}",
        json={
            "name": "Empresa Atualizada",
            "phone": "+55 11 98888-1111",
            "active": False,
        },
    )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [customer_id]
    assert fetched.status_code == 200
    assert fetched.json()["phone"] == "+5511999990000"
    assert updated.status_code == 200
    assert updated.json()["name"] == "Empresa Atualizada"
    assert updated.json()["phone"] == "+5511988881111"
    assert updated.json()["active"] is False


def test_customer_requires_country_code(client: TestClient) -> None:
    response = client.post(
        "/customers",
        json={
            "name": "Sem DDI",
            "phone": "(11) 99999-0000",
        },
    )

    assert response.status_code == 422
    assert "código do país" in response.text


def test_customer_not_found_returns_404(client: TestClient) -> None:
    response = client.get(f"/customers/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "cliente não encontrado"}


def test_customer_pagination_is_validated(client: TestClient) -> None:
    response = client.get("/customers?limit=101&offset=-1")

    assert response.status_code == 422

