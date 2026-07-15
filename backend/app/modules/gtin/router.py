"""API-слой модуля GTIN. Только HTTP."""

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_user
from app.modules.gtin import service
from app.modules.gtin.schemas import GtinCheckIn, GtinCheckOut

router = APIRouter()


@router.post("/check", response_model=GtinCheckOut)
def check(data: GtinCheckIn, _=Depends(get_current_user)) -> GtinCheckOut:
    """Проверить формат и контрольную цифру GTIN."""
    return service.check(data)
