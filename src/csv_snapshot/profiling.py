"""Streaming CSV profiling without retaining raw rows in Python memory."""

from __future__ import annotations

import csv
import hashlib
import math
import sqlite3
import tempfile
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import TextIO

from .config import AppConfig
from .errors import CsvInputError
from .inference import (
    classify,
    merge_types,
    parse_boolean,
    parse_date,
    parse_datetime,
    parse_number,
)
from .models import (
    BooleanMetrics,
    ColumnProfile,
    CsvInfo,
    NumericMetrics,
    Snapshot,
    SourceInfo,
    StringMetrics,
    TemporalMetrics,
)
from .version import __version__


@dataclass
class NumericAccumulator:
    count: int = 0
    total: Decimal = Decimal(0)
    mean: Decimal = Decimal(0)
    m2: Decimal = Decimal(0)
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    zero_count: int = 0
    negative_count: int = 0

    def add(self, value: Decimal) -> None:
        self.count += 1
        self.total += value
        delta = value - self.mean
        self.mean += delta / self.count
        self.m2 += delta * (value - self.mean)
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        self.zero_count += int(value == 0)
        self.negative_count += int(value < 0)


@dataclass
class ColumnAccumulator:
    name: str
    position: int
    null_count: int = 0
    non_null_count: int = 0
    empty_string_count: int = 0
    observed_types: set[str] = field(default_factory=set)
    numeric: NumericAccumulator = field(default_factory=NumericAccumulator)
    true_count: int = 0
    false_count: int = 0
    length_count: int = 0
    length_total: int = 0
    min_length: int | None = None
    max_length: int | None = None
    date_earliest: str | None = None
    date_latest: str | None = None
    datetime_earliest: str | None = None
    datetime_latest: str | None = None

    def add(self, raw: str, null_values: set[str]) -> None:
        if raw in null_values:
            self.null_count += 1
            return

        self.non_null_count += 1
        length = len(raw)
        self.length_count += 1
        self.length_total += length
        self.min_length = length if self.min_length is None else min(self.min_length, length)
        self.max_length = length if self.max_length is None else max(self.max_length, length)
        if raw == "":
            self.empty_string_count += 1
            return

        kind = classify(raw)
        self.observed_types.add(kind)
        number = parse_number(raw)
        if number is not None:
            self.numeric.add(number)
        boolean = parse_boolean(raw)
        if boolean is True:
            self.true_count += 1
        elif boolean is False:
            self.false_count += 1
        parsed_date = parse_date(raw)
        if parsed_date is not None:
            iso = parsed_date.isoformat()
            self.date_earliest = iso if self.date_earliest is None else min(self.date_earliest, iso)
            self.date_latest = iso if self.date_latest is None else max(self.date_latest, iso)
        parsed_datetime = parse_datetime(raw)
        if parsed_datetime is not None:
            iso = parsed_datetime.isoformat()
            self.datetime_earliest = (
                iso if self.datetime_earliest is None else min(self.datetime_earliest, iso)
            )
            self.datetime_latest = (
                iso if self.datetime_latest is None else max(self.datetime_latest, iso)
            )


def _clean_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    result = round(float(value), 12)
    if not math.isfinite(result):
        return None
    return 0.0 if result == 0 else result


def _number_for_json(value: Decimal | None, inferred_type: str) -> int | float | None:
    if value is None:
        return None
    if inferred_type == "integer":
        return int(value)
    return _clean_float(value)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _detect_encoding(path: Path) -> str:
    with path.open("rb") as handle:
        return "utf-8-sig" if handle.read(3) == b"\xef\xbb\xbf" else "utf-8"


def _open_csv(path: Path) -> TextIO:
    try:
        return path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise CsvInputError(f"unable to open CSV: {path}") from exc


