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
        metrics_token="m" * 16,
    )
    assert value.cors_origin_list == ["https://cabinet.example", "https://admin.example"]


def test_nk_api_requires_https_and_credentials() -> None:
    with pytest.raises(ValidationError, match="NK_API_KEY"):
        Settings(_env_file=None, nk_api_enabled=True)
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            _env_file=None,
            nk_api_enabled=True,
            nk_api_key="secret",
            nk_api_base_url="http://nk.example",
        )


def test_import_limits_are_bounded() -> None:
    with pytest.raises(ValidationError, match="MAX_IMPORT_ROWS"):
        Settings(_env_file=None, max_import_rows=0)
