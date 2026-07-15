"""Сценарии модуля GTIN."""

from app.modules.gtin.domain import check_gtin
from app.modules.gtin.schemas import GtinCheckIn, GtinCheckOut


def check(data: GtinCheckIn) -> GtinCheckOut:
    result = check_gtin(data.gtin)
    if result.valid:
        message = "GTIN корректен."
    elif not result.is_digits:
        message = "GTIN должен состоять только из цифр."
    elif not result.length_ok:
        message = "Недопустимая длина GTIN (ожидается 8, 12, 13 или 14 цифр)."
    else:
        message = "Неверная контрольная цифра GTIN."
    return GtinCheckOut(
        gtin=result.gtin,
        valid=result.valid,
        is_digits=result.is_digits,
        length_ok=result.length_ok,
        check_digit_ok=result.check_digit_ok,
        message=message,
    )
