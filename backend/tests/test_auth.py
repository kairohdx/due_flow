from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from dueflow.application.auth import AuthService
from dueflow.config import Settings
from dueflow.infrastructure.db.auth_repository import AuthRepository
from dueflow.infrastructure.db.database import Database
from dueflow.infrastructure.db.models import RefreshSession, User


PASSWORD = "correct-horse-battery-staple"


def create_user(database: Database, settings: Settings, *, active: bool = True) -> User:
    with database.session() as session:
        return AuthService(AuthRepository(session), settings).create_user(
            email="owner@example.com",
            name="Responsável",
            password=PASSWORD,
            active=active,
        )


def test_business_routes_require_authentication(
    unauthenticated_client: TestClient,
) -> None:
    response = unauthenticated_client.get("/customers")

    assert response.status_code == 401
    assert response.json() == {"detail": "não autenticado"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_health_remains_public(unauthenticated_client: TestClient) -> None:
    assert unauthenticated_client.get("/health").status_code == 200


def test_login_sets_httponly_cookie_and_me_returns_profile(
    unauthenticated_client: TestClient,
    database: Database,
    settings: Settings,
) -> None:
    user = create_user(database, settings)

    login = unauthenticated_client.post(
        "/auth/login",
        json={"email": " OWNER@EXAMPLE.COM ", "password": PASSWORD},
    )

    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["expires_in"] == 900
    cookie = login.headers["set-cookie"]
    assert settings.auth_refresh_cookie_name in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie

    me = unauthenticated_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json() == {
        "id": str(user.id),
        "email": "owner@example.com",
        "name": "Responsável",
    }


def test_login_rejects_invalid_credentials_and_inactive_user(
    unauthenticated_client: TestClient,
    database: Database,
    settings: Settings,
) -> None:
    create_user(database, settings, active=False)

    wrong_password = unauthenticated_client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    )
    inactive = unauthenticated_client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": PASSWORD},
    )

    assert wrong_password.status_code == 401
    assert wrong_password.json() == {"detail": "e-mail ou senha inválidos"}
    assert inactive.status_code == 401
    assert inactive.json() == {"detail": "usuário inativo"}


def test_refresh_rotates_session_and_rejects_previous_token(
    unauthenticated_client: TestClient,
    database: Database,
    settings: Settings,
) -> None:
    create_user(database, settings)
    login = unauthenticated_client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": PASSWORD},
    )
    original_refresh = unauthenticated_client.cookies[
        settings.auth_refresh_cookie_name
    ]

    refreshed = unauthenticated_client.post("/auth/refresh")
    rotated_refresh = unauthenticated_client.cookies[
        settings.auth_refresh_cookie_name
    ]

    assert refreshed.status_code == 200
    assert rotated_refresh != original_refresh

    replay = TestClient(unauthenticated_client.app)
    replay.cookies.set(
        settings.auth_refresh_cookie_name,
        original_refresh,
        path="/auth",
    )
    assert replay.post("/auth/refresh").status_code == 401

    with database.session() as session:
        sessions = list(
            session.scalars(
                select(RefreshSession).order_by(RefreshSession.created_at)
            )
        )
        assert len(sessions) == 2
        assert sessions[0].revoked_at is not None
        assert sessions[0].replaced_by_id == sessions[1].id


def test_logout_revokes_session_and_access_token(
    unauthenticated_client: TestClient,
    database: Database,
    settings: Settings,
) -> None:
    create_user(database, settings)
    login = unauthenticated_client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": PASSWORD},
    )
    access_token = login.json()["access_token"]

    logout = unauthenticated_client.post("/auth/logout")

    assert logout.status_code == 204
    assert settings.auth_refresh_cookie_name not in unauthenticated_client.cookies
    denied = unauthenticated_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert denied.status_code == 401

    with database.session() as session:
        refresh_session = session.scalar(select(RefreshSession))
        assert refresh_session is not None
        assert refresh_session.revoked_at is not None
        assert refresh_session.revoked_at <= datetime.now(timezone.utc).replace(
            tzinfo=None
        )


def test_reset_password_rejects_old_password_and_revokes_sessions(
    unauthenticated_client: TestClient,
    database: Database,
    settings: Settings,
) -> None:
    create_user(database, settings)
    login = unauthenticated_client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": PASSWORD},
    )
    old_access_token = login.json()["access_token"]

    with database.session() as session:
        AuthService(AuthRepository(session), settings).reset_password(
            email=" OWNER@EXAMPLE.COM ",
            password="new-secure-password-456",
        )

    old_password = unauthenticated_client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": PASSWORD},
    )
    new_password = unauthenticated_client.post(
        "/auth/login",
        json={
            "email": "owner@example.com",
            "password": "new-secure-password-456",
        },
    )
    revoked_access = unauthenticated_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {old_access_token}"},
    )

    assert old_password.status_code == 401
    assert new_password.status_code == 200
    assert revoked_access.status_code == 401


def test_authenticated_user_changes_password_and_sessions_are_revoked(
    unauthenticated_client: TestClient,
    database: Database,
    settings: Settings,
) -> None:
    create_user(database, settings)
    login = unauthenticated_client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": PASSWORD},
    )
    access_token = login.json()["access_token"]

    changed = unauthenticated_client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": PASSWORD,
            "new_password": "new-secure-password-789",
        },
    )

    assert changed.status_code == 204
    assert settings.auth_refresh_cookie_name not in unauthenticated_client.cookies
    assert (
        unauthenticated_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        ).status_code
        == 401
    )
    assert (
        unauthenticated_client.post(
            "/auth/login",
            json={
                "email": "owner@example.com",
                "password": "new-secure-password-789",
            },
        ).status_code
        == 200
    )
