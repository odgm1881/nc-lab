"""Pydantic-схемы модуля РД."""

from pydantic import BaseModel


class RdData(BaseModel):
    type: str | None = None
    number: str | None = None
    date: str | None = None
    valid_until: str | None = None


class RdCheckOut(BaseModel):
    complete: bool
    known_type: bool
    missing_fields: list[str]
    expired: bool
