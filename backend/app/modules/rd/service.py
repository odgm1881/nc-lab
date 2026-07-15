"""Сценарии модуля РД."""

from app.modules.rd.domain import check_rd
from app.modules.rd.schemas import RdCheckOut, RdData


def check(data: RdData) -> RdCheckOut:
    result = check_rd(data.model_dump())
    return RdCheckOut(
        complete=result.complete,
        known_type=result.known_type,
        missing_fields=result.missing_fields,
        expired=result.expired,
    )
