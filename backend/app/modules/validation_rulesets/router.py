from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.audit.schemas import AuditEventOut
from app.modules.auth.dependencies import get_current_user, require_operator
from app.modules.auth.models import User
from app.modules.validation_rulesets import service
from app.modules.validation_rulesets.schemas import (
    RuleSetApproveIn,
    RuleSetCreateIn,
    RuleSetListOut,
    RuleSetOut,
)

router = APIRouter()


@router.get("", response_model=RuleSetListOut)
def list_rulesets(
    db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> RuleSetListOut:
    return service.list_rulesets(db)


@router.post("", response_model=RuleSetOut, status_code=201)
def create_ruleset(
    data: RuleSetCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_operator),
) -> RuleSetOut:
    return service.create_ruleset(db, data, user)


@router.post("/{ruleset_id}/approve", response_model=RuleSetOut)
def approve_ruleset(
    ruleset_id: str,
    data: RuleSetApproveIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_operator),
) -> RuleSetOut:
    return service.approve_ruleset(db, ruleset_id, user, data.expert_name)


@router.post("/{ruleset_id}/retire", response_model=RuleSetOut)
def retire_ruleset(
    ruleset_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_operator),
) -> RuleSetOut:
    return service.retire_ruleset(db, ruleset_id, user)


@router.get("/{ruleset_id}/history", response_model=list[AuditEventOut])
def ruleset_history(
    ruleset_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[AuditEventOut]:
    return service.history(db, ruleset_id)
