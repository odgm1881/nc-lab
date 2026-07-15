"""Реестр активных правил валидации — единая точка, где видно все проверки.

При изменении требований НК правим или добавляем одну функцию правила и её тест,
а не переписываем приложение.
"""

from __future__ import annotations

from collections.abc import Callable

from app.modules.validation.domain import rules
from app.modules.validation.domain.result import (
    CardView,
    Issue,
    ValidationContext,
    ValidationResult,
)

Rule = Callable[[CardView, ValidationContext], list[Issue]]

# Порядок = порядок вывода замечаний. Сначала структурные, затем доменные.
RULES: list[Rule] = [
    rules.rule_category_known,
    rules.rule_required_attributes,
    rules.rule_no_mixed_variations,
    rules.rule_gtin_format,
    rules.rule_gtin_unique_per_card,
    rules.rule_rd_present_and_structured,
]


def run_validation(card: CardView, context: ValidationContext | None = None) -> ValidationResult:
    """Прогнать карточку через все активные правила."""
    ctx = context or ValidationContext()
    result = ValidationResult()
    for rule in RULES:
        result.issues.extend(rule(card, ctx))
    return result


def active_rule_names() -> list[str]:
    return [r.__name__ for r in RULES]
