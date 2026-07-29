import pytest
from pydantic import ValidationError

from dueflow.config import Settings


def test_settings_use_safe_development_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.app_timezone == "America/Sao_Paulo"
    assert settings.default_reminder_days_before == 3
    assert settings.cors_origins == ["http://localhost:5173"]


def test_settings_reject_unknown_timezone() -> None:
    with pytest.raises(ValidationError, match="fuso horário desconhecido"):
        Settings(app_timezone="Fuso/Inexistente", _env_file=None)


def test_production_requires_secure_auth_settings() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET deve ser alterado"):
        Settings(app_env="production", _env_file=None)

    with pytest.raises(
        ValidationError,
        match="AUTH_COOKIE_SECURE deve ser true",
    ):
        Settings(
            app_env="production",
            jwt_secret="production-secret-with-at-least-thirty-two-characters",
            _env_file=None,
        )
