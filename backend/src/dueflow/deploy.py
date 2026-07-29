import logging
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import uvicorn
from alembic import command
from alembic.config import Config

from dueflow.application.auth import AuthService, DuplicateUserError
from dueflow.application.demo_seed import seed_demo
from dueflow.config import get_settings
from dueflow.infrastructure.db.auth_repository import AuthRepository
from dueflow.infrastructure.db.database import Database

logger = logging.getLogger(__name__)


def migrate() -> None:
    backend_dir = Path(
        os.getenv("DUEFLOW_BACKEND_DIR", str(Path.cwd()))
    ).resolve()
    if not (backend_dir / "alembic.ini").is_file():
        raise RuntimeError(
            f"alembic.ini não encontrado em {backend_dir}"
        )
    command.upgrade(Config(backend_dir / "alembic.ini"), "head")


def bootstrap() -> None:
    settings = get_settings()
    email = os.getenv("INITIAL_ADMIN_EMAIL", "").strip()
    name = os.getenv("INITIAL_ADMIN_NAME", "Administrador").strip()
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
    if not email or not password:
        raise RuntimeError(
            "INITIAL_ADMIN_EMAIL e INITIAL_ADMIN_PASSWORD são obrigatórios"
        )
    database = Database(settings.database_url)
    try:
        with database.session() as session:
            try:
                AuthService(AuthRepository(session), settings).create_user(
                    email=email,
                    name=name,
                    password=password,
                )
                logger.info("usuário administrativo inicial criado")
            except DuplicateUserError:
                logger.info("usuário administrativo inicial já existe")
        if settings.demo_seed_enabled:
            with database.session() as session:
                reference_date = datetime.now(
                    ZoneInfo(settings.app_timezone)
                ).date()
                result = seed_demo(session, reference_date=reference_date)
                logger.info(
                    "seed da demo aplicado: clientes=%s cobranças=%s",
                    result.customers_created,
                    result.charges_created,
                )
    finally:
        database.dispose()


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    migrate()
    bootstrap()
    worker = subprocess.Popen([sys.executable, "-m", "dueflow.worker"])

    def stop_worker(*_: object) -> None:
        if worker.poll() is None:
            worker.terminate()

    signal.signal(signal.SIGTERM, stop_worker)
    try:
        uvicorn.run(
            "dueflow.main:app",
            host=settings.app_host,
            port=int(os.getenv("PORT", str(settings.app_port))),
            proxy_headers=True,
            forwarded_allow_ips="*",
        )
    finally:
        stop_worker()
        try:
            worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.kill()
