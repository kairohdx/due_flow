from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from dueflow.config import get_settings


def test_initial_migration_creates_and_removes_expected_tables(
    database_path: Path,
    monkeypatch,
) -> None:
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(backend_dir / "alembic.ini")

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    assert set(inspect(engine).get_table_names()) == {
        "alembic_version",
        "automation_settings",
        "charges",
        "customers",
        "notification_attempts",
        "processing_jobs",
    }

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]

    engine.dispose()
    get_settings.cache_clear()
