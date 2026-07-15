"""Общая обвязка интеграционных тестов: временная SQLite-база и TestClient."""

import os
import tempfile

import pytest

# Настраиваем тестовую БД ДО импорта приложения (settings кэшируется).
_TMP_DB = os.path.join(tempfile.gettempdir(), "nklab_test.db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TMP_DB}"
os.environ["JWT_SECRET"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

# импорт моделей для метаданных
from app.modules.auth import models as _auth  # noqa: E402,F401
from app.modules.catalog import models as _catalog  # noqa: E402,F401
from app.modules.import_data import models as _import  # noqa: E402,F401
from app.modules.operator import models as _operator  # noqa: E402,F401


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    """Зарегистрированный клиент с токеном в заголовке."""
    client.post(
        "/api/auth/register",
        json={
            "email": "user@test.ru",
            "password": "password",
            "full_name": "Тест",
            "client_name": "ТестКлиент",
        },
    )
    token = client.post(
        "/api/auth/login", json={"email": "user@test.ru", "password": "password"}
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
