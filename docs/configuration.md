# Configuration

`csv-snapshot.toml` is discovered in the current working directory or supplied with `--config`. `csv-snapshot init` creates a default file and refuses replacement without `--force`.

Pydantic rejects unknown keys, invalid severities, percentage values outside their allowed range, delimiters longer than one character, and column `min` values greater than `max`.

Null tokens are explicit strings. Empty CSV fields remain empty strings unless the user deliberately includes `""` in `null_values`. Executable Python configuration and external file includes are not supported.

Unknown CSV columns are profiled normally. Per-column contracts apply only to matching names; a missing contracted column is already handled by baseline schema drift when it existed in the snapshot.
