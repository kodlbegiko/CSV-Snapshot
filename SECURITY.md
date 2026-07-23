# Security policy

## Supported versions

Security fixes are applied to the latest released minor version.

## Reporting

Use GitHub's private vulnerability reporting feature when available. Do not post secrets, personal data, or exploitable details in a public issue.

## Security model

CSV Snapshot treats all cell content as inert data. It does not evaluate spreadsheet formulas, import Python configuration, upload files, send telemetry, or modify the input CSV. Snapshot writes are atomic and refuse symlink destinations. Temporary SQLite storage is deleted after profiling.

The tool does not guarantee anonymity, detect every personal-data field, sanitize CSVs, or replace organizational data governance.
