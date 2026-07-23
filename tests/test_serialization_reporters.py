import json
from pathlib import Path

import pytest

from csv_snapshot.comparison import compare_snapshots
from csv_snapshot.errors import OutputError, SnapshotError
from csv_snapshot.profiling import profile_csv
from csv_snapshot.reporters import render_markdown, render_report, render_terminal
from csv_snapshot.serialization import atomic_write_text, json_text, load_snapshot, write_snapshot


def test_snapshot_round_trip(fixtures_dir: Path, config, tmp_path: Path) -> None:
    snapshot = profile_csv(fixtures_dir / "simple-valid/data.csv", config)
    path = tmp_path / "snapshot.json"
    write_snapshot(snapshot, path)
    assert load_snapshot(path) == snapshot


def test_committed_example_snapshot_is_loadable() -> None:
    path = Path(__file__).parents[1] / "examples/snapshots/customers-v1.snapshot.json"
    snapshot = load_snapshot(path)
    assert snapshot.snapshot_schema_version == "1"
    assert snapshot.csv.row_count == 10


def test_json_is_sorted_and_valid(fixtures_dir: Path, config) -> None:
    text = json_text(profile_csv(fixtures_dir / "simple-valid/data.csv", config))
    payload = json.loads(text)
    assert list(payload) == sorted(payload)


def test_atomic_write_refuses_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    atomic_write_text(path, "first")
    with pytest.raises(OutputError, match="already exists"):
        atomic_write_text(path, "second")
    atomic_write_text(path, "second", force=True)
    assert path.read_text() == "second"


def test_atomic_write_refuses_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("x")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(OutputError, match="symlink"):
        atomic_write_text(link, "y", force=True)


def test_load_missing_snapshot(tmp_path: Path) -> None:
    with pytest.raises(SnapshotError, match="not found"):
        load_snapshot(tmp_path / "missing.json")


def test_load_invalid_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(SnapshotError, match="not valid JSON"):
        load_snapshot(path)


def test_reporters(fixtures_dir: Path, config) -> None:
    baseline = profile_csv(fixtures_dir / "schema-added-column/baseline.csv", config)
    current = profile_csv(fixtures_dir / "schema-added-column/current.csv", config)
    report = compare_snapshots(baseline, current, config)
    assert "CSV Snapshot: PASS" in render_terminal(report)
    assert "# CSV Snapshot Report" in render_markdown(report)
    assert json.loads(render_report(report, "json"))["summary"]["warningCount"] >= 1


def test_unknown_report_format(fixtures_dir: Path, config) -> None:
    snapshot = profile_csv(fixtures_dir / "simple-valid/data.csv", config)
    report = compare_snapshots(snapshot, snapshot, config)
    with pytest.raises(ValueError, match="unsupported"):
        render_report(report, "xml")
