from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dueflow.config import Settings
from dueflow.application.auth import AuthService
from dueflow.infrastructure.db.auth_repository import AuthRepository
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
        jwt_secret="test-secret-with-at-least-thirty-two-characters",
    )


@pytest.fixture
def database(settings: Settings) -> Iterator[Database]:
    database = Database(settings.database_url)
    Base.metadata.create_all(database.engine)
    yield database
    database.dispose()


@pytest.fixture
def unauthenticated_client(
    settings: Settings,
    database: Database,
) -> Iterator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client(
    settings: Settings,
    database: Database,
    unauthenticated_client: TestClient,
) -> Iterator[TestClient]:
    password = "not-a-real-test-password"
    with database.session() as session:
        AuthService(AuthRepository(session), settings).create_user(
            email="admin@example.com",
            name="Administrador de Teste",
            password=password,
        )
    login = unauthenticated_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": password},
    )
    assert login.status_code == 200
    unauthenticated_client.headers.update(
        {"Authorization": f"Bearer {login.json()['access_token']}"}
    )
    yield unauthenticated_client


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
