from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from dueflow.application.auth import AuthService
from dueflow.application.worker import Worker
from dueflow.application.whatsapp import WhatsAppProvider
from dueflow.config import Settings
from dueflow.infrastructure.db.database import Database
from dueflow.infrastructure.db.auth_repository import AuthRepository
from dueflow.infrastructure.db.job_queue import DatabaseJobQueue
from dueflow.infrastructure.messaging.fake import FakeWhatsAppProvider
from dueflow.main import create_app


def create_charge(
    client: TestClient,
    customer_id: str,
    *,
    description: str = "Cobrança para processar",
    due_date: str = "2026-07-29",
) -> dict:
    response = client.post(
        "/charges",
        json={
            "customer_id": customer_id,
            "description": description,
            "amount": "100.00",
            "due_date": due_date,
            "reminder_days_before": 3,
        },
    )
    assert response.status_code == 201
    return response.json()


def worker(
    database: Database,
    provider: WhatsAppProvider | None = None,
) -> Worker:
    return Worker(
        database=database,
        queue=DatabaseJobQueue(database),
        provider=provider or FakeWhatsAppProvider(),
        worker_id="test-worker",
        timezone="America/Sao_Paulo",
        poll_interval_seconds=0.01,
        lock_ttl=timedelta(minutes=5),
    )


def test_individual_processing_is_asynchronous_and_explainable(
    client: TestClient,
    database: Database,
    customer: dict,
) -> None:
    charge = create_charge(client, customer["id"])

    accepted = client.post(
        f"/charges/{charge['id']}/process",
        json={"reference_date": "2026-07-29"},
    )

    assert accepted.status_code == 202
    accepted_body = accepted.json()
    assert accepted_body["status"] == "queued"
    assert accepted_body["created"] is True

    before = client.get(f"/processing/jobs/{accepted_body['job_id']}")
    assert before.status_code == 200
    assert before.json()["status"] == "queued"
    assert before.json()["result"] is None

    assert worker(database).run_once() is True

    after = client.get(f"/processing/jobs/{accepted_body['job_id']}")
    assert after.status_code == 200
    body = after.json()
    assert body["status"] == "completed"
    assert body["origin"] == "manual"
    assert body["charge_id"] == charge["id"]
    assert body["terminal"] is True
    assert body["duration_ms"] >= 0
    assert body["attempts"] == 1
    assert body["result"]["evaluated"] == 1
    assert body["result"]["eligible"] == 1
    assert body["result"]["simulated"] == 1
    assert body["result"]["deduplicated"] == 0
    evaluation = body["result"]["evaluations"][0]
    assert evaluation["decision"]["policy_name"] == "DueTodayPolicy"
    assert evaluation["trace"]["strategy"] == "first_match"
    assert evaluation["notification"]["status"] == "simulated"
    assert evaluation["notification"]["provider_message_id"].startswith(
        "wamid.fake."
    )
    assert "+5511999990000" not in str(body["result"])

    history = client.get(
        f"/charges/{charge['id']}/notifications"
    )
    assert history.status_code == 200
    attempts = history.json()["items"]
    assert len(attempts) == 1
    assert attempts[0]["status"] == "simulated"
    assert attempts[0]["processing_job_id"] == accepted_body["job_id"]
    assert attempts[0]["destination"] == "+5511999990000"
    assert attempts[0]["provider_response"]["request"]["to"] == "5511999990000"
    assert attempts[0]["provider_response"]["request"]["type"] == "text"
    detail = client.get(f"/notifications/{attempts[0]['id']}")
    filtered = client.get(
        "/notifications?status=simulated&provider=fake"
        "&notification_type=due_today"
    )
    assert detail.status_code == 200
    assert detail.json()["id"] == attempts[0]["id"]
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["id"] == attempts[0]["id"]


def test_repeated_request_returns_same_active_job(
    client: TestClient,
    customer: dict,
) -> None:
    charge = create_charge(client, customer["id"])
    endpoint = f"/charges/{charge['id']}/process"

    first = client.post(endpoint, json={}).json()
    second_response = client.post(endpoint, json={})
    second = second_response.json()

    assert second_response.status_code == 202
    assert first["job_id"] == second["job_id"]
    assert second["created"] is False


