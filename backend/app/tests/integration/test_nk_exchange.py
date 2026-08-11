from fastapi.testclient import TestClient

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

    download = auth_client.get(
        f"/api/integration/nk/exchanges/{first.json()['id']}/payload"
    )
    assert download.status_code == 200
    assert download.json()["schema_version"] == "nklab-nk-file-1"
    assert download.json()["gtin"] == VALID_CARD["gtin"]


def test_exchange_rejects_unready_card(auth_client: TestClient) -> None:
    card_id = auth_client.post("/api/cards", json=VALID_CARD).json()["id"]
    response = auth_client.post(
        "/api/integration/nk/exchanges", json={"card_id": card_id, "mode": "mock"}
    )
    assert response.status_code == 400


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
