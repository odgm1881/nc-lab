from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DomainError, NotFoundError
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditEvent
from app.modules.audit.schemas import AuditEventOut
from app.modules.auth.models import User
from app.modules.validation.domain.registry import (
    MANDATORY_RULE_NAMES,
    RULESET_VERSION,
    active_rule_names,
)
from app.modules.validation_rulesets.models import (
    STATUS_APPROVED,
    STATUS_DRAFT,
    STATUS_RETIRED,
    ValidationRuleSet,
)
from app.modules.validation_rulesets.schemas import (
    RuleSetCreateIn,
    RuleSetListOut,
    RuleSetOut,
)


@dataclass(frozen=True)
class ResolvedRuleSet:
    version: str
    rule_names: tuple[str, ...]


def _require(db: Session, ruleset_id: str) -> ValidationRuleSet:
    item = db.get(ValidationRuleSet, ruleset_id)
    if item is None:
        raise NotFoundError("Версия правил не найдена.")
    return item


def list_rulesets(db: Session) -> RuleSetListOut:
    items = list(
        db.scalars(
            select(ValidationRuleSet).order_by(
                ValidationRuleSet.effective_from.desc(),
                ValidationRuleSet.created_at.desc(),
            )
        )
    )
    return RuleSetListOut(
        items=[RuleSetOut.model_validate(item) for item in items],
        total=len(items),
    )


def create_ruleset(db: Session, data: RuleSetCreateIn, actor: User) -> RuleSetOut:
    if db.scalar(select(ValidationRuleSet.id).where(ValidationRuleSet.version == data.version)):
        raise ConflictError("Версия с таким номером уже существует.")
    rule_names = data.rule_names or active_rule_names()
    unknown_rules = sorted(set(rule_names) - set(active_rule_names()))
    if unknown_rules:
        raise DomainError(f"Неизвестные правила: {', '.join(unknown_rules)}")
    missing_mandatory = sorted(MANDATORY_RULE_NAMES - set(rule_names))
    if missing_mandatory:
        raise DomainError(
            "Нельзя отключить обязательные правила: " + ", ".join(missing_mandatory)
        )
    item = ValidationRuleSet(
        version=data.version,
        title=data.title.strip(),
        category_codes=data.category_codes,
        rule_names=rule_names,
        source_reference=data.source_reference.strip(),
        change_summary=data.change_summary.strip(),
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        created_by=actor.id,
    )
    db.add(item)
    db.flush()
    audit_service.record(
        db,
        client_id=actor.client_id,
        actor_id=actor.id,
        action="validation_ruleset.created",
        entity_type="validation_ruleset",
        entity_id=item.id,
        after=audit_service.snapshot(item),
    )
    db.commit()
    db.refresh(item)
    return RuleSetOut.model_validate(item)


def approve_ruleset(
    db: Session,
    ruleset_id: str,
    actor: User,
    expert_name: str | None = None,
) -> RuleSetOut:
    item = _require(db, ruleset_id)
    if item.status != STATUS_DRAFT:
        raise ConflictError("Утвердить можно только черновик версии правил.")
    if not item.source_reference.strip() or item.effective_from is None:
        raise DomainError("Для утверждения укажите источник и дату начала действия.")
    before = audit_service.snapshot(item)
    item.status = STATUS_APPROVED
    item.approved_by = actor.id
    item.approved_by_name = (expert_name or actor.full_name or actor.email).strip()
    item.approved_at = datetime.now(UTC)
    audit_service.record(
        db,
        client_id=actor.client_id,
        actor_id=actor.id,
        action="validation_ruleset.approved",
        entity_type="validation_ruleset",
        entity_id=item.id,
        before=before,
        after=audit_service.snapshot(item),
    )
    db.commit()
    db.refresh(item)
    return RuleSetOut.model_validate(item)


def retire_ruleset(db: Session, ruleset_id: str, actor: User) -> RuleSetOut:
    item = _require(db, ruleset_id)
    if item.status != STATUS_APPROVED:
        raise ConflictError("Архивировать можно только утверждённую версию.")
    before = audit_service.snapshot(item)
    item.status = STATUS_RETIRED
    audit_service.record(
        db,
        client_id=actor.client_id,
        actor_id=actor.id,
        action="validation_ruleset.retired",
        entity_type="validation_ruleset",
        entity_id=item.id,
        before=before,
        after=audit_service.snapshot(item),
    )
    db.commit()
    db.refresh(item)
    return RuleSetOut.model_validate(item)


def history(db: Session, ruleset_id: str) -> list[AuditEventOut]:
    _require(db, ruleset_id)
    events = list(
        db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.entity_type == "validation_ruleset",
                AuditEvent.entity_id == ruleset_id,
            )
            .order_by(AuditEvent.created_at.desc())
        )
    )
    return [AuditEventOut.model_validate(event) for event in events]


def resolve_ruleset(
    db: Session,
    category_code: str | None,
    on_date: date | None = None,
) -> ResolvedRuleSet:
    target_date = on_date or date.today()
    candidates = list(
        db.scalars(
            select(ValidationRuleSet)
            .where(
                ValidationRuleSet.status == STATUS_APPROVED,
                ValidationRuleSet.effective_from <= target_date,
            )
            .order_by(
                ValidationRuleSet.effective_from.desc(),
                ValidationRuleSet.approved_at.desc(),
            )
        )
    )
    for item in candidates:
        if item.effective_to and item.effective_to < target_date:
            continue
        categories = set(item.category_codes or [])
        if not categories or (category_code and category_code in categories):
            return ResolvedRuleSet(
                version=item.version,
                rule_names=tuple(item.rule_names or active_rule_names()),
            )
    return ResolvedRuleSet(
        version=RULESET_VERSION,
        rule_names=tuple(active_rule_names()),
    )


def resolve_version(
    db: Session,
    category_code: str | None,
    on_date: date | None = None,
) -> str:
    """Совместимый помощник для мест, которым нужна только метка версии."""
    return resolve_ruleset(db, category_code, on_date).version
