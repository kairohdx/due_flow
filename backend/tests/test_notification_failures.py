from datetime import timedelta

from dueflow.application.worker import Worker
from dueflow.domain.messaging import NotificationProvider
from dueflow.infrastructure.db.job_queue import DatabaseJobQueue


class FailingProvider:
    name = NotificationProvider.FAKE

    def send_text(
        self,
        to: str,
        body: str,
        *,
        correlation_id: str,
    ):
        raise RuntimeError("falha controlada do provider")


def create_charge(client, customer_id: str) -> dict:
    response = client.post(
        "/charges",
        json={
            "customer_id": customer_id,
            "description": "Cobrança com falha",
            "amount": "100.00",
            "due_date": "2026-07-29",
            "reminder_days_before": 3,
        },
    )
    assert response.status_code == 201
    return response.json()


def failing_worker(database) -> Worker:
    return Worker(
        database=database,
        queue=DatabaseJobQueue(database),
        provider=FailingProvider(),
        worker_id="failure-worker",
        timezone="America/Sao_Paulo",
        poll_interval_seconds=0.01,
        lock_ttl=timedelta(minutes=5),
    )


def test_provider_failure_is_persisted_without_changing_charge(
    client,
    database,
    customer,
) -> None:
    charge = create_charge(client, customer["id"])
    accepted = client.post(
        f"/charges/{charge['id']}/process",
        json={"reference_date": "2026-07-29"},
    ).json()

    failing_worker(database).run_once()

    job = client.get(f"/processing/jobs/{accepted['job_id']}").json()
    attempts = client.get(
        f"/charges/{charge['id']}/notifications"
    ).json()
    current_charge = client.get(f"/charges/{charge['id']}").json()

    assert job["status"] == "completed"
    assert job["result"]["notification_failed"] == 1
    attempt = attempts["items"][0]
    assert attempt["status"] == "failed"
    assert "falha controlada do provider" in attempt["error"]
    assert attempt["provider_response"] is None
    assert current_charge["status"] == "pending"
