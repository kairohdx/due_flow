from datetime import UTC, datetime, timedelta

from dueflow.domain.jobs import JobStatus, JobType
from dueflow.infrastructure.db.models import ProcessingJob


def add_job(
    database,
    *,
    status: JobStatus,
    now: datetime,
    attempts: int = 1,
    recent: bool = True,
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
    )
    add_job(database, status=JobStatus.FAILED, now=now)
    add_job(
        database,
        status=JobStatus.COMPLETED,
        now=now,
        attempts=3,
        recent=False,
    )

    response = client.get("/dashboard/summary")

    assert response.status_code == 200
    assert {
        key: response.json()[key]
        for key in (
            "customers_total",
            "jobs_queued",
            "jobs_processing",
            "jobs_completed_last_24h",
            "job_retries_last_24h",
            "jobs_failed_last_24h",
        )
    } == {
        "customers_total": 1,
        "jobs_queued": 1,
        "jobs_processing": 1,
        "jobs_completed_last_24h": 1,
        "job_retries_last_24h": 1,
        "jobs_failed_last_24h": 1,
    }
    generated = datetime.fromisoformat(response.json()["generated_at"])
    window = datetime.fromisoformat(response.json()["window_started_at"])
    assert generated - window == timedelta(hours=24)
