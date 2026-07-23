# Performance

The CSV reader streams records and never stores the full row set in a Python list. Aggregates are constant-memory per column. Exact distinct values are stored in a temporary SQLite database, shifting high-cardinality storage from Python memory to temporary disk.

Validation environment results:

| Target | Actual bytes | Rows | Elapsed | Peak RSS | Snapshot |
|---:|---:|---:|---:|---:|---:|
| 10 MiB | 10,485,778 | 168,071 | 4.261329 s | 115,124 KiB | 2,602 bytes |
| 50 MiB | 52,428,819 | 840,346 | 21.381564 s | 115,128 KiB | 2,604 bytes |

These are reproducible synthetic measurements, not universal performance guarantees. CPU, storage, operating system, column count, field size, and cardinality affect runtime and temporary disk usage. Run `python benchmarks/profile_benchmark.py --megabytes 10` to reproduce.
