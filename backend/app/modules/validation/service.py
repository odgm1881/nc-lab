"""Сценарии модуля валидации.

Здесь — преобразование доменного результата в API-схему и разовая проверка
карточки без сохранения. Валидацию сохранённых карточек оркеструет catalog.service,
используя тот же реестр правил.
"""

from sqlalchemy.orm import Session

from app.modules.validation.domain.registry import (
    REFERENCE_DATA_VERSION,
    RULESET_VERSION,
    active_rule_names,
    run_validation,
)
from app.modules.validation.domain.result import (
    CardView,
    Issue,
    ValidationContext,
    ValidationResult,
)
from app.modules.validation.schemas import (
    CardValidationIn,
    IssueOut,
    RulesOut,
    ValidationResultOut,
)
from app.modules.validation_rulesets.service import resolve_ruleset


def _issue_to_schema(issue: Issue) -> IssueOut:
    return IssueOut(
        code=issue.code,
        severity=issue.severity.value,
        message=issue.message,
        field=issue.field,
    )


def result_to_schema(
    result: ValidationResult,
    ruleset_version: str | None = None,
) -> ValidationResultOut:
    return ValidationResultOut(
        ruleset_version=ruleset_version or RULESET_VERSION,
        reference_data_version=REFERENCE_DATA_VERSION,
        is_valid=result.is_valid,
        errors=[_issue_to_schema(i) for i in result.errors],
        warnings=[_issue_to_schema(i) for i in result.warnings],
        issues=[_issue_to_schema(i) for i in result.issues],
    )


def validate_payload(db: Session, data: CardValidationIn) -> ValidationResultOut:
    """Проверить карточку-черновик без сохранения и без контекста уникальности GTIN."""
    card = CardView(
        category_code=data.category_code,
        gtin=data.gtin,
        attributes=data.attributes or {},
        rd_data=data.rd_data or {},
    )
    ruleset = resolve_ruleset(db, data.category_code)
    result = run_validation(
        card,
        ValidationContext(),
        rule_names=ruleset.rule_names,
    )
    return result_to_schema(result, ruleset.version)


def list_rules() -> RulesOut:
    return RulesOut(rules=active_rule_names())
