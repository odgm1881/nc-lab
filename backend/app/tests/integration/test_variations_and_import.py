"""Интеграционные тесты вариаций, построения карточек и импорта."""

import io

from fastapi.testclient import TestClient
from openpyxl import Workbook


def test_variation_preview(auth_client: TestClient):
    r = auth_client.post(
        "/api/variations/preview",
        json={"base_vendor_code": "TS", "colors": ["чёрный", "белый"], "sizes": ["S", "M", "L"]},
    )
    assert r.status_code == 200
    assert r.json()["count"] == 6
    assert len(r.json()["variations"]) == 6


def test_build_from_variations_creates_cards(auth_client: TestClient):
    r = auth_client.post(
        "/api/cards/build-from-variations",
        json={
            "name": "Футболка",
            "base_vendor_code": "TS",
            "category_code": "6109",
            "common_attributes": {"item_type": "футболка", "composition": "хлопок"},
            "colors": ["чёрный", "белый"],
            "sizes": ["S", "M"],
        },
    )
    assert r.status_code == 201
    assert r.json()["created"] == 4
    # Каждая вариация — отдельная карточка (правило легпрома).
    assert auth_client.get("/api/cards").json()["total"] == 4


def test_variation_preview_rejects_oversized_cartesian_product(auth_client: TestClient):
    values = [str(index) for index in range(10)]
    response = auth_client.post(
        "/api/variations/preview",
        json={
            "colors": values,
            "sizes": values,
            "genders": values,
            "completeness": values,
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VARIATION_LIMIT_EXCEEDED"


def _xlsx_bytes() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(
        [
            "Наименование",
            "Артикул",
            "Категория",
            "GTIN",
            "Цвет",
            "Размер",
            "Пол",
            "Состав",
            "Возрастная группа",
            "Тип РД",
            "Номер РД",
            "Дата РД",
            "Срок действия",
        ]
    )
    ws.append(
        [
            "Футболка",
            "TS-1",
            "6109",
            "4600000000015",
            "чёрный",
            "M",
            "мужской",
            "хлопок 100%",
            "взрослая",
            "декларация",
            "Д-1",
            "2026-02-01",
            "2029-02-01",
        ]
    )
    ws.append(
        [
            "Футболка",
            "TS-2",
            "6109",
            "",
            "белый",
            "L",
            "мужской",
            "хлопок 100%",
            "взрослая",
            "декларация",
            "Д-1",
            "2026-02-01",
            "2029-02-01",
        ]
    )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_import_preview(auth_client: TestClient):
    files = {"file": ("nomenclature.xlsx", _xlsx_bytes())}
    r = auth_client.post("/api/import/preview", files=files)
    assert r.status_code == 200, r.text
    assert r.json()["source"] == "excel"
    assert r.json()["rows_total"] == 2
    assert r.json()["rows"][0]["attributes"]["color"] == "чёрный"


def test_import_preview_rejects_broken_excel_without_server_error(auth_client: TestClient):
    response = auth_client.post(
        "/api/import/preview",
        files={"file": ("broken.xlsx", b"not-an-excel-file")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IMPORT_PARSE_ERROR"


def test_import_commit_creates_cards(auth_client: TestClient):
    files = {"file": ("nomenclature.xlsx", _xlsx_bytes())}
    r = auth_client.post("/api/import/commit", files=files, data={"create_cards": "true"})
    assert r.status_code == 201, r.text
    assert r.json()["cards_created"] == 2
    assert auth_client.get("/api/cards").json()["total"] == 2
    # Задание импорта зафиксировано.
    jobs = auth_client.get("/api/import/jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["status"] == "done"