def profile_csv(path: Path, config: AppConfig) -> Snapshot:
    path = path.expanduser()
    if not path.exists():
        raise CsvInputError(f"CSV file not found: {path}")
    if not path.is_file():
        raise CsvInputError(f"CSV input is not a regular file: {path}")

    null_values = set(config.snapshot.null_values)
    row_count = 0
    headers: list[str] = []
    accumulators: list[ColumnAccumulator] = []

    with tempfile.TemporaryDirectory(prefix="csv-snapshot-") as temp_dir:
        db_path = Path(temp_dir) / "distinct.sqlite3"
        connection = sqlite3.connect(db_path)
        connection.execute(
            "CREATE TABLE distinct_values (column_position INTEGER NOT NULL, value TEXT NOT NULL, "
            "PRIMARY KEY (column_position, value)) WITHOUT ROWID"
        )
        try:
            with _open_csv(path) as handle:
                reader = csv.reader(handle, delimiter=config.snapshot.delimiter, strict=True)
                try:
                    headers = next(reader)
                except StopIteration:
                    headers = []
                except (csv.Error, UnicodeDecodeError) as exc:
                    raise CsvInputError(f"unable to parse CSV header: {exc}") from exc

                if headers:
                    duplicates = sorted({name for name in headers if headers.count(name) > 1})
                    if duplicates:
                        raise CsvInputError(
                            "duplicate header names are not supported: " + ", ".join(duplicates)
                        )
                    accumulators = [
                        ColumnAccumulator(name=name, position=index)
                        for index, name in enumerate(headers)
                    ]

                try:
                    for line_number, row in enumerate(reader, start=2):
                        if len(row) != len(headers):
                            raise CsvInputError(
                                f"irregular row length at record {line_number}: "
                                f"expected {len(headers)} fields, found {len(row)}"
                            )
                        row_count += 1
                        for index, raw in enumerate(row):
                            accumulators[index].add(raw, null_values)
                            if raw not in null_values:
                                connection.execute(
                                    "INSERT OR IGNORE INTO distinct_values(column_position, value) "
                                    "VALUES (?, ?)",
                                    (index, raw),
                                )
                        if row_count % 10_000 == 0:
                            connection.commit()
                except UnicodeDecodeError as exc:
                    raise CsvInputError(f"CSV is not valid UTF-8: {exc}") from exc
                except csv.Error as exc:
                    raise CsvInputError(f"malformed CSV: {exc}") from exc
            connection.commit()

            columns: list[ColumnProfile] = []
            for accumulator in accumulators:
                distinct_count = connection.execute(
                    "SELECT COUNT(*) FROM distinct_values WHERE column_position = ?",
                    (accumulator.position,),
                ).fetchone()[0]
                inferred_type = merge_types(accumulator.observed_types)
                metrics = _build_metrics(accumulator, inferred_type)
                columns.append(
                    ColumnProfile(
                        name=accumulator.name,
                        position=accumulator.position,
                        inferredType=inferred_type,
                        nullable=accumulator.null_count > 0,
                        nullCount=accumulator.null_count,
                        nullRate=_rate(accumulator.null_count, row_count),
                        nonNullCount=accumulator.non_null_count,
                        distinctCount=distinct_count,
                        metrics=metrics,
                    )
                )
        finally:
            connection.close()

    return Snapshot(
        snapshotSchemaVersion="1",
        toolVersion=__version__,
        source=SourceInfo(
            fileName=path.name,
            fileSizeBytes=path.stat().st_size,
            contentHash=sha256_file(path),
        ),
        csv=CsvInfo(
            delimiter=config.snapshot.delimiter,
            hasHeader=True,
            encoding=_detect_encoding(path),
            rowCount=row_count,
            columnCount=len(headers),
        ),
        columns=columns,
    )


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 12) if denominator else 0.0


def _build_metrics(
    accumulator: ColumnAccumulator, inferred_type: str
) -> NumericMetrics | StringMetrics | BooleanMetrics | TemporalMetrics | None:
    if inferred_type in {"integer", "float"}:
        variance = (
            accumulator.numeric.m2 / accumulator.numeric.count
            if accumulator.numeric.count
            else Decimal(0)
        )
        return NumericMetrics(
            min=_number_for_json(accumulator.numeric.minimum, inferred_type),
            max=_number_for_json(accumulator.numeric.maximum, inferred_type),
            mean=_clean_float(accumulator.numeric.mean)
            if accumulator.numeric.count
            else None,
            standardDeviation=_clean_float(variance.sqrt())
            if accumulator.numeric.count
            else None,
            zeroCount=accumulator.numeric.zero_count,
            negativeCount=accumulator.numeric.negative_count,
        )
    if inferred_type == "boolean":
        return BooleanMetrics(trueCount=accumulator.true_count, falseCount=accumulator.false_count)
    if inferred_type == "date":
        return TemporalMetrics(
            earliest=accumulator.date_earliest,
            latest=accumulator.date_latest,
            parseSuccessRate=1.0,
        )
    if inferred_type == "datetime":
        return TemporalMetrics(
            earliest=accumulator.datetime_earliest,
            latest=accumulator.datetime_latest,
            parseSuccessRate=1.0,
        )
    if inferred_type in {"string", "mixed"} or accumulator.empty_string_count:
        return StringMetrics(
            minLength=accumulator.min_length,
            maxLength=accumulator.max_length,
            meanLength=round(accumulator.length_total / accumulator.length_count, 12)
            if accumulator.length_count
            else None,
            emptyStringCount=accumulator.empty_string_count,
            emptyStringRate=_rate(accumulator.empty_string_count, accumulator.non_null_count),
        )
    return None
