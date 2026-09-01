"""Юнит-тесты доменной логики вариаций. Без базы и HTTP."""

import pytest

from app.modules.variations.domain import (
    MAX_VARIATION_COMBINATIONS,
    VariationAxes,
    VariationLimitError,
    build_variations,
    variation_count,
    variation_sku,
)


def test_cartesian_product_count():
    axes = VariationAxes(colors=["чёрный", "белый"], sizes=["S", "M", "L"])
    assert variation_count(axes) == 6
    assert len(build_variations(axes)) == 6


def test_empty_axis_does_not_multiply():
    axes = VariationAxes(colors=["чёрный"], sizes=[], genders=[])
    variations = build_variations(axes)
    assert len(variations) == 1
    assert variations[0].color == "чёрный"
    assert variations[0].size is None


def test_full_four_axes():
    axes = VariationAxes(
        colors=["к", "б"], sizes=["S", "M"], genders=["муж"], completeness=["штука", "комплект"]
    )
    assert variation_count(axes) == 2 * 2 * 1 * 2
    assert len(build_variations(axes)) == 8


def test_duplicates_and_blanks_removed():
    axes = VariationAxes(colors=["чёрный", "чёрный", " ", "белый"], sizes=["M", "M"])
    assert variation_count(axes) == 2 * 1


def test_variation_sku_transliteration():
    axes = VariationAxes(colors=["чёрный"], sizes=["M"])
    v = build_variations(axes)[0]
    sku = variation_sku("TSHIRT-01", v)
    assert sku.startswith("TSHIRT-01-")
    assert " " not in sku
    assert sku.isupper() or "-" in sku


def test_variation_as_attributes_skips_none():
    axes = VariationAxes(colors=["синий"], sizes=["L"])
    attrs = build_variations(axes)[0].as_attributes()
    assert attrs == {"color": "синий", "size": "L"}


def test_cartesian_product_above_limit_is_not_materialized():
    values = [str(index) for index in range(10)]
    axes = VariationAxes(
        colors=values,
        sizes=values,
        genders=values,
        completeness=values,
    )
    assert variation_count(axes) > MAX_VARIATION_COMBINATIONS
    with pytest.raises(VariationLimitError, match="Слишком много комбинаций"):
        build_variations(axes)
