from pathlib import Path

import pytest

from csv_snapshot.comparison import compare_snapshots
from csv_snapshot.config import AppConfig, ColumnRule
from csv_snapshot.profiling import profile_csv


def compare_pair(fixtures_dir: Path, folder: str, config: AppConfig | None = None):
    app_config = config or AppConfig()
    baseline = profile_csv(fixtures_dir / folder / "baseline.csv", app_config)
    current = profile_csv(fixtures_dir / folder / "current.csv", app_config)
    return compare_snapshots(baseline, current, app_config)


def rule_ids(report) -> set[str]:
    return {finding.rule_id for finding in report.findings}


@pytest.mark.parametrize(
    ("folder", "expected"),
    [
        ("schema-added-column", "schema.column_added"),
        ("schema-removed-column", "schema.column_removed"),
        ("schema-reordered-columns", "schema.column_order_changed"),
        ("type-drift", "schema.type_changed"),
        ("null-rate-drift", "missingness.null_rate_increased"),
        ("numeric-range-drift", "numeric.min_changed"),
        ("row-count-drift", "volume.row_count_changed"),
        ("string-length-drift", "string.max_length_changed"),
    ],
)
def test_drift_rules(fixtures_dir: Path, folder: str, expected: str) -> None:
    assert expected in rule_ids(compare_pair(fixtures_dir, folder))


def test_removed_column_blocks(fixtures_dir: Path) -> None:
    report = compare_pair(fixtures_dir, "schema-removed-column")
    assert report.passed is False
    assert report.summary.error_count >= 1


def test_added_column_is_warning(fixtures_dir: Path) -> None:
    report = compare_pair(fixtures_dir, "schema-added-column")
    assert report.passed is True
    assert report.summary.warning_count >= 1


def test_negative_values_appeared(fixtures_dir: Path) -> None:
    report = compare_pair(fixtures_dir, "numeric-range-drift")
    assert "numeric.negative_values_appeared" in rule_ids(report)


def test_empty_current_is_error(fixtures_dir: Path, config: AppConfig) -> None:
    baseline = profile_csv(fixtures_dir / "simple-valid/data.csv", config)
    current = profile_csv(fixtures_dir / "empty-file/data.csv", config)
    report = compare_snapshots(baseline, current, config)
    assert "volume.empty_file" in rule_ids(report)
    assert not report.passed


def test_header_only_current_is_warning(fixtures_dir: Path, config: AppConfig) -> None:
    baseline = profile_csv(fixtures_dir / "simple-valid/data.csv", config)
    current = profile_csv(fixtures_dir / "header-only/data.csv", config)
    report = compare_snapshots(baseline, current, config)
    assert "volume.header_only" in rule_ids(report)


def test_identical_files_pass(fixtures_dir: Path, config: AppConfig) -> None:
    snapshot = profile_csv(fixtures_dir / "simple-valid/data.csv", config)
    report = compare_snapshots(snapshot, snapshot, config)
    assert report.passed
    assert report.findings == []


def test_expected_type_rule(tmp_path: Path, config: AppConfig) -> None:
    path = tmp_path / "data.csv"
    path.write_text("id\n001\n", encoding="utf-8")
    config.columns["id"] = ColumnRule(type="integer")
    snapshot = profile_csv(path, config)
    report = compare_snapshots(snapshot, snapshot, config)
    assert "quality.expected_type" in rule_ids(report)


def test_not_nullable_rule(tmp_path: Path, config: AppConfig) -> None:
    path = tmp_path / "data.csv"
    path.write_text("id\nNULL\n", encoding="utf-8")
    config.columns["id"] = ColumnRule(nullable=False)
    snapshot = profile_csv(path, config)
    report = compare_snapshots(snapshot, snapshot, config)
    assert "quality.not_nullable" in rule_ids(report)


def test_max_null_rate_rule(tmp_path: Path, config: AppConfig) -> None:
    path = tmp_path / "data.csv"
    path.write_text("id\nNULL\n1\n", encoding="utf-8")
    config.columns["id"] = ColumnRule(max_null_rate=0.1)
    snapshot = profile_csv(path, config)
    report = compare_snapshots(snapshot, snapshot, config)
    assert "quality.max_null_rate" in rule_ids(report)


@pytest.mark.parametrize(
    ("rule", "expected"),
    [
        (ColumnRule(min=0), "quality.minimum"),
        (ColumnRule(max=5), "quality.maximum"),
    ],
)
def test_numeric_bounds(tmp_path: Path, config: AppConfig, rule: ColumnRule, expected: str) -> None:
    path = tmp_path / "data.csv"
    path.write_text("value\n-1\n10\n", encoding="utf-8")
    config.columns["value"] = rule
    snapshot = profile_csv(path, config)
    report = compare_snapshots(snapshot, snapshot, config)
    assert expected in rule_ids(report)


def test_findings_are_stably_sorted(fixtures_dir: Path) -> None:
    report = compare_pair(fixtures_dir, "numeric-range-drift")
    keys = [
        (finding.severity, finding.column or "", finding.rule_id)
        for finding in report.findings
    ]
    severity = {"error": 0, "warning": 1, "info": 2}
    assert keys == sorted(keys, key=lambda item: (severity[item[0]], item[1], item[2]))
