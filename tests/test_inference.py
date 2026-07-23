from datetime import date, datetime
from decimal import Decimal

import pytest

from csv_snapshot.inference import (
    classify,
    merge_types,
    parse_boolean,
    parse_date,
    parse_datetime,
    parse_number,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1", "integer"),
        ("-1", "integer"),
        ("0", "integer"),
        ("1.0", "float"),
        (".5", "float"),
        ("1e6", "float"),
        ("-2.5E-2", "float"),
        ("true", "boolean"),
        ("FALSE", "boolean"),
        ("2026-07-23", "date"),
        ("2026-07-23T12:00:00", "datetime"),
        ("2026-07-23T12:00:00Z", "datetime"),
        ("00123", "string"),
        ("hello", "string"),
        ("NaN", "string"),
        ("Infinity", "string"),
    ],
)
def test_classify(value: str, expected: str) -> None:
    assert classify(value) == expected


@pytest.mark.parametrize(
    ("types", "expected"),
    [
        (set(), "null"),
        ({"integer"}, "integer"),
        ({"integer", "float"}, "float"),
        ({"string"}, "string"),
        ({"integer", "string"}, "mixed"),
        ({"date", "datetime"}, "mixed"),
    ],
)
def test_merge_types(types: set[str], expected: str) -> None:
    assert merge_types(types) == expected


def test_parse_helpers() -> None:
    assert parse_boolean("TRUE") is True
    assert parse_boolean("no") is None
    assert parse_number("1.5") == Decimal("1.5")
    assert parse_number("001") is None
    assert parse_date("2026-07-23") == date(2026, 7, 23)
    assert parse_date("23/07/2026") is None
    assert parse_datetime("2026-07-23T12:00:00") == datetime(2026, 7, 23, 12)
    assert parse_datetime("2026-07-23") is None


def test_aware_datetime_is_normalized_to_utc() -> None:
    assert parse_datetime("2026-07-23T08:00:00+08:00") == datetime(2026, 7, 23, 0)
