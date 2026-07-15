"""Pydantic-схемы модуля GTIN."""

from pydantic import BaseModel


class GtinCheckIn(BaseModel):
    gtin: str


class GtinCheckOut(BaseModel):
    gtin: str
    valid: bool
    is_digits: bool
    length_ok: bool
    check_digit_ok: bool
    message: str
