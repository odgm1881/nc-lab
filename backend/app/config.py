"""Настройки приложения через pydantic-settings. Секреты — только из окружения."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # База данных. По умолчанию — sqlite, чтобы прототип запускался без Postgres.
    # В проде: postgresql+psycopg://... (см. .env.example).
    database_url: str = "sqlite+pysqlite:///./nklab.db"

    # JWT
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # S3-совместимое хранилище (российское облако). Если ключи пустые — локальное хранилище.
    s3_endpoint_url: str = "https://storage.yandexcloud.net"
    s3_bucket: str = "nklab-files"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "ru-central1"

    # Приложение
    app_env: str = "development"
    app_version: str = "0.1.0"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    demo_accounts_enabled: bool = True
    max_upload_bytes: int = 10 * 1024 * 1024
    log_level: str = "INFO"

    @model_validator(mode="after")
    def validate_deployment_safety(self) -> "Settings":
        """Не позволять staging/production стартовать с небезопасным конфигом."""
        if self.app_env not in {"development", "test", "staging", "production"}:
            raise ValueError("APP_ENV должен быть development, test, staging или production")
        if self.max_upload_bytes < 1 or self.max_upload_bytes > 100 * 1024 * 1024:
            raise ValueError("MAX_UPLOAD_BYTES должен быть от 1 байта до 100 МБ")

        if self.app_env in {"staging", "production"}:
            if self.jwt_secret == "change-me" or len(self.jwt_secret) < 32:
                raise ValueError(
                    "JWT_SECRET для staging/production должен быть не короче 32 символов"
                )
            if not self.cors_origin_list or "*" in self.cors_origin_list:
                raise ValueError(
                    "CORS_ORIGINS для staging/production должен содержать явные домены"
                )
            if self.demo_accounts_enabled:
                raise ValueError("DEMO_ACCOUNTS_ENABLED должен быть false в staging/production")
            if self.is_sqlite:
                raise ValueError("SQLite запрещён в staging/production; используйте PostgreSQL")

        if self.app_env == "production" and not self.s3_enabled:
            raise ValueError("S3-хранилище обязательно в production")
        return self

    @property
    def s3_enabled(self) -> bool:
        return bool(self.s3_access_key and self.s3_secret_key)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
