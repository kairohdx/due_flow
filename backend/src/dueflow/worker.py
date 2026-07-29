import logging
import os
import socket
from datetime import timedelta
from uuid import uuid4

from dueflow.application.scheduler import AutomationScheduler
from dueflow.application.fake_delivery import FakeDeliverySimulator
from dueflow.application.whatsapp import WhatsAppProvider
from dueflow.application.message_delivery import TemplateConfiguration
from dueflow.application.worker import Worker
from dueflow.config import Settings, get_settings
from dueflow.infrastructure.db.automation_repository import (
    AutomationRepository,
)
from dueflow.infrastructure.db.database import Database
from dueflow.infrastructure.db.job_queue import DatabaseJobQueue
from dueflow.infrastructure.messaging.fake import FakeWhatsAppProvider
from dueflow.infrastructure.messaging.meta import MetaWhatsAppProvider


def build_provider(settings: Settings) -> WhatsAppProvider:
    if settings.message_provider == "fake":
        return FakeWhatsAppProvider()
    if settings.meta_whatsapp_token is None:
        raise RuntimeError("token da Meta ausente")
    return MetaWhatsAppProvider(
        token=settings.meta_whatsapp_token.get_secret_value(),
        phone_number_id=settings.meta_whatsapp_phone_number_id,
        graph_api_version=settings.meta_graph_api_version,
        base_url=settings.meta_graph_api_base_url,
        timeout_seconds=settings.meta_request_timeout_seconds,
    )


def build_worker() -> Worker:
    settings = get_settings()
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
    worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
    fake_delivery_simulator = None
    if settings.message_provider == "fake":
        fake_delivery_simulator = FakeDeliverySimulator(
            database,
            outcome=settings.fake_delivery_outcome,
            delay_seconds=settings.fake_delivery_delay_seconds,
            error_code=settings.fake_delivery_error_code,
        )
    return Worker(
        database=database,
        queue=queue,
        provider=build_provider(settings),
        worker_id=worker_id,
        timezone=settings.app_timezone,
        poll_interval_seconds=settings.worker_poll_interval_seconds,
        lock_ttl=timedelta(seconds=settings.worker_lock_ttl_seconds),
        scheduler=scheduler,
        fake_delivery_simulator=fake_delivery_simulator,
        template_configuration=TemplateConfiguration(
            mode=settings.meta_template_mode,
            name=settings.meta_template_name,
            language=settings.meta_template_language,
        ),
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
