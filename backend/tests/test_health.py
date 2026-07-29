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


def test_spa_is_served_without_shadowing_api(
    settings,
    database,
    tmp_path,
) -> None:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text(
        "<html><body>DueFlow SPA</body></html>",
        encoding="utf-8",
    )
    app = create_app(
        settings.model_copy(
            update={"frontend_dist_path": str(frontend)}
        )
    )

    with TestClient(app) as test_client:
        assert test_client.get("/health").status_code == 200
        response = test_client.get("/cobrancas/qualquer-id")

    assert response.status_code == 200
    assert "DueFlow SPA" in response.text
