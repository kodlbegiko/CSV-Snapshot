"""Pydantic data models for snapshots and reports."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Severity = Literal["error", "warning", "info"]
InferredType = Literal[
    "integer", "float", "boolean", "date", "datetime", "string", "null", "mixed"
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SourceInfo(StrictModel):
    file_name: str = Field(alias="fileName")
    file_size_bytes: int = Field(alias="fileSizeBytes", ge=0)
    content_hash: str = Field(alias="contentHash")


class CsvInfo(StrictModel):
    delimiter: str
    has_header: bool = Field(alias="hasHeader")
    encoding: str
    row_count: int = Field(alias="rowCount", ge=0)
    column_count: int = Field(alias="columnCount", ge=0)

    @field_validator("delimiter")
    @classmethod
    def delimiter_is_one_character(cls, value: str) -> str:
        if len(value) != 1:
            raise ValueError("delimiter must be exactly one character")
        return value


class NumericMetrics(StrictModel):
    min: float | int | None = None
    max: float | int | None = None
    mean: float | None = None
    standard_deviation: float | None = Field(default=None, alias="standardDeviation")
    zero_count: int = Field(default=0, alias="zeroCount", ge=0)
    negative_count: int = Field(default=0, alias="negativeCount", ge=0)


class StringMetrics(StrictModel):
    min_length: int | None = Field(default=None, alias="minLength", ge=0)
    max_length: int | None = Field(default=None, alias="maxLength", ge=0)
    mean_length: float | None = Field(default=None, alias="meanLength")
    empty_string_count: int = Field(default=0, alias="emptyStringCount", ge=0)
    empty_string_rate: float = Field(default=0.0, alias="emptyStringRate", ge=0, le=1)


class BooleanMetrics(StrictModel):
    true_count: int = Field(alias="trueCount", ge=0)
    false_count: int = Field(alias="falseCount", ge=0)


class TemporalMetrics(StrictModel):
    earliest: str | None = None
    latest: str | None = None
    parse_success_rate: float = Field(alias="parseSuccessRate", ge=0, le=1)


class ColumnProfile(StrictModel):
    name: str
    position: int = Field(ge=0)
    inferred_type: InferredType = Field(alias="inferredType")
    nullable: bool
    null_count: int = Field(alias="nullCount", ge=0)
    null_rate: float = Field(alias="nullRate", ge=0, le=1)
    non_null_count: int = Field(alias="nonNullCount", ge=0)
    distinct_count: int = Field(alias="distinctCount", ge=0)
    metrics: NumericMetrics | StringMetrics | BooleanMetrics | TemporalMetrics | None = None


class Snapshot(StrictModel):
    snapshot_schema_version: Literal["1"] = Field(alias="snapshotSchemaVersion")
    tool_version: str = Field(alias="toolVersion")
    source: SourceInfo
    csv: CsvInfo
    columns: list[ColumnProfile]


class Finding(StrictModel):
    rule_id: str = Field(alias="ruleId")
    severity: Severity
    message: str
    column: str | None = None
    baseline: Any | None = None
    current: Any | None = None
    difference: Any | None = None
    threshold: Any | None = None
    suggestion: str | None = None


class ReportSummary(StrictModel):
    error_count: int = Field(alias="errorCount", ge=0)
    warning_count: int = Field(alias="warningCount", ge=0)
    info_count: int = Field(alias="infoCount", ge=0)
    finding_count: int = Field(alias="findingCount", ge=0)


class ComparisonReport(StrictModel):
    report_schema_version: Literal["1"] = Field(alias="reportSchemaVersion")
    tool_version: str = Field(alias="toolVersion")
    passed: bool
    baseline_snapshot: str = Field(alias="baselineSnapshot")
    current_file: str = Field(alias="currentFile")
    summary: ReportSummary
    findings: list[Finding]
