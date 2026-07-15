"""Сценарии модуля вариаций. Оркестрация над чистым доменом."""

from app.modules.variations.domain import (
    VariationAxes,
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
    variations = build_variations(axes)
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
