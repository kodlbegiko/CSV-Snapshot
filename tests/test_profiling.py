import json
from pathlib import Path

import pytest

from csv_snapshot.errors import CsvInputError
from csv_snapshot.models import BooleanMetrics, NumericMetrics, StringMetrics, TemporalMetrics
from csv_snapshot.profiling import profile_csv, sha256_file
from csv_snapshot.serialization import json_text


def test_simple_profile(fixtures_dir: Path, config) -> None:
    snapshot = profile_csv(fixtures_dir / "simple-valid/data.csv", config)
    assert snapshot.csv.row_count == 2
    assert snapshot.csv.column_count == 3
    assert [column.inferred_type for column in snapshot.columns] == ["integer", "integer", "string"]


def test_utf8_bom(fixtures_dir: Path, config) -> None:
    snapshot = profile_csv(fixtures_dir / "utf8-bom/data.csv", config)
    assert snapshot.columns[0].name == "id"
    assert snapshot.csv.encoding == "utf-8-sig"


@pytest.mark.parametrize("folder", ["crlf", "quoted-commas", "multiline-fields"])
def test_valid_csv_variants(fixtures_dir: Path, config, folder: str) -> None:
    snapshot = profile_csv(fixtures_dir / folder / "data.csv", config)
    assert snapshot.csv.row_count >= 1


def test_empty_file(fixtures_dir: Path, config) -> None:
    snapshot = profile_csv(fixtures_dir / "empty-file/data.csv", config)
    assert snapshot.csv.row_count == 0
    assert snapshot.csv.column_count == 0


def test_header_only(fixtures_dir: Path, config) -> None:
    snapshot = profile_csv(fixtures_dir / "header-only/data.csv", config)
    assert snapshot.csv.row_count == 0
    assert [column.name for column in snapshot.columns] == ["id", "name"]


@pytest.mark.parametrize("folder", ["duplicate-headers", "irregular-row-length"])
def test_invalid_csv(fixtures_dir: Path, config, folder: str) -> None:
    with pytest.raises(CsvInputError):
        profile_csv(fixtures_dir / folder / "data.csv", config)


def test_missing_file(config, tmp_path: Path) -> None:
    with pytest.raises(CsvInputError, match="not found"):
        profile_csv(tmp_path / "missing.csv", config)


def test_all_null_column(fixtures_dir: Path, config) -> None:
    snapshot = profile_csv(fixtures_dir / "all-null-column/data.csv", config)
    column = snapshot.columns[1]
    assert column.inferred_type == "null"
    assert column.null_count == 2
    assert column.distinct_count == 0


def test_mixed_type_column(fixtures_dir: Path, config) -> None:
    snapshot = profile_csv(fixtures_dir / "mixed-type-column/data.csv", config)
    assert snapshot.columns[1].inferred_type == "mixed"
    assert isinstance(snapshot.columns[1].metrics, StringMetrics)


def test_leading_zero_is_string(fixtures_dir: Path, config) -> None:
    snapshot = profile_csv(fixtures_dir / "leading-zero-identifiers/data.csv", config)
    assert snapshot.columns[0].inferred_type == "string"


def test_numeric_metrics(tmp_path: Path, config) -> None:
    path = tmp_path / "n.csv"
    path.write_text("value\n-1\n0\n2\n", encoding="utf-8")
    metrics = profile_csv(path, config).columns[0].metrics
    assert isinstance(metrics, NumericMetrics)
    assert metrics.min == -1
    assert metrics.max == 2
    assert metrics.mean == pytest.approx(1 / 3)
    assert metrics.zero_count == 1
    assert metrics.negative_count == 1


def test_boolean_metrics(tmp_path: Path, config) -> None:
    path = tmp_path / "b.csv"
    path.write_text("flag\ntrue\nFALSE\ntrue\n", encoding="utf-8")
    metrics = profile_csv(path, config).columns[0].metrics
    assert isinstance(metrics, BooleanMetrics)
    assert metrics.true_count == 2
    assert metrics.false_count == 1


def test_string_empty_is_not_null(tmp_path: Path, config) -> None:
    path = tmp_path / "s.csv"
    path.write_text('value\n""\nhello\n', encoding="utf-8")
    column = profile_csv(path, config).columns[0]
    assert column.null_count == 0
    assert column.non_null_count == 2
    assert isinstance(column.metrics, StringMetrics)
    assert column.metrics.empty_string_count == 1


def test_temporal_metrics(fixtures_dir: Path, config) -> None:
    snapshot = profile_csv(fixtures_dir / "date-and-datetime/data.csv", config)
    date_metrics = snapshot.columns[0].metrics
    datetime_metrics = snapshot.columns[1].metrics
    assert isinstance(date_metrics, TemporalMetrics)
    assert date_metrics.earliest == "2026-07-23"
    assert isinstance(datetime_metrics, TemporalMetrics)
    assert datetime_metrics.earliest == "2026-07-23T12:30:00"


def test_snapshot_is_deterministic(fixtures_dir: Path, config) -> None:
    path = fixtures_dir / "simple-valid/data.csv"
    assert json_text(profile_csv(path, config)) == json_text(profile_csv(path, config))


def test_privacy_snapshot_does_not_contain_sensitive_values(fixtures_dir: Path, config) -> None:
    text = json_text(profile_csv(fixtures_dir / "privacy-sensitive-values/data.csv", config))
    assert "alice@example.test" not in text
    assert "secret-token-1" not in text
    json.loads(text)


def test_sha256_streaming(fixtures_dir: Path) -> None:
    value = sha256_file(fixtures_dir / "simple-valid/data.csv", chunk_size=3)
    assert value.startswith("sha256:")
    assert len(value) == 71
