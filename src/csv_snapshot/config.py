"""Safe TOML configuration loading and validation."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .errors import ConfigurationError
from .models import Severity


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SnapshotConfig(ConfigModel):
    delimiter: str = ","
    encoding: Literal["utf-8", "utf-8-sig"] = "utf-8"
    hash_algorithm: Literal["sha256"] = "sha256"
    null_values: list[str] = Field(default_factory=lambda: ["NULL", "null", "NA", "N/A"])

    @model_validator(mode="after")
    def validate_delimiter(self) -> "SnapshotConfig":
        if len(self.delimiter) != 1:
            raise ValueError("delimiter must be exactly one character")
        return self


class ComparisonConfig(ConfigModel):
    column_order: Severity = "warning"
    new_columns: Severity = "warning"
    removed_columns: Severity = "error"
    type_changes: Severity = "error"
    nullable_changes: Severity = "warning"


class ThresholdConfig(ConfigModel):
    row_count_relative_change: float = Field(default=0.20, ge=0)
    null_rate_absolute_change: float = Field(default=0.05, ge=0, le=1)
    numeric_mean_relative_change: float = Field(default=0.20, ge=0)
    distinct_count_relative_change: float = Field(default=0.30, ge=0)


class ColumnRule(ConfigModel):
    type: Literal[
        "integer", "float", "boolean", "date", "datetime", "string", "null", "mixed"
    ] | None = None
    nullable: bool | None = None
    min: float | None = None
    max: float | None = None
    max_null_rate: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_bounds(self) -> "ColumnRule":
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must not be greater than max")
        return self


class AppConfig(ConfigModel):
    snapshot: SnapshotConfig = Field(default_factory=SnapshotConfig)
    comparison: ComparisonConfig = Field(default_factory=ComparisonConfig)
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    columns: dict[str, ColumnRule] = Field(default_factory=dict)


DEFAULT_CONFIG = """[snapshot]
delimiter = ","
encoding = "utf-8"
hash_algorithm = "sha256"
null_values = ["NULL", "null", "NA", "N/A"]

[comparison]
column_order = "warning"
new_columns = "warning"
removed_columns = "error"
type_changes = "error"
nullable_changes = "warning"

[thresholds]
row_count_relative_change = 0.20
null_rate_absolute_change = 0.05
numeric_mean_relative_change = 0.20
distinct_count_relative_change = 0.30

# Per-column rules are optional.
# [columns.id]
# type = "string"
# nullable = false
"""


def load_config(path: Path | None) -> AppConfig:
    if path is None:
        return AppConfig()
    try:
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
        return AppConfig.model_validate(payload)
    except FileNotFoundError as exc:
        raise ConfigurationError(f"configuration file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"invalid TOML in {path}: {exc}") from exc
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise ConfigurationError(f"invalid configuration: {details}") from exc


def discover_config(start: Path) -> Path | None:
    candidate = start / "csv-snapshot.toml"
    return candidate if candidate.exists() else None
