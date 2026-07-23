"""Generate deterministic synthetic CSVs and measure profiling behavior."""

from __future__ import annotations

import argparse
import json
import resource
import tempfile
import time
from pathlib import Path

from csv_snapshot.config import AppConfig
from csv_snapshot.profiling import profile_csv
from csv_snapshot.serialization import json_text


def generate_csv(path: Path, target_bytes: int) -> int:
    row_count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("id,group,amount,active,event_date,note\n")
        while handle.tell() < target_bytes:
            index = row_count + 1
            handle.write(
                f"ID{index:09d},G{index % 97:02d},{(index % 10000) / 10:.1f},"
                f"{'true' if index % 2 else 'false'},2026-07-{(index % 28) + 1:02d},"
                f"synthetic-row-{index:09d}\n"
            )
            row_count += 1
    return row_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--megabytes", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="csv-snapshot-benchmark-") as directory:
        csv_path = Path(directory) / "synthetic.csv"
        rows = generate_csv(csv_path, args.megabytes * 1024 * 1024)
        started = time.perf_counter()
        snapshot = profile_csv(csv_path, AppConfig())
        elapsed = time.perf_counter() - started
        snapshot_text = json_text(snapshot)
        peak_kib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result = {
            "requestedMegabytes": args.megabytes,
            "fileSizeBytes": csv_path.stat().st_size,
            "rowCount": rows,
            "elapsedSeconds": round(elapsed, 6),
            "peakRssKiB": peak_kib,
            "snapshotSizeBytes": len(snapshot_text.encode("utf-8")),
        }
        text = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        print(text, end="")


if __name__ == "__main__":
    main()
