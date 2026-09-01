from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.modules.catalog.models import STATUS_ERROR, Card
from app.tests.integration.test_cards_flow import VALID_CARD


def _ready_card(client: TestClient) -> str:
    card_id = client.post("/api/cards", json=VALID_CARD).json()["id"]
    client.post(f"/api/cards/{card_id}/validate")
    client.post(f"/api/cards/{card_id}/ready")
    return card_id


def test_file_exchange_is_idempotent_and_downloadable(auth_client: TestClient) -> None:
    card_id = _ready_card(auth_client)
    payload = {"card_id": card_id, "mode": "file", "idempotency_key": "pilot-key-001"}

    first = auth_client.post("/api/integration/nk/exchanges", json=payload)
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "prepared"
    assert first.json()["attempts"] == 1

    repeated = auth_client.post("/api/integration/nk/exchanges", json=payload)
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]
    assert repeated.json()["attempts"] == 1

    download = auth_client.get(f"/api/integration/nk/exchanges/{first.json()['id']}/payload")
    assert download.status_code == 200
    assert download.json()["schema_version"] == "nklab-nk-file-2"
    assert download.json()["gtin"] == VALID_CARD["gtin"]
    assert first.json()["correlation_id"]
    assert first.json()["last_attempt_at"]
    assert len(first.json()["request_fingerprint"]) == 64
    assert first.json()["reconciliation_status"] == "not_checked"

    automatic = auth_client.post(
        "/api/integration/nk/exchanges",
        json={"card_id": card_id, "mode": "file"},
    )
    repeated_automatic = auth_client.post(
        "/api/integration/nk/exchanges",
        json={"card_id": card_id, "mode": "file"},
    )
    assert automatic.json()["id"] == repeated_automatic.json()["id"]

    reconciled = auth_client.post(
        f"/api/integration/nk/exchanges/{first.json()['id']}/reconcile"
    )
    assert reconciled.status_code == 200
    assert reconciled.json()["reconciliation_status"] == "in_sync"


def test_exchange_rejects_unready_card(auth_client: TestClient) -> None:
    card_id = auth_client.post("/api/cards", json=VALID_CARD).json()["id"]
    response = auth_client.post(
        "/api/integration/nk/exchanges", json={"card_id": card_id, "mode": "mock"}
    )
    assert response.status_code == 400


def test_exchange_revalidates_published_card(auth_client: TestClient) -> None:
    card_id = _ready_card(auth_client)
    with SessionLocal() as db:
        card = db.scalar(select(Card).where(Card.id == card_id))
        assert card is not None
        card.rd_data = {**card.rd_data, "valid_until": "2026-08-31"}
        db.commit()

    response = auth_client.post(
        "/api/integration/nk/exchanges",
        json={"card_id": card_id, "mode": "file"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_STALE"
    with SessionLocal() as db:
        card = db.scalar(select(Card).where(Card.id == card_id))
        assert card is not None
        assert card.status == STATUS_ERROR


def test_exchange_detects_changed_payload_and_queue_summary(auth_client: TestClient) -> None:
    card_id = _ready_card(auth_client)
    exchange = auth_client.post(
        "/api/integration/nk/exchanges", json={"card_id": card_id, "mode": "mock"}
    ).json()

    # Готовую карточку напрямую не редактируем; моделируем изменение источника после отправки.
    with SessionLocal() as db:
        card = db.get(Card, card_id)
        assert card is not None
        card.service_comment = "Изменено после отправки"
        card.name = "Обновлённое наименование"
        db.commit()

    reconciled = auth_client.post(
        f"/api/integration/nk/exchanges/{exchange['id']}/reconcile"
    )
    assert reconciled.json()["reconciliation_status"] == "stale_payload"

    summary = auth_client.get("/api/integration/nk/exchanges-queue/summary")
    assert summary.status_code == 200
    assert summary.json()["total"] == 1
    assert summary.json()["stale_payload"] == 1

    filtered = auth_client.get(
        "/api/integration/nk/exchanges",
        params={"reconciliation_status": "stale_payload"},
    )
    assert filtered.json()["total"] == 1


def test_api_exchange_is_disabled_until_credentials_are_configured(
    auth_client: TestClient,
) -> None:
    card_id = _ready_card(auth_client)
    response = auth_client.post(
        "/api/integration/nk/exchanges", json={"card_id": card_id, "mode": "api"}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NK_NOT_CONFIGURED"


def test_integration_status_does_not_expose_secrets(auth_client: TestClient) -> None:
    response = auth_client.get("/api/integration/nk/status")
    assert response.status_code == 200
    assert response.json()["api_enabled"] is False
    assert "token" not in response.text.lower()
    assert "key" not in response.text.lower()


def test_exchange_is_tenant_isolated(client: TestClient, auth_client: TestClient) -> None:
    card_id = _ready_card(auth_client)
    exchange = auth_client.post(
        "/api/integration/nk/exchanges", json={"card_id": card_id, "mode": "mock"}
    ).json()

    client.post(
        "/api/auth/register",
        json={
            "email": "other-exchange@test.ru",
            "password": "password",
            "full_name": "Другой",
            "client_name": "Другой клиент",
        },
    )
    token = client.post(
        "/api/auth/login", json={"email": "other-exchange@test.ru", "password": "password"}
    ).json()["access_token"]
    response = client.get(
        f"/api/integration/nk/exchanges/{exchange['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
