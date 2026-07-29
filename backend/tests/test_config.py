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


def test_meta_provider_requires_complete_and_valid_configuration() -> None:
    with pytest.raises(
        ValidationError,
        match="META_WHATSAPP_TOKEN",
    ):
        Settings(message_provider="meta", _env_file=None)

    with pytest.raises(
        ValidationError,
        match="PHONE_NUMBER_ID deve conter apenas números",
    ):
        Settings(
            message_provider="meta",
            meta_whatsapp_token="-".join(["not", "a", "real", "token"]),
            meta_whatsapp_phone_number_id="phone-id",
            meta_graph_api_version="v99.0",
            _env_file=None,
        )

    settings = Settings(
        message_provider="meta",
        meta_whatsapp_token="-".join(["not", "a", "real", "token"]),
        meta_whatsapp_phone_number_id="123456789",
        meta_graph_api_version="v99.0",
        _env_file=None,
    )

    assert settings.message_provider == "meta"
    assert repr(settings.meta_whatsapp_token) == "SecretStr('**********')"


def test_neon_postgres_url_uses_psycopg_driver() -> None:
    settings = Settings(
        database_url=(
            "postgresql://user:password@example.neon.tech/neondb"
            "?sslmode=require"
        ),
        _env_file=None,
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
