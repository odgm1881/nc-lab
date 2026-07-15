"""Доменная логика разрешительной документации (РД) — ЧИСТЫЙ Python.

Для легпрома РД обязательна для ввода в оборот. Частая ошибка: пробел или
некорректное заполнение РД блокирует ввод в оборот уже после печати. Поэтому
структуру и полноту РД проверяем заранее, на этапе описания карточки.

Данные РД хранятся в JSONB-поле карточки `rd_data` в форме:
{
  "type": "declaration" | "certificate" | "refusal_letter",
  "number": "ЕАЭС N RU Д-...",
  "date": "2026-03-01",
  "valid_until": "2029-03-01"   # необязательно для отказного письма
}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# Типы РД, принимаемые для легпрома.
RD_TYPES = {
    "declaration": "Декларация соответствия",
    "certificate": "Сертификат соответствия",
    "refusal_letter": "Отказное письмо",
}

# У отказного письма нет срока действия — это разъяснение, что товар не подлежит
# обязательной сертификации/декларированию.
TYPES_WITHOUT_EXPIRY = {"refusal_letter"}


@dataclass(frozen=True)
class RdCheck:
    known_type: bool
    missing_fields: list[str] = field(default_factory=list)
    expired: bool = False

    @property
    def complete(self) -> bool:
        return self.known_type and not self.missing_fields and not self.expired


def _is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def check_rd(rd_data: dict | None, today: date | None = None) -> RdCheck:
    """Проверить полноту и структуру сведений о РД.

    Возвращает, известен ли тип, каких обязательных полей не хватает и не истёк ли
    срок действия. Чистая функция: today можно передать для детерминированных тестов.
    """
    today = today or date.today()
    data = rd_data or {}

    rd_type = data.get("type")
    known_type = rd_type in RD_TYPES

    required = ["type", "number", "date"]
    missing = [f for f in required if _is_blank(data.get(f))]

    expired = False
    if known_type and rd_type not in TYPES_WITHOUT_EXPIRY:
        valid_until = data.get("valid_until")
        if _is_blank(valid_until):
            missing.append("valid_until")
        else:
            parsed = _parse_date(valid_until)
            if parsed is not None and parsed < today:
                expired = True

    return RdCheck(known_type=known_type, missing_fields=missing, expired=expired)


def _parse_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None
