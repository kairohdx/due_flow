import logging
import os
import socket
from datetime import timedelta
from uuid import uuid4

from dueflow.application.worker import Worker
from dueflow.application.scheduler import AutomationScheduler
from dueflow.config import get_settings
from dueflow.infrastructure.db.database import Database
from dueflow.infrastructure.db.automation_repository import (
    AutomationRepository,
)
from dueflow.infrastructure.db.job_queue import DatabaseJobQueue
from dueflow.infrastructure.messaging.fake import FakeWhatsAppProvider


def build_worker() -> Worker:
    settings = get_settings()
    if settings.message_provider != "fake":
        raise RuntimeError(
            "somente MESSAGE_PROVIDER=fake está disponível nesta etapa"
        )
    database = Database(settings.database_url)
    queue = DatabaseJobQueue(database)
    scheduler = AutomationScheduler(
        AutomationRepository(
            database,
            default_interval_seconds=settings.automation_interval_seconds,
        ),
        queue,
        timezone=settings.app_timezone,
        max_attempts=settings.worker_max_attempts,
    )
    worker_id = (
        f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
    )
    return Worker(
        database=database,
        queue=queue,
        provider=FakeWhatsAppProvider(),
        worker_id=worker_id,
        timezone=settings.app_timezone,
        poll_interval_seconds=settings.worker_poll_interval_seconds,
        lock_ttl=timedelta(seconds=settings.worker_lock_ttl_seconds),
        scheduler=scheduler,
    )


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    worker = build_worker()
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("worker encerrado")
    finally:
        worker.database.dispose()


if __name__ == "__main__":
    main()
