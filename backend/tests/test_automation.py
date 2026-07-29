from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from dueflow.application.scheduler import AutomationScheduler
from dueflow.application.worker import Worker
from dueflow.domain.jobs import JobStatus
from dueflow.infrastructure.db.automation_repository import (
    AutomationRepository,
)
from dueflow.infrastructure.db.job_queue import DatabaseJobQueue
from dueflow.infrastructure.db.models import ProcessingJob
from dueflow.infrastructure.messaging.fake import FakeWhatsAppProvider

NOW = datetime(2026, 7, 29, 12, tzinfo=UTC)


def repository(database) -> AutomationRepository:
    return AutomationRepository(
        database,
        default_interval_seconds=120,
    )


def scheduler(database) -> AutomationScheduler:
    return AutomationScheduler(
        repository(database),
        DatabaseJobQueue(database),
        timezone="America/Sao_Paulo",
        max_attempts=3,
    )


def automatic_worker(database, *, now=NOW) -> Worker:
    return Worker(
        database=database,
        queue=DatabaseJobQueue(database),
        provider=FakeWhatsAppProvider(),
        worker_id="automatic-worker",
        timezone="America/Sao_Paulo",
        poll_interval_seconds=0.01,
        lock_ttl=timedelta(minutes=5),
        now_provider=lambda: now,
        scheduler=scheduler(database),
    )


def create_due_today_charge(client, customer) -> dict:
    response = client.post(
        "/charges",
        json={
            "customer_id": customer["id"],
            "description": "Cobrança automática",
            "amount": "80.00",
            "due_date": "2026-07-29",
            "reminder_days_before": 3,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_automation_controls_are_persisted(client) -> None:
    initial = client.get("/automation")
    enabled = client.post(
        "/automation/enable",
        json={"interval_seconds": 120},
    )
    persisted = client.get("/automation")
    disabled = client.post("/automation/disable")

    assert initial.status_code == 200
    assert initial.json()["enabled"] is False
    assert enabled.status_code == 200
    assert enabled.json()["enabled"] is True
    assert enabled.json()["interval_seconds"] == 120
    assert enabled.json()["next_run_at"] is not None
    assert persisted.json()["enabled"] is True
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert disabled.json()["next_run_at"] is None


def test_enable_validates_interval(client) -> None:
    response = client.post(
        "/automation/enable",
        json={"interval_seconds": 0},
    )

    assert response.status_code == 422


def test_configure_interval_preserves_automation_state(client) -> None:
    paused = client.put("/automation", json={"interval_seconds": 300})
    client.post("/automation/enable", json={"interval_seconds": 120})
    active = client.put("/automation", json={"interval_seconds": 600})

    assert paused.status_code == 200
    assert paused.json()["enabled"] is False
    assert paused.json()["interval_seconds"] == 300
    assert active.status_code == 200
    assert active.json()["enabled"] is True
    assert active.json()["interval_seconds"] == 600
    assert active.json()["next_run_at"] is not None


def test_enabled_automation_creates_and_processes_job(
    client,
    database,
    customer,
) -> None:
    charge = create_due_today_charge(client, customer)
    repository(database).enable(now=NOW, interval_seconds=120)

    processed = automatic_worker(database).run_once()

    assert processed is True
    with database.session() as session:
        job = session.scalar(
            select(ProcessingJob).where(
                ProcessingJob.payload["origin"].as_string() == "automatic"
            )
        )
        assert job is not None
        job_id = job.id
    completed = client.get(f"/processing/jobs/{job_id}").json()
    attempts = client.get(
        f"/charges/{charge['id']}/notifications"
    ).json()
    state = client.get("/automation").json()
    automatic_jobs = client.get(
        "/processing/jobs?origin=automatic&status=completed"
    ).json()

    assert completed["status"] == JobStatus.COMPLETED.value
    assert completed["payload"]["origin"] == "automatic"
    assert completed["payload"]["reference_date"] == "2026-07-29"
    assert completed["retain_deduplication_key"] is True
    assert completed["result"]["simulated"] == 1
    assert attempts["items"][0]["submission_status"] == "simulated"
    assert state["last_enqueued_at"] is not None
    assert state["next_run_at"] is not None
    assert [item["id"] for item in automatic_jobs["items"]] == [str(job_id)]


def test_disabled_automation_does_not_create_job(database) -> None:
    assert automatic_worker(database).run_once() is False

    with database.session() as session:
        assert session.scalar(select(ProcessingJob)) is None


def test_same_automatic_window_is_claimed_once(database) -> None:
    repository(database).enable(now=NOW, interval_seconds=120)

    def tick(_: int):
        return scheduler(database).tick(now=NOW)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(tick, [1, 2]))

    created = [
        result
        for result in results
        if result is not None and result.created
    ]
    assert len(created) == 1
    with database.session() as session:
        assert len(list(session.scalars(select(ProcessingJob)))) == 1


def test_scheduler_waits_until_next_interval(database) -> None:
    automation = repository(database)
    automation.enable(now=NOW, interval_seconds=120)
    target = scheduler(database)

    first = target.tick(now=NOW)
    early = target.tick(now=NOW + timedelta(seconds=119))
    next_window = target.tick(now=NOW + timedelta(seconds=120))

    assert first is not None and first.created is True
    assert early is None
    assert next_window is not None and next_window.created is True
    assert next_window.job.id != first.job.id
