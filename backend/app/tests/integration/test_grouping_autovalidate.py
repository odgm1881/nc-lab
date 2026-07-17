"""Интеграционные тесты: автовалидация при импорте и группировка по моделям."""

import io

from fastapi.testclient import TestClient
from openpyxl import Workbook


def _xlsx(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(
        ["Наименование", "Артикул", "Категория", "GTIN", "Вид изделия", "Цвет", "Размер", "Пол",
         "Состав", "Возрастная группа", "Тип РД", "Номер РД", "Дата РД", "Срок действия"]
    )
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# Две разные модели в одном файле: Футболка (валидная) и Свитер (без GTIN → ошибка).
FILE = _xlsx(
    [
        ["Футболка PRO", "TSH-1", "6109", "4600000000015", "футболка", "чёрный", "M", "мужской",
         "хлопок 100%", "взрослая", "декларация", "Д-1", "2026-02-01", "2029-02-01"],
        ["Свитер PRO", "SWT-1", "6110", "", "джемпер", "серый", "L", "женский",
         "шерсть", "взрослая", "декларация", "Д-2", "2026-02-01", "2029-02-01"],
    ]
)


def test_import_auto_validates(auth_client: TestClient):
    r = auth_client.post("/api/import/commit", files={"file": ("n.xlsx", FILE)})
    assert r.status_code == 201, r.text
    # Без ручного клика «Валидировать» статусы уже проставлены.
    valid = auth_client.get("/api/cards", params={"status": "valid"}).json()
    error = auth_client.get("/api/cards", params={"status": "error"}).json()
    assert valid["total"] == 1  # Футболка PRO — валидна сразу
    assert error["total"] == 1  # Свитер PRO — ошибка (нет GTIN)
    # Черновиков после импорта не осталось.
    draft = auth_client.get("/api/cards", params={"status": "draft"}).json()
    assert draft["total"] == 0


def test_models_grouping(auth_client: TestClient):
    auth_client.post("/api/import/commit", files={"file": ("n.xlsx", FILE)})
    models = auth_client.get("/api/cards/models").json()["items"]
    names = {m["name"]: m for m in models}
    # Две разные модели — не смешаны в один список.
    assert "Футболка PRO" in names
    assert "Свитер PRO" in names
    assert names["Футболка PRO"]["total"] == 1
    assert names["Футболка PRO"]["counts"].get("valid") == 1
    assert names["Свитер PRO"]["counts"].get("error") == 1


def test_filter_cards_by_model(auth_client: TestClient):
    auth_client.post("/api/import/commit", files={"file": ("n.xlsx", FILE)})
    r = auth_client.get("/api/cards", params={"name": "Свитер PRO"}).json()
    assert r["total"] == 1
    assert r["items"][0]["name"] == "Свитер PRO"


def test_validate_all(auth_client: TestClient):
    # Создаём карточку вручную (остаётся черновиком), затем массово валидируем.
    auth_client.post(
        "/api/cards",
        json={
            "name": "Ручная", "vendor_code": "M-1", "category_code": "6109",
            "gtin": "4600000000015",
            "attributes": {"item_type": "футболка", "composition": "хлопок", "size": "M",
                           "color": "чёрный", "gender": "мужской", "age_group": "взрослая"},
            "rd_data": {"type": "declaration", "number": "Д", "date": "2026-01-01",
                        "valid_until": "2029-01-01"},
        },
    )
    assert auth_client.get("/api/cards", params={"status": "draft"}).json()["total"] == 1
    r = auth_client.post("/api/cards/validate-all").json()
    assert r["validated"] >= 1
    assert r["valid"] == 1
    assert auth_client.get("/api/cards", params={"status": "draft"}).json()["total"] == 0
