"""Парсер CSV. Автоопределение разделителя (запятая или точка с запятой)."""

from __future__ import annotations

import csv
import io


def parse_csv(content: bytes, delimiter: str | None = None) -> list[dict]:
    text = _decode(content)
    if delimiter is None:
        delimiter = _sniff_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    raw_rows: list[dict] = []
    for row in reader:
        if not any((v or "").strip() for v in row.values()):
            continue
        raw_rows.append({(k or "").strip(): v for k, v in row.items()})
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
