# Privacy

CSV Snapshot is local-first and performs no network requests or telemetry. The snapshot contains aggregate statistics, a basename, file size, and SHA-256 content hash. It does not persist raw rows or actual distinct values.

Exact distinct counts are calculated in a temporary local SQLite database. This temporary database contains values during processing and is removed when profiling completes. Users handling highly sensitive data should apply normal workstation, filesystem, backup, and CI-runner controls.

A content hash may still be sensitive in some threat models and does not prove that a dataset contains no personal data. CSV Snapshot does not claim anonymity or compliance certification.
