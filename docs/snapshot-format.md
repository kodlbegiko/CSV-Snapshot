# Snapshot format

Snapshot schema version `1` is a deterministic JSON object with `snapshotSchemaVersion`, `toolVersion`, `source`, `csv`, and `columns`. Keys are sorted when serialized; no timestamp is emitted.

`source.contentHash` is a streaming SHA-256 identifier. It is not encryption, anonymization, or the sole drift signal. `source.fileName` stores only the basename, not an absolute home-directory path.

Per-column fields include position, inferred type, null/non-null counts, null rate, and exact distinct count. Metrics depend on inferred type:

- numeric: min, max, mean, population standard deviation, zero count, negative count
- string/mixed: min, max, and mean length plus empty-string count/rate
- boolean: true and false count
- date/datetime: earliest, latest, and parse success rate

Snapshots omit raw rows, actual category values, email lists, names, identifiers, and tokens by default. The formal JSON Schema is `src/csv_snapshot/snapshot-schema.json`.
