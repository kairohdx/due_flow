from fastapi.testclient import TestClient

from dueflow.config import Settings
from dueflow.main import create_app


def test_health_reports_api_and_database_as_ready(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unavailable(tmp_path) -> None:
    missing_parent = tmp_path / "missing" / "database.db"
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{missing_parent.as_posix()}",
        _env_file=None,
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "banco de dados indisponível"}

