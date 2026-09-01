"""Юнит-тесты доменной логики GTIN: формат и контрольная цифра GS1."""

from app.modules.gtin.domain import check_gtin, compute_check_digit, is_valid_gtin, normalize_gtin


def test_compute_check_digit_known():
    # EAN-13 body 400638133393 -> контрольная цифра 1 (классический пример GS1).
    assert compute_check_digit("400638133393") == 1


def test_valid_ean13():
    assert is_valid_gtin("4006381333931")


def test_valid_gtin13_demo():
    assert is_valid_gtin("4600000000015")


def test_invalid_check_digit():
    result = check_gtin("4600000000019")
    assert result.length_ok
    assert result.is_digits
    assert not result.check_digit_ok
    assert not result.valid


def test_invalid_length():
    result = check_gtin("123")
    assert not result.length_ok
    assert not result.valid


def test_non_digits():
    result = check_gtin("46000ABC0015")
    assert not result.is_digits or not result.valid


def test_non_digits_are_not_silently_removed():
    result = check_gtin("46A01000001002")
    assert result.gtin == "46A01000001002"
    assert not result.is_digits
    assert not result.valid


def test_normalize_strips_spaces():
    assert normalize_gtin("  4600 0000 00015 ") == "4600000000015"


def test_empty_gtin():
    assert not is_valid_gtin("")
    assert not is_valid_gtin(None)
