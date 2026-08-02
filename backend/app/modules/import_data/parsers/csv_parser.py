"""Парсер CSV. Автоопределение разделителя (запятая или точка с запятой)."""

from __future__ import annotations

import csv
import io

from app.modules.import_data.parsers.base import SOURCE_ROW_NUMBER


def parse_csv(content: bytes, delimiter: str | None = None) -> list[dict]:
    text = _decode(content)
    if delimiter is None:
        delimiter = _sniff_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    raw_rows: list[dict] = []
    for row in reader:
        # DictReader помещает лишние значения строки под ключ ``None`` и
        # возвращает их списком. Такое часто встречается в ручных выгрузках с
        # лишним разделителем и не должно превращать импорт в HTTP 500.
        normalized = {
            str(key).strip(): value
            for key, value in row.items()
            if key is not None
        }
        if not any(str(value or "").strip() for value in normalized.values()):
            continue
        normalized[SOURCE_ROW_NUMBER] = reader.line_num
        raw_rows.append(normalized)
    return raw_rows


def _decode(content: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _sniff_delimiter(text: str) -> str:
    first_line = text.splitlines()[0] if text.splitlines() else ""
    return ";" if first_line.count(";") >= first_line.count(",") else ","
