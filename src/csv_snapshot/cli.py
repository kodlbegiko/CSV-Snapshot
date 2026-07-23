"""Command-line interface for CSV Snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Callable, TypeVar

import typer

from .comparison import compare_snapshots
from .config import DEFAULT_CONFIG, AppConfig, discover_config, load_config
from .errors import CsvSnapshotError, OutputError
from .profiling import profile_csv
from .reporters import render_report
from .serialization import atomic_write_text, load_snapshot, write_snapshot
from .version import __version__

app = typer.Typer(
    name="csv-snapshot",
    help="Create deterministic CSV quality snapshots and catch data drift in CI.",
    no_args_is_help=True,
    invoke_without_command=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)

OutputFormat = Annotated[
    str,
    typer.Option("--format", help="Report format: terminal, json, or markdown."),
]
T = TypeVar("T")


def _validated_format(value: str) -> str:
    if value not in {"terminal", "json", "markdown"}:
        raise typer.BadParameter("must be terminal, json, or markdown")
    return value


def _config_for(csv_path: Path, config_path: Path | None, delimiter: str | None) -> AppConfig:
    selected = config_path or discover_config(Path.cwd())
    config = load_config(selected)
    if delimiter is not None:
        if len(delimiter) != 1:
            raise CsvSnapshotError("delimiter must be exactly one character")
        config.snapshot.delimiter = delimiter
    return config


def _handle_error(action: Callable[[], T]) -> T:
    try:
        return action()
    except CsvSnapshotError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


@app.callback()
def root(
    version: Annotated[
        bool | None,
        typer.Option("--version", help="Show the installed version and exit."),
    ] = None,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command("create")
def create_command(
    csv_file: Annotated[Path, typer.Argument(help="CSV file to profile.")],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    delimiter: Annotated[str | None, typer.Option("--delimiter")] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Replace an existing snapshot.")
    ] = False,
) -> None:
    """Create a deterministic quality snapshot."""

    def action() -> None:
        destination = output or Path(f"{csv_file}.snapshot.json")
        if destination.resolve(strict=False) == csv_file.resolve(strict=False):
            raise OutputError("output path must not overwrite the source CSV")
        snapshot = profile_csv(csv_file, _config_for(csv_file, config, delimiter))
        write_snapshot(snapshot, destination, force=force)
        typer.echo(f"Created snapshot: {destination}")

    _handle_error(action)


@app.command("check")
def check_command(
    csv_file: Annotated[Path, typer.Argument(help="Current CSV file.")],
    snapshot: Annotated[Path, typer.Option("--snapshot", help="Committed baseline snapshot.")],
    output_format: OutputFormat = "terminal",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    delimiter: Annotated[str | None, typer.Option("--delimiter")] = None,
    warnings_as_errors: Annotated[bool, typer.Option("--warnings-as-errors")] = False,
    ci: Annotated[
        bool, typer.Option("--ci", help="CI-friendly mode with deterministic output.")
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Replace an existing report.")] = False,
) -> None:
    """Check a CSV against a baseline snapshot."""

    del ci

    def action() -> None:
        fmt = _validated_format(output_format)
        app_config = _config_for(csv_file, config, delimiter)
        baseline = load_snapshot(snapshot)
        current = profile_csv(csv_file, app_config)
        report = compare_snapshots(
            baseline,
            current,
            app_config,
            baseline_name=snapshot.name,
            current_name=csv_file.name,
        )
        rendered = render_report(report, fmt)
        if output:
            atomic_write_text(output, rendered, force=force)
        else:
            typer.echo(rendered, nl=False)
        blocking = report.summary.error_count > 0 or (
            warnings_as_errors and report.summary.warning_count > 0
        )
        if blocking:
            raise typer.Exit(code=1)

    _handle_error(action)


@app.command("diff")
def diff_command(
    baseline_csv: Annotated[Path, typer.Argument(help="Baseline CSV file.")],
    current_csv: Annotated[Path, typer.Argument(help="Current CSV file.")],
    output_format: OutputFormat = "terminal",
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    delimiter: Annotated[str | None, typer.Option("--delimiter")] = None,
    warnings_as_errors: Annotated[bool, typer.Option("--warnings-as-errors")] = False,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Compare two CSV files without writing a baseline snapshot."""

    def action() -> None:
        fmt = _validated_format(output_format)
        app_config = _config_for(current_csv, config, delimiter)
        baseline = profile_csv(baseline_csv, app_config)
        current = profile_csv(current_csv, app_config)
        report = compare_snapshots(
            baseline,
            current,
            app_config,
            baseline_name=baseline_csv.name,
            current_name=current_csv.name,
        )
        rendered = render_report(report, fmt)
        if output:
            atomic_write_text(output, rendered, force=force)
        else:
            typer.echo(rendered, nl=False)
        blocking = report.summary.error_count > 0 or (
            warnings_as_errors and report.summary.warning_count > 0
        )
        if blocking:
            raise typer.Exit(code=1)

    _handle_error(action)


@app.command("init")
def init_command(
    output: Annotated[Path, typer.Option("--output", "-o")] = Path("csv-snapshot.toml"),
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Create a documented default configuration file."""

    def action() -> None:
        atomic_write_text(output, DEFAULT_CONFIG, force=force)
        typer.echo(f"Created configuration: {output}")

    _handle_error(action)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
