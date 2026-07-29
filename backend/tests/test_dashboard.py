from datetime import UTC, datetime, timedelta
from uuid import UUID

from dueflow.domain.jobs import JobStatus, JobType
from dueflow.domain.messaging import (
    NotificationAttemptStatus,
    NotificationProvider,
)
from dueflow.domain.notifications import NotificationType
from dueflow.infrastructure.db.models import NotificationAttempt, ProcessingJob


def add_job(
    database,
    *,
    status: JobStatus,
    now: datetime,
    attempts: int = 1,
    recent: bool = True,
    evaluated: int = 0,
) -> None:
    moment = now - (timedelta(hours=1) if recent else timedelta(hours=25))
    with database.session() as session:
        session.add(
            ProcessingJob(
                type=JobType.PROCESS_DUE_CHARGES,
                status=status,
                payload={"origin": "automatic"},
                scheduled_for=moment,
                attempts=attempts,
                max_attempts=3,
                result=(
                    {"evaluated": evaluated}
                    if status == JobStatus.COMPLETED
                    else None
                ),
                started_at=moment if attempts else None,
                finished_at=(
                    moment
                    if status in {JobStatus.COMPLETED, JobStatus.FAILED}
                    else None
                ),
            )
        )
        session.commit()


def test_dashboard_summary_reports_queue_and_last_24_hours(
    client,
    database,
    customer,
) -> None:
    now = datetime.now(UTC)
    add_job(database, status=JobStatus.QUEUED, now=now, attempts=0)
    add_job(database, status=JobStatus.PROCESSING, now=now)
    add_job(
        database,
        status=JobStatus.COMPLETED,
        now=now,
        attempts=2,
        evaluated=7,
    )
    add_job(database, status=JobStatus.FAILED, now=now)
    add_job(
        database,
        status=JobStatus.COMPLETED,
        now=now,
        attempts=3,
        recent=False,
        evaluated=99,
    )
    charge = client.post(
        "/charges",
        json={
            "customer_id": customer["id"],
            "description": "Cobrança vencendo hoje",
            "amount": "50.00",
            "due_date": now.date().isoformat(),
        },
    ).json()
    for description, due_date in (
        ("Cobrança vencida", now.date() - timedelta(days=1)),
        ("Cobrança vencendo em breve", now.date() + timedelta(days=5)),
    ):
        created = client.post(
            "/charges",
            json={
                "customer_id": customer["id"],
                "description": description,
                "amount": "50.00",
                "due_date": due_date.isoformat(),
            },
        )
        assert created.status_code == 201
    with database.session() as session:
        for index, status in enumerate(
            [
                NotificationAttemptStatus.SIMULATED,
                NotificationAttemptStatus.FAILED,
            ]
        ):
            session.add(
                NotificationAttempt(
                    charge_id=UUID(charge["id"]),
                    notification_type=NotificationType.DUE_TODAY,
                    provider=NotificationProvider.FAKE,
                    destination="+5511999990000",
                    message="Mensagem de teste",
                    status=status,
                    error="falha controlada" if status.value == "failed" else None,
                    idempotency_key=f"dashboard:{index}",
                    policy_name="DueTodayPolicy",
                    decision_reason="teste do dashboard",
                    processed_at=now - timedelta(hours=1),
                )
            )
        session.commit()

    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    assert {
        key: response.json()[key]
        for key in (
            "customers_total",
            "charges_pending",
            "charges_overdue",
            "charges_due_today",
            "charges_due_next_7_days",
            "charges_evaluated_last_24h",
            "notifications_processed_last_24h",
            "notification_failures_last_24h",
            "jobs_queued",
            "jobs_processing",
            "jobs_completed_last_24h",
            "job_retries_last_24h",
            "jobs_failed_last_24h",
        )
    } == {
        "customers_total": 1,
        "charges_pending": 3,
        "charges_overdue": 1,
        "charges_due_today": 1,
        "charges_due_next_7_days": 1,
        "charges_evaluated_last_24h": 7,
        "notifications_processed_last_24h": 1,
        "notification_failures_last_24h": 1,
        "jobs_queued": 1,
        "jobs_processing": 1,
        "jobs_completed_last_24h": 1,
        "job_retries_last_24h": 1,
        "jobs_failed_last_24h": 1,
    }
    generated = datetime.fromisoformat(response.json()["generated_at"])
    window = datetime.fromisoformat(response.json()["window_started_at"])
    assert generated - window == timedelta(hours=24)
