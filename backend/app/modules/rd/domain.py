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
    invalid_date_fields: list[str] = field(default_factory=list)
    invalid_date_range: bool = False
    expired: bool = False

    @property
    def complete(self) -> bool:
        return (
            self.known_type
            and not self.missing_fields
            and not self.invalid_date_fields
            and not self.invalid_date_range
            and not self.expired
        )


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

    invalid_date_fields: list[str] = []
    issue_date = None
    if not _is_blank(data.get("date")):
        issue_date = _parse_date(data.get("date"))
        if issue_date is None:
            invalid_date_fields.append("date")

    expired = False
    valid_until_date = None
    if known_type and rd_type not in TYPES_WITHOUT_EXPIRY:
        valid_until = data.get("valid_until")
        if _is_blank(valid_until):
            missing.append("valid_until")
        else:
            valid_until_date = _parse_date(valid_until)
            if valid_until_date is None:
                invalid_date_fields.append("valid_until")
            elif valid_until_date < today:
                expired = True

    invalid_date_range = bool(
        issue_date is not None
        and valid_until_date is not None
        and issue_date > valid_until_date
    )
    return RdCheck(
        known_type=known_type,
        missing_fields=missing,
        invalid_date_fields=invalid_date_fields,
        invalid_date_range=invalid_date_range,
        expired=expired,
    )


def _parse_date(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None
