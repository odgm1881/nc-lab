"""API-слой модуля РД. Только HTTP."""

from fastapi import APIRouter, Depends

from app.modules.auth.dependencies import get_current_user
from app.modules.rd import service
from app.modules.rd.schemas import RdCheckOut, RdData

router = APIRouter()


@router.post("/check", response_model=RdCheckOut)
def check(data: RdData, _=Depends(get_current_user)) -> RdCheckOut:
    """Проверить полноту и структуру сведений о разрешительной документации."""
    return service.check(data)
