from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
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
    message_provider: Literal["fake", "meta"] = "fake"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
