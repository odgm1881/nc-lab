"""Правила валидации карточки — чистые функции card -> list[Issue].

Каждое правило: получает CardView и ValidationContext, возвращает список замечаний.
Никакого движка правил или DSL — обычные функции читаются и отлаживаются проще.

Правила зависят только от других доменных модулей (gtin, rd), но НЕ от FastAPI и
SQLAlchemy. Добавление правила — см. навык add-validation-rule.
"""

from __future__ import annotations

from app.modules.gtin.domain import check_gtin, normalize_gtin
from app.modules.rd.domain import RD_TYPES, check_rd
from app.modules.validation.domain.ontology import (
    attribute_label,
    get_category,
    required_attributes,
)
from app.modules.validation.domain.result import (
    CardView,
    Issue,
    Severity,
    ValidationContext,
)


def _is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def rule_category_known(card: CardView, ctx: ValidationContext) -> list[Issue]:
    """Категория должна быть в словаре. Иначе — предупреждение (проверяем базовый набор)."""
    if _is_blank(card.category_code):
        return [
            Issue(
                code="CATEGORY_MISSING",
                severity=Severity.ERROR,
                message="Не указана категория товара (код ТН ВЭД).",
                field="category_code",
            )
        ]
    if get_category(card.category_code) is None:
        return [
            Issue(
                code="CATEGORY_UNKNOWN",
                severity=Severity.WARNING,
                message=(
                    f"Категория {card.category_code} не в словаре — проверяем базовый "
                    "набор атрибутов одежды."
                ),
                field="category_code",
            )
        ]
    return []


def rule_required_attributes(card: CardView, ctx: ValidationContext) -> list[Issue]:
    """Обязательные атрибуты категории должны быть заполнены."""
    issues: list[Issue] = []
    for attr in required_attributes(card.category_code):
        if _is_blank(card.attributes.get(attr)):
            issues.append(
                Issue(
                    code="ATTR_MISSING",
                    severity=Severity.ERROR,
                    message=f"Не заполнен обязательный атрибут: {attribute_label(attr)}.",
                    field=attr,
                )
            )
    return issues


def rule_no_mixed_variations(card: CardView, ctx: ValidationContext) -> list[Issue]:
    """Цвет и размер — отдельные вариации, не смешиваются в одной карточке.

    Если в атрибуте цвета или размера пришёл список/несколько значений — это
    смешение вариаций, что нарушает правило легпрома «1 GTIN = 1 карточка».
    """
    issues: list[Issue] = []
    for attr in ("color", "size"):
        value = card.attributes.get(attr)
        mixed = isinstance(value, (list, tuple, set)) and len(value) > 1
        if not mixed and isinstance(value, str):
            # Разделители, намекающие на несколько значений в одной строке.
            mixed = any(sep in value for sep in (",", ";", "/")) and len(value.strip()) > 1
        if mixed:
            issues.append(
                Issue(
                    code="VARIATION_MIXED",
                    severity=Severity.ERROR,
                    message=(
                        f"В одной карточке смешаны несколько значений «{attribute_label(attr)}». "
                        "Цвет и размер — отдельные вариации и отдельные карточки."
                    ),
                    field=attr,
                )
            )
    return issues


def rule_gtin_format(card: CardView, ctx: ValidationContext) -> list[Issue]:
    """GTIN обязателен и должен иметь корректный формат и контрольную цифру."""
    if _is_blank(card.gtin):
        return [
            Issue(
                code="GTIN_MISSING",
                severity=Severity.ERROR,
                message="Не указан GTIN. Каждая вариация требует свой GTIN.",
                field="gtin",
            )
        ]
    result = check_gtin(card.gtin)
    if not result.valid:
        if not result.length_ok:
            msg = "Недопустимая длина GTIN (ожидается 8, 12, 13 или 14 цифр)."
        elif not result.is_digits:
            msg = "GTIN должен состоять только из цифр."
        else:
            msg = "Неверная контрольная цифра GTIN."
        return [Issue(code="GTIN_INVALID", severity=Severity.ERROR, message=msg, field="gtin")]
    return []


def rule_gtin_unique_per_card(card: CardView, ctx: ValidationContext) -> list[Issue]:
    """1 GTIN = 1 карточка. GTIN не должен принадлежать другой карточке."""
    if _is_blank(card.gtin):
        return []
    key = normalize_gtin(card.gtin)
    owner = ctx.gtin_index.get(key)
    if owner is not None and owner != card.id:
        return [
            Issue(
                code="GTIN_NOT_UNIQUE",
                severity=Severity.ERROR,
                message="GTIN уже привязан к другой карточке. Один GTIN = одна карточка.",
                field="gtin",
            )
        ]
    return []


def rule_rd_present_and_structured(card: CardView, ctx: ValidationContext) -> list[Issue]:
    """РД обязательна для легпрома: тип, номер, дата, срок действия."""
    if not card.rd_data:
        return [
            Issue(
                code="RD_MISSING",
                severity=Severity.ERROR,
                message="Не заполнены сведения о разрешительной документации (РД).",
                field="rd_data",
            )
        ]
    result = check_rd(card.rd_data)
    issues: list[Issue] = []
    if not result.known_type:
        allowed = ", ".join(RD_TYPES.values())
        issues.append(
            Issue(
                code="RD_TYPE_UNKNOWN",
                severity=Severity.ERROR,
                message=f"Неизвестный тип РД. Допустимо: {allowed}.",
                field="rd_data.type",
            )
        )
    for missing in result.missing_fields:
        if missing == "type":
            continue  # уже покрыто RD_TYPE_UNKNOWN
        issues.append(
            Issue(
                code="RD_FIELD_MISSING",
                severity=Severity.ERROR,
                message=f"В сведениях РД не заполнено поле «{missing}».",
                field=f"rd_data.{missing}",
            )
        )
    if result.expired:
        issues.append(
            Issue(
                code="RD_EXPIRED",
                severity=Severity.ERROR,
                message="Срок действия РД истёк.",
                field="rd_data.valid_until",
            )
        )
    return issues
