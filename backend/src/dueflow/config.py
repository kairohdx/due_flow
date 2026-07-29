from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65_535)
    database_url: str = "sqlite:///./dueflow.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    app_timezone: str = "America/Sao_Paulo"
    default_reminder_days_before: int = Field(default=3, ge=0)
    jwt_secret: str = Field(
        default="dueflow-development-secret-change-before-production",
        min_length=32,
    )
    jwt_issuer: str = "dueflow"
    jwt_audience: str = "dueflow-web"
    jwt_access_token_expires_minutes: int = Field(default=15, ge=1, le=1440)
    auth_refresh_token_expires_days: int = Field(default=30, ge=1, le=365)
    auth_refresh_cookie_name: str = "dueflow_refresh"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    message_provider: Literal["fake", "meta"] = "fake"
    meta_whatsapp_token: SecretStr | None = None
    meta_whatsapp_phone_number_id: str = ""
    meta_graph_api_version: str = ""
    meta_graph_api_base_url: str = "https://graph.facebook.com"
    meta_request_timeout_seconds: float = Field(default=10, gt=0, le=60)
    automation_interval_seconds: int = Field(default=120, ge=1, le=86_400)
    worker_poll_interval_seconds: float = Field(default=2, gt=0, le=60)
    worker_lock_ttl_seconds: int = Field(default=300, ge=10)
    worker_max_attempts: int = Field(default=3, ge=1, le=10)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"fuso horário desconhecido: {value}") from exc
        return value

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("JWT_SECRET não pode ser vazio")
        return value

    @model_validator(mode="after")
    def validate_auth_security(self) -> "Settings":
        development_secret = (
            "dueflow-development-secret-change-before-production"
        )
        if self.app_env == "production":
            if self.jwt_secret == development_secret:
                raise ValueError(
                    "JWT_SECRET deve ser alterado em produção"
                )
            if not self.auth_cookie_secure:
                raise ValueError(
                    "AUTH_COOKIE_SECURE deve ser true em produção"
                )
        if self.auth_cookie_samesite == "none" and not self.auth_cookie_secure:
            raise ValueError(
                "SameSite=None exige AUTH_COOKIE_SECURE=true"
            )
        if self.message_provider == "meta":
            missing = []
            if (
                self.meta_whatsapp_token is None
                or not self.meta_whatsapp_token.get_secret_value().strip()
            ):
                missing.append("META_WHATSAPP_TOKEN")
            if not self.meta_whatsapp_phone_number_id.strip():
                missing.append("META_WHATSAPP_PHONE_NUMBER_ID")
            if not self.meta_graph_api_version.strip():
                missing.append("META_GRAPH_API_VERSION")
            if missing:
                raise ValueError(
                    "MESSAGE_PROVIDER=meta exige " + ", ".join(missing)
                )
            if not self.meta_whatsapp_phone_number_id.isdigit():
                raise ValueError(
                    "META_WHATSAPP_PHONE_NUMBER_ID deve conter apenas números"
                )
            version = self.meta_graph_api_version
            if (
                not version.startswith("v")
                or not version[1:].replace(".", "", 1).isdigit()
                or "." not in version
            ):
                raise ValueError(
                    "META_GRAPH_API_VERSION deve seguir o formato vNN.N"
                )
            if not self.meta_graph_api_base_url.startswith(("https://", "http://")):
                raise ValueError(
                    "META_GRAPH_API_BASE_URL deve ser uma URL HTTP(S)"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
