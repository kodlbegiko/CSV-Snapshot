"""Deterministic, locale-independent scalar type inference."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

_INTEGER_RE = re.compile(r"^[+-]?(?:0|[1-9][0-9]*)$")
_FLOAT_RE = re.compile(
    r"^[+-]?(?:"
    r"(?:[0-9]+\.[0-9]*)|(?:[0-9]*\.[0-9]+)|(?:[0-9]+[eE][+-]?[0-9]+)|"
    r"(?:[0-9]+\.[0-9]*[eE][+-]?[0-9]+)|(?:[0-9]*\.[0-9]+[eE][+-]?[0-9]+)"
    r")$"
)
_LEADING_ZERO_RE = re.compile(r"^[+-]?0[0-9]+$")
_BOOLEAN_VALUES = {"true": True, "false": False}


def classify(value: str) -> str:
    lowered = value.lower()
    if lowered in _BOOLEAN_VALUES:
        return "boolean"
    if _LEADING_ZERO_RE.fullmatch(value):
        return "string"
    if _INTEGER_RE.fullmatch(value):
        return "integer"
    if _FLOAT_RE.fullmatch(value):
        try:
            parsed = Decimal(value)
            if parsed.is_finite():
                return "float"
        except InvalidOperation:
            pass
    if _parse_datetime(value) is not None:
        return "datetime"
    if _parse_date(value) is not None:
        return "date"
    return "string"


def merge_types(types: set[str]) -> str:
    if not types:
        return "null"
    if types <= {"integer"}:
        return "integer"
    if types <= {"integer", "float"}:
        return "float" if "float" in types else "integer"
    if len(types) == 1:
        return next(iter(types))
    return "mixed"


def parse_boolean(value: str) -> bool | None:
    return _BOOLEAN_VALUES.get(value.lower())


def parse_number(value: str) -> Decimal | None:
    if classify(value) not in {"integer", "float"}:
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def parse_date(value: str) -> date | None:
    return _parse_date(value)


def parse_datetime(value: str) -> datetime | None:
    return _parse_datetime(value)


def _parse_date(value: str) -> date | None:
    try:
        if len(value) != 10:
            return None
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_datetime(value: str) -> datetime | None:
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    if "T" not in candidate:
        return None
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(UTC).replace(tzinfo=None)
