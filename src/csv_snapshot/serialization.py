"""Deterministic JSON serialization and atomic file writes."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .errors import OutputError, SnapshotError
from .models import ComparisonReport, Snapshot


def json_text(value: Snapshot | ComparisonReport | dict[str, Any]) -> str:
    if hasattr(value, "model_dump"):
        payload = value.model_dump(by_alias=True, exclude_none=True)
    else:
        payload = value
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    )


def atomic_write_text(path: Path, content: str, *, force: bool = False) -> None:
    path = path.expanduser()
    if path.exists() and not force:
        raise OutputError(f"output already exists; use --force to replace it: {path}")
    if path.is_symlink():
        raise OutputError(f"refusing to write through a symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except OSError as exc:
        with contextlib.suppress(OSError):
            os.unlink(temporary_name)
        raise OutputError(f"unable to write output: {path}") from exc


def write_snapshot(snapshot: Snapshot, path: Path, *, force: bool = False) -> None:
    atomic_write_text(path, json_text(snapshot), force=force)


def load_snapshot(path: Path) -> Snapshot:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Snapshot.model_validate(payload)
    except FileNotFoundError as exc:
        raise SnapshotError(f"snapshot not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"snapshot is not valid JSON: {path}: {exc}") from exc
    except ValidationError as exc:
        raise SnapshotError(f"snapshot schema validation failed: {exc}") from exc
