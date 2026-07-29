import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from dueflow.application.job_queue import JobQueue
from dueflow.application.job_processor import ProcessingJobHandler
from dueflow.application.scheduler import AutomationScheduler
from dueflow.application.fake_delivery import FakeDeliverySimulator
from dueflow.application.whatsapp import WhatsAppProvider
from dueflow.application.message_delivery import TemplateConfiguration
from dueflow.infrastructure.db.database import Database
from dueflow.infrastructure.db.notification_repository import (
    NotificationAttemptRepository,
)
from dueflow.infrastructure.db.repositories import ChargeRepository, CustomerRepository

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        *,
        database: Database,
        queue: JobQueue,
        provider: WhatsAppProvider,
        worker_id: str,
        timezone: str,
        poll_interval_seconds: float,
        lock_ttl: timedelta,
        now_provider: Callable[[], datetime] | None = None,
        scheduler: AutomationScheduler | None = None,
        fake_delivery_simulator: FakeDeliverySimulator | None = None,
        template_configuration: TemplateConfiguration | None = None,
    ) -> None:
        self.database = database
        self.queue = queue
        self.provider = provider
        self.worker_id = worker_id
        self.timezone = timezone
        self.poll_interval_seconds = poll_interval_seconds
        self.lock_ttl = lock_ttl
        self.now_provider = now_provider or (lambda: datetime.now(UTC))
        self.scheduler = scheduler
        self.fake_delivery_simulator = fake_delivery_simulator
        self.template_configuration = template_configuration

    def run_once(self) -> bool:
        now = self.now_provider()
        if self.scheduler is not None:
            automatic_job = self.scheduler.tick(now=now)
            if automatic_job is not None and automatic_job.created:
                logger.info(
                    "job automático criado: id=%s",
                    automatic_job.job.id,
                )
        recovered = self.queue.recover_stale(now=now, lock_ttl=self.lock_ttl)
        if recovered:
            logger.warning("jobs com lock expirado recuperados: %s", recovered)

        simulated = 0
        if self.fake_delivery_simulator is not None:
            simulated = self.fake_delivery_simulator.tick(now=now).advanced
            if simulated:
                logger.info(
                    "eventos de entrega simulados avançados: %s",
                    simulated,
                )

        job = self.queue.claim(worker_id=self.worker_id, now=now)
        if job is None:
            return simulated > 0

        logger.info("job iniciado: id=%s type=%s", job.id, job.type.value)
        try:
            with self.database.session() as session:
                handler = ProcessingJobHandler(
                    ChargeRepository(session),
                    CustomerRepository(session),
                    NotificationAttemptRepository(session),
                    self.provider,
                    timezone=self.timezone,
                    template_configuration=self.template_configuration,
                )
                result = handler.process(job)
            self.queue.complete(
                job_id=job.id,
                worker_id=self.worker_id,
                result=result,
                now=self.now_provider(),
            )
            logger.info("job concluído: id=%s", job.id)
        except Exception as exc:
            logger.exception("job falhou: id=%s", job.id)
            self.queue.fail(
                job_id=job.id,
                worker_id=self.worker_id,
                error=f"{type(exc).__name__}: {exc}",
                now=self.now_provider(),
                retry_delay=timedelta(seconds=self.poll_interval_seconds),
            )
        return True

    def run_forever(self) -> None:
        logger.info("worker iniciado: id=%s", self.worker_id)
        while True:
            processed = self.run_once()
            if not processed:
                time.sleep(self.poll_interval_seconds)
