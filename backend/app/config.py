"""Настройки приложения через pydantic-settings. Секреты — только из окружения."""

from functools import lru_cache

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

    @property
    def s3_enabled(self) -> bool:
        return bool(self.s3_access_key and self.s3_secret_key)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
