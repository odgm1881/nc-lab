"""API-слой модуля валидации. Только HTTP."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.validation import service
from app.modules.validation.schemas import (
    CardValidationIn,
    RulesOut,
    ValidationResultOut,
)

router = APIRouter()


@router.post("/check", response_model=ValidationResultOut)
def check(
    data: CardValidationIn,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> ValidationResultOut:
    """Разовая проверка карточки-черновика без сохранения."""
    return service.validate_payload(db, data)


@router.get("/rules", response_model=RulesOut)
def rules(_=Depends(get_current_user)) -> RulesOut:
    """Список активных правил валидации."""
    return service.list_rules()
