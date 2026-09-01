"""Сценарии модуля вариаций. Оркестрация над чистым доменом."""

from app.core.exceptions import DomainError
from app.modules.variations.domain import (
    VariationAxes,
    VariationLimitError,
    build_variations,
    variation_count,
    variation_sku,
)
from app.modules.variations.schemas import (
    VariationAxesIn,
    VariationOut,
    VariationPreviewOut,
)


def preview_variations(data: VariationAxesIn) -> VariationPreviewOut:
    axes = VariationAxes(
        colors=data.colors,
        sizes=data.sizes,
        genders=data.genders,
        completeness=data.completeness,
    )
    try:
        variations = build_variations(axes)
    except VariationLimitError as exc:
        raise DomainError(str(exc), code="VARIATION_LIMIT_EXCEEDED") from exc
    out = [
        VariationOut(
            sku=variation_sku(data.base_vendor_code, v),
            color=v.color,
            size=v.size,
            gender=v.gender,
            completeness=v.completeness,
        )
        for v in variations
    ]
    return VariationPreviewOut(count=variation_count(axes), variations=out)
