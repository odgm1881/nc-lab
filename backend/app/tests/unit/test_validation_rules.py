"""Юнит-тесты ядра правил валидации. Чистые функции card -> issues."""

from app.modules.validation.domain.registry import run_validation
from app.modules.validation.domain.result import CardView, ValidationContext


def _good_card(**overrides) -> CardView:
    data = {
        "id": "c1",
        "client_id": "cl1",
        "category_code": "6109",
        "gtin": "4600000000015",
        "attributes": {
            "item_type": "футболка",
            "composition": "хлопок 100%",
            "size": "M",
            "color": "чёрный",
            "gender": "мужской",
            "age_group": "взрослая",
        },
        "rd_data": {
            "type": "declaration",
            "number": "ЕАЭС N RU Д-...",
            "date": "2026-02-01",
            "valid_until": "2029-02-01",
        },
    }
    data.update(overrides)
    return CardView(**data)


def test_valid_card_passes():
    result = run_validation(_good_card())
    assert result.is_valid
    assert result.errors == []


def test_missing_attribute_is_error():
    attrs = {"item_type": "футболка", "size": "M", "color": "чёрный"}
    result = run_validation(_good_card(attributes=attrs))
    codes = {i.code for i in result.errors}
    assert "ATTR_MISSING" in codes
    assert not result.is_valid


def test_missing_gtin_is_error():
    result = run_validation(_good_card(gtin=None))
    assert "GTIN_MISSING" in {i.code for i in result.errors}


def test_invalid_gtin_is_error():
    result = run_validation(_good_card(gtin="123"))
    assert "GTIN_INVALID" in {i.code for i in result.errors}


def test_missing_rd_is_error():
    result = run_validation(_good_card(rd_data={}))
    assert "RD_MISSING" in {i.code for i in result.errors}


def test_mixed_variation_is_error():
    attrs = _good_card().attributes | {"color": "чёрный, белый"}
    result = run_validation(_good_card(attributes=attrs))
    assert "VARIATION_MIXED" in {i.code for i in result.errors}


def test_gtin_not_unique_is_error():
    ctx = ValidationContext(gtin_index={"4600000000015": "other-card"})
    result = run_validation(_good_card(), ctx)
    assert "GTIN_NOT_UNIQUE" in {i.code for i in result.errors}


def test_gtin_unique_for_same_card_ok():
    # Тот же GTIN, но принадлежит этой же карточке (id совпадает) — не ошибка.
    ctx = ValidationContext(gtin_index={"4600000000015": "c1"})
    result = run_validation(_good_card(id="c1"), ctx)
    assert "GTIN_NOT_UNIQUE" not in {i.code for i in result.errors}


def test_unknown_category_is_warning():
    result = run_validation(_good_card(category_code="9999"))
    assert "CATEGORY_UNKNOWN" in {i.code for i in result.warnings}
