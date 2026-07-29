from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dueflow.config import Settings
from dueflow.infrastructure.db.base import Base
from dueflow.infrastructure.db import models  # noqa: F401
from dueflow.infrastructure.db.database import Database
from dueflow.main import create_app


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "dueflow-test.db"


@pytest.fixture
def settings(database_path: Path) -> Settings:
    return Settings(
        app_env="test",
        database_url=f"sqlite:///{database_path.as_posix()}",
        cors_origins=["http://testserver"],
    )


@pytest.fixture
def database(settings: Settings) -> Iterator[Database]:
    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    yield database
    database.dispose()


@pytest.fixture
def client(settings: Settings, database: Database) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def customer_payload() -> dict[str, object]:
    return {
        "name": "Empresa Exemplo",
        "phone": "+55 (11) 99999-0000",
        "active": True,
    }


@pytest.fixture
def customer(client: TestClient, customer_payload: dict[str, object]) -> dict:
    response = client.post("/customers", json=customer_payload)
    assert response.status_code == 201
    return response.json()
