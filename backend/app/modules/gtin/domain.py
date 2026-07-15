"""Доменная логика GTIN — ЧИСТЫЙ Python.

Здесь живёт правило легпрома «1 GTIN = 1 карточка» (проверка уникальности — на
уровне карточек и БД) и проверка формата номера: длина и контрольная цифра GS1.

Ошибка в GTIN необратима, поэтому проверяем формат до заказа кодов.
"""

from __future__ import annotations

from dataclasses import dataclass

# GS1 допускает GTIN-8, GTIN-12 (UPC-A), GTIN-13 (EAN-13), GTIN-14.
VALID_LENGTHS = {8, 12, 13, 14}


@dataclass(frozen=True)
class GtinCheck:
    gtin: str
    is_digits: bool
    length_ok: bool
    check_digit_ok: bool

    @property
    def valid(self) -> bool:
        return self.is_digits and self.length_ok and self.check_digit_ok


def normalize_gtin(raw: str | None) -> str:
    """Убрать пробелы и незначащие символы. Сохраняем ведущие нули."""
    if not raw:
        return ""
    return "".join(ch for ch in str(raw).strip() if ch.isdigit())


def compute_check_digit(body: str) -> int | None:
    """Контрольная цифра GS1 (mod-10) по телу номера без последней цифры.

    Веса чередуются 3,1,3,1... справа налево. Возвращает 0..9 или None,
    если тело не числовое.
    """
    if not body or not body.isdigit():
        return None
    total = 0
    # справа налево, самый правый разряд тела имеет вес 3
    for i, ch in enumerate(reversed(body)):
        weight = 3 if i % 2 == 0 else 1
        total += int(ch) * weight
    return (10 - (total % 10)) % 10


def check_gtin(raw: str | None) -> GtinCheck:
    """Полная проверка формата GTIN."""
    gtin = normalize_gtin(raw)
    is_digits = gtin.isdigit() and len(gtin) > 0
    length_ok = len(gtin) in VALID_LENGTHS
    check_digit_ok = False
    if is_digits and length_ok:
        expected = compute_check_digit(gtin[:-1])
        check_digit_ok = expected is not None and expected == int(gtin[-1])
    return GtinCheck(
        gtin=gtin,
        is_digits=is_digits,
        length_ok=length_ok,
        check_digit_ok=check_digit_ok,
    )


def is_valid_gtin(raw: str | None) -> bool:
    return check_gtin(raw).valid
