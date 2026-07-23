from pathlib import Path

from typer.testing import CliRunner

from csv_snapshot.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def test_create_and_check(fixtures_dir: Path, tmp_path: Path) -> None:
    csv_file = fixtures_dir / "simple-valid/data.csv"
    snapshot = tmp_path / "data.snapshot.json"
    created = runner.invoke(app, ["create", str(csv_file), "--output", str(snapshot)])
    assert created.exit_code == 0
    checked = runner.invoke(app, ["check", str(csv_file), "--snapshot", str(snapshot)])
    assert checked.exit_code == 0
    assert "PASS" in checked.stdout


def test_create_refuses_overwrite(fixtures_dir: Path, tmp_path: Path) -> None:
    csv_file = fixtures_dir / "simple-valid/data.csv"
    snapshot = tmp_path / "data.snapshot.json"
    assert runner.invoke(app, ["create", str(csv_file), "-o", str(snapshot)]).exit_code == 0
    result = runner.invoke(app, ["create", str(csv_file), "-o", str(snapshot)])
    assert result.exit_code == 2
    assert "already exists" in result.stderr


def test_create_force(fixtures_dir: Path, tmp_path: Path) -> None:
    csv_file = fixtures_dir / "simple-valid/data.csv"
    snapshot = tmp_path / "data.snapshot.json"
    runner.invoke(app, ["create", str(csv_file), "-o", str(snapshot)])
    result = runner.invoke(app, ["create", str(csv_file), "-o", str(snapshot), "--force"])
    assert result.exit_code == 0


def test_check_blocking_exit(fixtures_dir: Path, tmp_path: Path) -> None:
    baseline = fixtures_dir / "schema-removed-column/baseline.csv"
    current = fixtures_dir / "schema-removed-column/current.csv"
    snapshot = tmp_path / "baseline.json"
    runner.invoke(app, ["create", str(baseline), "-o", str(snapshot)])
    result = runner.invoke(app, ["check", str(current), "--snapshot", str(snapshot)])
    assert result.exit_code == 1
    assert "column_removed" in result.stdout


def test_warnings_as_errors(fixtures_dir: Path, tmp_path: Path) -> None:
    baseline = fixtures_dir / "schema-added-column/baseline.csv"
    current = fixtures_dir / "schema-added-column/current.csv"
    snapshot = tmp_path / "baseline.json"
    runner.invoke(app, ["create", str(baseline), "-o", str(snapshot)])
    normal = runner.invoke(app, ["check", str(current), "--snapshot", str(snapshot)])
    strict = runner.invoke(
        app,
        ["check", str(current), "--snapshot", str(snapshot), "--warnings-as-errors"],
    )
    assert normal.exit_code == 0
    assert strict.exit_code == 1


def test_diff_json(fixtures_dir: Path) -> None:
    baseline = fixtures_dir / "schema-added-column/baseline.csv"
    current = fixtures_dir / "schema-added-column/current.csv"
    result = runner.invoke(app, ["diff", str(baseline), str(current), "--format", "json"])
    assert result.exit_code == 0
    assert '"ruleId": "schema.column_added"' in result.stdout


def test_markdown_output(fixtures_dir: Path, tmp_path: Path) -> None:
    baseline = fixtures_dir / "simple-valid/data.csv"
    snapshot = tmp_path / "baseline.json"
    report = tmp_path / "report.md"
    runner.invoke(app, ["create", str(baseline), "-o", str(snapshot)])
    result = runner.invoke(
        app,
        [
            "check",
            str(baseline),
            "--snapshot",
            str(snapshot),
            "--format",
            "markdown",
            "--output",
            str(report),
        ],
    )
    assert result.exit_code == 0
    assert report.read_text().startswith("# CSV Snapshot Report")


def test_init_and_force(tmp_path: Path) -> None:
    output = tmp_path / "csv-snapshot.toml"
    assert runner.invoke(app, ["init", "-o", str(output)]).exit_code == 0
    assert runner.invoke(app, ["init", "-o", str(output)]).exit_code == 2
    assert runner.invoke(app, ["init", "-o", str(output), "--force"]).exit_code == 0


def test_invalid_delimiter(fixtures_dir: Path) -> None:
    result = runner.invoke(
        app,
        ["create", str(fixtures_dir / "simple-valid/data.csv"), "--delimiter", "||"],
    )
    assert result.exit_code == 2
    assert "delimiter" in result.stderr


def test_invalid_format(fixtures_dir: Path) -> None:
    result = runner.invoke(
        app,
        [
            "diff",
            str(fixtures_dir / "simple-valid/data.csv"),
            str(fixtures_dir / "simple-valid/data.csv"),
            "--format",
            "xml",
        ],
    )
    assert result.exit_code == 2
