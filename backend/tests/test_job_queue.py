from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from dueflow.domain.jobs import JobStatus, JobType
from dueflow.infrastructure.db.database import Database
from dueflow.infrastructure.db.job_queue import DatabaseJobQueue

NOW = datetime(2026, 7, 29, 12, tzinfo=UTC)


def enqueue(queue: DatabaseJobQueue, *, max_attempts: int = 3):
    return queue.enqueue(
        job_type=JobType.PROCESS_DUE_CHARGES,
        payload={"origin": "test"},
        scheduled_for=NOW,
        max_attempts=max_attempts,
        deduplication_key="batch:test",
    )


def test_enqueue_deduplicates_active_job(database: Database) -> None:
    queue = DatabaseJobQueue(database)

    first = enqueue(queue)
    second = enqueue(queue)

    assert first.created is True
    assert second.created is False
    assert second.job.id == first.job.id
    assert first.job.status is JobStatus.QUEUED


def test_only_one_worker_claims_a_job(database: Database) -> None:
    queue = DatabaseJobQueue(database)
    queued = enqueue(queue).job

    def claim(worker_id: str):
        return DatabaseJobQueue(database).claim(worker_id=worker_id, now=NOW)

    with ThreadPoolExecutor(max_workers=2) as executor:
        claimed = list(executor.map(claim, ["worker-a", "worker-b"]))

    jobs = [job for job in claimed if job is not None]
    assert len(jobs) == 1
    assert jobs[0].id == queued.id
    assert jobs[0].status is JobStatus.PROCESSING
    assert jobs[0].attempts == 1


def test_completed_job_releases_deduplication_key(database: Database) -> None:
    queue = DatabaseJobQueue(database)
    first = enqueue(queue).job
    claimed = queue.claim(worker_id="worker-a", now=NOW)
    assert claimed is not None

    queue.complete(
        job_id=claimed.id,
        worker_id="worker-a",
        result={"evaluated": 0},
        now=NOW + timedelta(seconds=1),
    )
    second = enqueue(queue)

    assert queue.get(first.id).status is JobStatus.COMPLETED
    assert second.created is True
    assert second.job.id != first.id


def test_completed_automatic_job_retains_window_key(
    database: Database,
) -> None:
    queue = DatabaseJobQueue(database)
    first = queue.enqueue(
        job_type=JobType.PROCESS_DUE_CHARGES,
        payload={"origin": "automatic"},
        scheduled_for=NOW,
        max_attempts=3,
        deduplication_key="automation:window-1",
        retain_deduplication_key=True,
    ).job
    claimed = queue.claim(worker_id="worker-a", now=NOW)
    assert claimed is not None
    queue.complete(
        job_id=claimed.id,
        worker_id="worker-a",
        result={"evaluated": 0},
        now=NOW + timedelta(seconds=1),
    )

    repeated = queue.enqueue(
        job_type=JobType.PROCESS_DUE_CHARGES,
        payload={"origin": "automatic"},
        scheduled_for=NOW,
        max_attempts=3,
        deduplication_key="automation:window-1",
        retain_deduplication_key=True,
    )

    assert repeated.created is False
    assert repeated.job.id == first.id
    assert repeated.job.status is JobStatus.COMPLETED


def test_expired_lock_is_requeued(database: Database) -> None:
    queue = DatabaseJobQueue(database)
    job = enqueue(queue).job
    queue.claim(worker_id="abandoned", now=NOW)

    recovered = queue.recover_stale(
        now=NOW + timedelta(minutes=10),
        lock_ttl=timedelta(minutes=5),
    )

    assert recovered == 1
    current = queue.get(job.id)
    assert current is not None
    assert current.status is JobStatus.QUEUED
    assert current.locked_by is None


def test_expired_lock_fails_job_after_last_attempt(database: Database) -> None:
    queue = DatabaseJobQueue(database)
    job = enqueue(queue, max_attempts=1).job
    queue.claim(worker_id="abandoned", now=NOW)

    queue.recover_stale(
        now=NOW + timedelta(minutes=10),
        lock_ttl=timedelta(minutes=5),
    )

    current = queue.get(job.id)
    assert current is not None
    assert current.status is JobStatus.FAILED
    assert current.finished_at is not None
