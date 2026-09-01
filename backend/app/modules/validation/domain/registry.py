"""Реестр активных правил валидации — единая точка, где видно все проверки.

При изменении требований НК правим или добавляем одну функцию правила и её тест,
а не переписываем приложение.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from app.modules.validation.domain import rules
from app.modules.validation.domain.result import (
    CardView,
    Issue,
    ValidationContext,
    ValidationResult,
)

Rule = Callable[[CardView, ValidationContext], list[Issue]]

# Версии являются частью воспроизводимого результата валидации. Менять их нужно
# при изменении поведения правила или состава/значений доменных справочников.
RULESET_VERSION = "1.0.0"
REFERENCE_DATA_VERSION = "2026.08"

# Порядок = порядок вывода замечаний. Сначала структурные, затем доменные.
RULES: list[Rule] = [
    rules.rule_category_known,
    rules.rule_required_attributes,
    rules.rule_no_mixed_variations,
    rules.rule_gtin_format,
    rules.rule_gtin_unique_per_card,
    rules.rule_rd_present_and_structured,
]
RULES_BY_NAME: dict[str, Rule] = {rule.__name__: rule for rule in RULES}
MANDATORY_RULE_NAMES = frozenset(
    {
        "rule_category_known",
        "rule_required_attributes",
        "rule_gtin_format",
        "rule_gtin_unique_per_card",
        "rule_rd_present_and_structured",
    }
)


def run_validation(
    card: CardView,
    context: ValidationContext | None = None,
    *,
    rule_names: Iterable[str] | None = None,
) -> ValidationResult:
    """Прогнать карточку через выбранный неизменяемый снимок правил."""
    ctx = context or ValidationContext()
    result = ValidationResult()
    selected = RULES if rule_names is None else [_rule_by_name(name) for name in rule_names]
    for rule in selected:
        result.issues.extend(rule(card, ctx))
    return result


def active_rule_names() -> list[str]:
    return [r.__name__ for r in RULES]


def _rule_by_name(name: str) -> Rule:
    try:
        return RULES_BY_NAME[name]
    except KeyError as exc:
        raise ValueError(f"Неизвестное исполняемое правило: {name}") from exc
