"""Юнит-тесты нормализации импорта: маппинг заголовков и парсер CSV."""

from app.modules.import_data.parsers.base import SOURCE_ROW_NUMBER, map_row, map_rows
from app.modules.import_data.parsers.csv_parser import parse_csv


def test_map_row_russian_headers():
    raw = {
        "Наименование": "Футболка",
        "Артикул": "TS-1",
        "Категория": "6109",
        "GTIN": "4600000000015",
        "Цвет": "чёрный",
        "Размер": "M",
        "Пол": "мужской",
        "Состав": "хлопок 100%",
        "Тип РД": "декларация",
        "Номер РД": "Д-123",
        "Дата РД": "2026-02-01",
    }
    row = map_row(raw)
    assert row.name == "Футболка"
    assert row.vendor_code == "TS-1"
    assert row.category_code == "6109"
    assert row.gtin == "4600000000015"
    assert row.attributes["color"] == "чёрный"
    assert row.attributes["composition"] == "хлопок 100%"
    assert row.rd_data["type"] == "declaration"
    assert row.rd_data["number"] == "Д-123"


def test_map_rows_skips_empty():
    rows = map_rows([{"Наименование": ""}, {"Артикул": "A1"}])
    assert len(rows) == 1
    assert rows[0].vendor_code == "A1"


def test_parse_csv_semicolon():
    content = "Наименование;Артикул;Цвет\nФутболка;TS-1;чёрный\n".encode()
    raw = parse_csv(content)
    assert len(raw) == 1
    assert raw[0]["Наименование"] == "Футболка"


def test_parse_csv_comma():
    content = b"name,vendor_code\nJumper,JMP-1\n"
    raw = parse_csv(content)
    assert raw[0]["vendor_code"] == "JMP-1"


def test_parse_csv_ignores_extra_values_and_empty_malformed_rows():
    content = (
        "Наименование;Артикул;GTIN\n"
        "\n"
        "Футболка;A1;;лишняя колонка\n"
        ";;;только лишняя колонка\n"
    ).encode()

    raw = parse_csv(content)

    assert len(raw) == 1
    assert raw[0]["Наименование"] == "Футболка"
    assert raw[0]["Артикул"] == "A1"
    assert raw[0][SOURCE_ROW_NUMBER] == 3
