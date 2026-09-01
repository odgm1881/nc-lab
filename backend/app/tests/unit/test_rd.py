"""Юнит-тесты доменной логики РД: структура, полнота, срок действия."""

from datetime import date

from app.modules.rd.domain import check_rd


def test_complete_declaration():
    rd = {
        "type": "declaration",
        "number": "ЕАЭС N RU Д-...",
        "date": "2026-02-01",
        "valid_until": "2029-02-01",
    }
    result = check_rd(rd, today=date(2026, 7, 1))
    assert result.complete
    assert not result.missing_fields


def test_missing_number():
    rd = {"type": "certificate", "date": "2026-02-01", "valid_until": "2028-02-01"}
    result = check_rd(rd, today=date(2026, 7, 1))
    assert "number" in result.missing_fields
    assert not result.complete


def test_unknown_type():
    rd = {"type": "какой-то", "number": "1", "date": "2026-02-01"}
    result = check_rd(rd)
    assert not result.known_type
    assert not result.complete


def test_expired():
    rd = {
        "type": "declaration",
        "number": "1",
        "date": "2020-01-01",
        "valid_until": "2021-01-01",
    }
    result = check_rd(rd, today=date(2026, 7, 1))
    assert result.expired
    assert not result.complete


def test_refusal_letter_needs_no_expiry():
    rd = {"type": "refusal_letter", "number": "1", "date": "2026-02-01"}
    result = check_rd(rd, today=date(2026, 7, 1))
    assert result.complete


def test_empty_rd():
    result = check_rd({})
    assert not result.complete
    assert "type" in result.missing_fields


def test_invalid_dates_are_rejected():
    result = check_rd(
        {
            "type": "declaration",
            "number": "1",
            "date": "not-a-date",
            "valid_until": "also-not-a-date",
        }
    )
    assert result.invalid_date_fields == ["date", "valid_until"]
    assert not result.complete


def test_issue_date_cannot_be_after_expiry():
    result = check_rd(
        {
            "type": "certificate",
            "number": "1",
            "date": "2029-01-01",
            "valid_until": "2028-01-01",
        },
        today=date(2026, 7, 1),
    )
    assert result.invalid_date_range
    assert not result.complete