def test_batch_job_evaluates_pending_charges(
    client: TestClient,
    database: Database,
    customer: dict,
) -> None:
    create_charge(client, customer["id"], description="Vence hoje")
    create_charge(
        client,
        customer["id"],
        description="Fora da janela",
        due_date="2026-08-10",
    )

    accepted = client.post(
        "/processing/run",
        json={"reference_date": "2026-07-29"},
    ).json()
    worker(database).run_once()
    completed = client.get(
        f"/processing/jobs/{accepted['job_id']}"
    ).json()

    assert completed["status"] == "completed"
    assert completed["result"]["evaluated"] == 2
    assert completed["result"]["eligible"] == 1
    assert completed["result"]["skipped"] == 1
    assert completed["result"]["simulated"] == 1


def test_notification_is_not_sent_twice(
    client: TestClient,
    database: Database,
    customer: dict,
) -> None:
    charge = create_charge(client, customer["id"])
    endpoint = f"/charges/{charge['id']}/process"
    payload = {"reference_date": "2026-07-29"}

    first = client.post(endpoint, json=payload).json()
    worker(database).run_once()
    assert client.get(
        f"/processing/jobs/{first['job_id']}"
    ).json()["status"] == "completed"

    second = client.post(endpoint, json=payload).json()
    worker(database).run_once()
    second_job = client.get(
        f"/processing/jobs/{second['job_id']}"
    ).json()
    attempts = client.get(
        f"/charges/{charge['id']}/notifications"
    ).json()["items"]

    assert first["job_id"] != second["job_id"]
    assert second_job["result"]["simulated"] == 0
    assert second_job["result"]["deduplicated"] == 1
    assert second_job["result"]["evaluations"][0]["notification"][
        "deduplicated"
    ] is True
    assert len(attempts) == 1


def test_skipped_decision_does_not_create_attempt(
    client: TestClient,
    database: Database,
    customer: dict,
) -> None:
    charge = create_charge(
        client,
        customer["id"],
        due_date="2026-08-10",
    )
    accepted = client.post(
        f"/charges/{charge['id']}/process",
        json={"reference_date": "2026-07-29"},
    ).json()

    worker(database).run_once()
    job = client.get(f"/processing/jobs/{accepted['job_id']}").json()
    attempts = client.get(
        f"/charges/{charge['id']}/notifications"
    ).json()["items"]

    assert job["result"]["skipped"] == 1
    assert job["result"]["evaluations"][0]["notification"] is None
    assert attempts == []


def test_processing_unknown_charge_returns_404(client: TestClient) -> None:
    response = client.post(f"/charges/{uuid4()}/process", json={})

    assert response.status_code == 404
    assert response.json() == {"detail": "cobrança não encontrada"}


def test_processing_unknown_job_returns_404(client: TestClient) -> None:
    response = client.get(f"/processing/jobs/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "job não encontrado"}


def test_reference_date_is_rejected_in_production(
    database_path,
) -> None:
    settings = Settings(
        app_env="production",
        database_url=f"sqlite:///{database_path.as_posix()}",
        jwt_secret="production-secret-with-at-least-thirty-two-characters",
        auth_cookie_secure=True,
        _env_file=None,
    )
    app = create_app(settings)
    from dueflow.infrastructure.db.base import Base

    Base.metadata.create_all(app.state.database.engine)
    with app.state.database.session() as session:
        AuthService(AuthRepository(session), settings).create_user(
            email="production@example.com",
            name="Produção",
            password="not-a-real-test-password",
        )
    with TestClient(app) as production_client:
        login = production_client.post(
            "/auth/login",
            json={
                "email": "production@example.com",
                "password": "not-a-real-test-password",
            },
        )
        production_client.headers["Authorization"] = (
            f"Bearer {login.json()['access_token']}"
        )
        response = production_client.post(
            "/processing/run",
            json={"reference_date": "2026-07-29"},
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "reference_date não é permitida em produção"
    }
