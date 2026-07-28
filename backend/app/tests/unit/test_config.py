import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_rejects_default_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+psycopg://db",
            demo_accounts_enabled=False,
            cors_origins="https://cabinet.example",
            s3_access_key="key",
            s3_secret_key="secret",
        )


def test_staging_rejects_open_cors_and_demo_accounts() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            _env_file=None,
            app_env="staging",
            database_url="postgresql+psycopg://db",
            jwt_secret="x" * 32,
            demo_accounts_enabled=True,
            cors_origins="*",
        )


def test_production_accepts_explicit_safe_settings() -> None:
    value = Settings(
        _env_file=None,
        app_env="production",
        database_url="postgresql+psycopg://db",
        jwt_secret="x" * 32,
        demo_accounts_enabled=False,
        cors_origins="https://cabinet.example, https://admin.example",
        s3_access_key="key",
        s3_secret_key="secret",
    )
    assert value.cors_origin_list == ["https://cabinet.example", "https://admin.example"]
