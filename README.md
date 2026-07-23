# CSV Snapshot

Create deterministic CSV quality snapshots and catch data drift in CI.

CSV files can remain syntactically valid while their schema, inferred types, missingness, row volume, numeric ranges, string lengths, and date boundaries change silently. CSV Snapshot profiles a local CSV, writes a Git-friendly JSON contract, and compares later exports against that contract.

## Why CSV Snapshot

- **Local-first:** CSV content is processed on the machine or CI runner; no upload and no telemetry.
- **Deterministic:** stable key ordering, stable finding ordering, no timestamps, no random sampling.
- **Privacy-aware by default:** snapshots contain statistics and a SHA-256 content identifier, not raw rows or category values.
- **CI-ready:** exit codes distinguish drift from invalid input or configuration.
- **Cross-platform:** Python 3.11+ on Windows, macOS, and Linux.

## Installation

The project is not published to PyPI in v0.1.0. Install from a checkout:

```bash
git clone https://github.com/kodlbegiko/CSV-Snapshot.git
cd CSV-Snapshot
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

After a GitHub tag is available, an immutable install can use:

```bash
python -m pip install "git+https://github.com/kodlbegiko/CSV-Snapshot.git@v0.1.0"
```

## Quick start

```bash
csv-snapshot create data.csv
csv-snapshot check data.csv --snapshot data.csv.snapshot.json
csv-snapshot diff baseline.csv current.csv
```

Create a configuration file without overwriting an existing one:

```bash
csv-snapshot init
```

## Create a snapshot

```bash
csv-snapshot create data.csv
csv-snapshot create data.csv --output snapshots/data.snapshot.json
csv-snapshot create semicolon.csv --delimiter ";"
```

Existing snapshots are not replaced unless `--force` is supplied. Writes are atomic and symlink outputs are rejected.

## Check against a snapshot

```bash
csv-snapshot check data.csv \
  --snapshot snapshots/data.snapshot.json \
  --format markdown \
  --output report.md
```

Use `--warnings-as-errors` when warnings must block CI. `--ci` is accepted for explicit CI invocation and keeps output deterministic.

## Diff two CSV files

```bash
csv-snapshot diff baseline.csv current.csv --format json
```

Both files are profiled once; terminal, JSON, and Markdown reporters consume the same comparison model.

## Snapshot schema

Each snapshot records:

- schema and tool version
- source filename, byte size, and streaming SHA-256
- delimiter, encoding, row count, and column count
- per-column inferred type, null statistics, exact distinct count, and type-specific metrics

The machine-readable schema is packaged at `src/csv_snapshot/snapshot-schema.json`. See [Snapshot format](docs/snapshot-format.md).

## Drift rules

v0.1.0 detects:

- added, removed, reordered, and type-changed columns
- nullable changes
- row-count and empty/header-only outputs
- null-rate increases
- numeric min, max, mean, and new negative values
- string length and distinct-count changes
- date/datetime earliest and latest changes
- configured column contracts for type, nullability, null rate, min, and max

See [Drift rules](docs/drift-rules.md).

## Threshold configuration

`csv-snapshot.toml` is parsed with the Python TOML parser and validated by Pydantic. It is data only; executable Python configuration is not supported.

```toml
[thresholds]
row_count_relative_change = 0.20
null_rate_absolute_change = 0.05
numeric_mean_relative_change = 0.20
distinct_count_relative_change = 0.30

[columns.age]
type = "integer"
nullable = true
min = 0
max = 130
```

See [Configuration](docs/configuration.md).

## GitHub Actions

Until PyPI publication, either install from a tag or use the repository composite action:

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  - uses: kodlbegiko/CSV-Snapshot/.github/actions/csv-snapshot-check@v0.1.0
    with:
      csv-path: data/export.csv
      snapshot-path: snapshots/export.snapshot.json
```

The repository CI validates Python 3.11 and 3.12 across Ubuntu, Windows, and macOS.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Completed without blocking errors |
| 1 | Blocking drift or quality failure found |
| 2 | Invalid CSV, configuration, snapshot, output path, or tool execution failure |

Warnings become code 1 only with `--warnings-as-errors`.

## Type inference

Inference is deterministic and independent of locale and local timezone. Leading-zero identifiers such as `00123` remain strings. Integers and floats merge to float; incompatible observed types become `mixed`. Empty strings are counted separately from configured null tokens. See [Type inference](docs/type-inference.md).

## Performance model

Rows are streamed with Python's CSV parser. Exact distinct counts use a temporary SQLite database, avoiding a Python list or an in-memory set containing every row/value. A 50 MiB synthetic test with 840,346 rows produced a 2,604-byte snapshot in 21.381564 seconds on the validation environment. Results vary by CPU, storage, and data cardinality. See [Performance](docs/performance.md).

## Security and privacy model

CSV cells are treated only as data. The tool executes no formulas or cell content, performs no network requests, records no telemetry, preserves the source file, and omits raw values from snapshots and findings. SHA-256 identifies content; it does not anonymize or secure data. See [Privacy](docs/privacy.md) and [Security policy](SECURITY.md).

## Limitations

v0.1.0 supports UTF-8/UTF-8 BOM, a header row, configurable single-character delimiters, LF/CRLF, quoted commas, and multiline quoted fields. It does not support XLSX, Parquet, JSONL, remote URLs, compressed archives, automatic cleaning, ML drift metrics, or distributed multi-terabyte processing. See [Limitations](docs/limitations.md).

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
pytest
pytest --cov=csv_snapshot --cov-branch
python -m build
twine check dist/*
```

See [Contributing](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
