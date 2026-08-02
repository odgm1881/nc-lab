"""Интеграционные тесты: создание → валидация → готовность к публикации."""

from fastapi.testclient import TestClient

VALID_CARD = {
    "name": "Джемпер",
    "vendor_code": "JMP-1",
    "category_code": "6110",
    "gtin": "4600000000015",
    "attributes": {
        "item_type": "джемпер",
        "composition": "шерсть 80%",
        "size": "M",
        "color": "серый",
        "gender": "женский",
        "age_group": "взрослая",
    },
    "rd_data": {
        "type": "certificate",
        "number": "С-123",
        "date": "2026-01-15",
        "valid_until": "2028-01-15",
    },
}


def test_create_validate_publish(auth_client: TestClient):
    r = auth_client.post("/api/cards", json=VALID_CARD)
    assert r.status_code == 201, r.text
    card = r.json()
    assert card["status"] == "draft"
    card_id = card["id"]

    r = auth_client.post(f"/api/cards/{card_id}/validate")
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["is_valid"] is True
    assert body["card"]["status"] == "valid"

    r = auth_client.post(f"/api/cards/{card_id}/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "published"


def test_publish_requires_valid(auth_client: TestClient):
    broken = dict(VALID_CARD, gtin="123", rd_data={})
    card_id = auth_client.post("/api/cards", json=broken).json()["id"]
    auth_client.post(f"/api/cards/{card_id}/validate")
    r = auth_client.post(f"/api/cards/{card_id}/ready")
    assert r.status_code == 400


def test_validation_reports_errors(auth_client: TestClient):
    broken = dict(VALID_CARD, gtin=None, attributes={"item_type": "джемпер"}, rd_data={})
    card_id = auth_client.post("/api/cards", json=broken).json()["id"]
    r = auth_client.post(f"/api/cards/{card_id}/validate")
    result = r.json()["result"]
    assert result["is_valid"] is False
    codes = {i["code"] for i in result["errors"]}
    assert "GTIN_MISSING" in codes
    assert "RD_MISSING" in codes
    assert "ATTR_MISSING" in codes


def test_duplicate_gtin_conflict(auth_client: TestClient):
    auth_client.post("/api/cards", json=VALID_CARD)
    r = auth_client.post("/api/cards", json=dict(VALID_CARD, vendor_code="JMP-2"))
    assert r.status_code == 409


def test_list_and_filter(auth_client: TestClient):
    auth_client.post("/api/cards", json=VALID_CARD)
    r = auth_client.get("/api/cards")
    assert r.json()["total"] == 1
    r = auth_client.get("/api/cards", params={"search": "JMP"})
    assert r.json()["total"] == 1
    r = auth_client.get("/api/cards", params={"status": "published"})
    assert r.json()["total"] == 0


def test_list_rejects_negative_pagination(auth_client: TestClient):
    assert auth_client.get("/api/cards", params={"limit": -1}).status_code == 422
    assert auth_client.get("/api/cards", params={"offset": -1}).status_code == 422


def test_update_resets_to_draft(auth_client: TestClient):
    card_id = auth_client.post("/api/cards", json=VALID_CARD).json()["id"]
    auth_client.post(f"/api/cards/{card_id}/validate")
    r = auth_client.patch(f"/api/cards/{card_id}", json={"name": "Новое имя"})
    assert r.json()["status"] == "draft"
    assert r.json()["name"] == "Новое имя"
