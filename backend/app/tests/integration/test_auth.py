"""Интеграционные тесты аутентификации."""

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.modules.audit.models import AuditEvent


def test_register_and_login(client: TestClient):
    r = client.post(
        "/api/auth/register",
        json={
            "email": "a@test.ru",
            "password": "password",
            "full_name": "Анна",
            "client_name": "Орг",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "a@test.ru"
    assert r.json()["role"] == "client"

    r = client.post("/api/auth/login", json={"email": "a@test.ru", "password": "password"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_duplicate_email_conflict(client: TestClient):
    payload = {
        "email": "b@test.ru",
        "password": "password",
        "full_name": "",
        "client_name": "Орг",
    }
    client.post("/api/auth/register", json=payload)
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 409


def test_wrong_password(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"email": "c@test.ru", "password": "password", "client_name": "Орг"},
    )
    r = client.post("/api/auth/login", json={"email": "c@test.ru", "password": "wrong"})
    assert r.status_code == 401
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.action == "auth.login_failed"))
        assert event is not None
        assert event.actor_id is not None
        assert event.details["email"] == "c@test.ru"


def test_unknown_email_login_is_audited(client: TestClient):
    response = client.post(
        "/api/auth/login", json={"email": "missing@test.ru", "password": "wrong"}
    )

    assert response.status_code == 401
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.action == "auth.login_failed"))
        assert event is not None
        assert event.actor_id is None
        assert event.details["email"] == "missing@test.ru"


def test_passwords_longer_than_bcrypt_limit_are_rejected(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "long-password@test.ru",
            "password": "я" * 37,
            "client_name": "Орг",
        },
    )

    assert response.status_code == 422


def test_me_requires_auth(client: TestClient):
    assert client.get("/api/auth/me").status_code == 401


def test_health(client: TestClient):
    assert client.get("/api/health").json()["status"] == "ok"
