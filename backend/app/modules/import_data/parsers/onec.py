"""Парсер выгрузки 1С.

На этапе 1 поддерживаем самый частый формат — CSV-выгрузка 1С с разделителем «;»
в кодировке Windows-1251 или UTF-8. Полноценный обмен через XML/EnterpriseData —
задача этапа 2 (см. дорожную карту).
"""

from __future__ import annotations

from app.modules.import_data.parsers.csv_parser import parse_csv


def parse_onec(content: bytes) -> list[dict]:
    return parse_csv(content, delimiter=";")
