"""Deterministic snapshot comparison and quality rule evaluation."""

from __future__ import annotations

from typing import Any

from .config import AppConfig, ColumnRule
from .models import (
    ColumnProfile,
    ComparisonReport,
    Finding,
    NumericMetrics,
    ReportSummary,
    Snapshot,
    StringMetrics,
    TemporalMetrics,
    Severity,
)
from .version import __version__

_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def _relative_change(baseline: float | int, current: float | int) -> float | None:
    if baseline == 0:
        return 0.0 if current == 0 else None
    return round(abs(current - baseline) / abs(baseline), 12)


def _finding(
    rule_id: str,
    severity: Severity,
    message: str,
    *,
    column: str | None = None,
    baseline: Any = None,
    current: Any = None,
    difference: Any = None,
    threshold: Any = None,
    suggestion: str | None = None,
) -> Finding:
    return Finding(
        ruleId=rule_id,
        severity=severity,
        message=message,
        column=column,
        baseline=baseline,
        current=current,
        difference=difference,
        threshold=threshold,
        suggestion=suggestion,
    )


def compare_snapshots(
    baseline: Snapshot,
    current: Snapshot,
    config: AppConfig,
    *,
    baseline_name: str = "baseline snapshot",
    current_name: str = "current CSV",
) -> ComparisonReport:
    findings: list[Finding] = []
    baseline_by_name = {column.name: column for column in baseline.columns}
    current_by_name = {column.name: column for column in current.columns}

    for name in sorted(current_by_name.keys() - baseline_by_name.keys()):
        findings.append(
            _finding(
                "schema.column_added",
                config.comparison.new_columns,
                f"Column '{name}' was added.",
                column=name,
                current=current_by_name[name].position,
                suggestion="Review downstream consumers and commit a new baseline if intentional.",
            )
        )
    for name in sorted(baseline_by_name.keys() - current_by_name.keys()):
        findings.append(
            _finding(
                "schema.column_removed",
                config.comparison.removed_columns,
                f"Column '{name}' was removed.",
                column=name,
                baseline=baseline_by_name[name].position,
                suggestion="Restore the column or update consumers before accepting the change.",
            )
        )

    common_names = sorted(baseline_by_name.keys() & current_by_name.keys())
    baseline_order = [column.name for column in baseline.columns if column.name in common_names]
    current_order = [column.name for column in current.columns if column.name in common_names]
    if baseline_order != current_order:
        findings.append(
            _finding(
                "schema.column_order_changed",
                config.comparison.column_order,
                "Column order changed.",
                baseline=baseline_order,
                current=current_order,
                suggestion="Confirm positional CSV consumers do not rely on the previous order.",
            )
        )

    for name in common_names:
        before = baseline_by_name[name]
        after = current_by_name[name]
        if before.inferred_type != after.inferred_type:
            findings.append(
                _finding(
                    "schema.type_changed",
                    config.comparison.type_changes,
                    (
                        f"Column '{name}' changed type from {before.inferred_type} "
                        f"to {after.inferred_type}."
                    ),
                    column=name,
                    baseline=before.inferred_type,
                    current=after.inferred_type,
                    suggestion="Inspect source formatting or configure the intended column type.",
                )
            )
        if before.nullable != after.nullable:
            findings.append(
                _finding(
                    "schema.nullable_changed",
                    config.comparison.nullable_changes,
                    f"Column '{name}' nullable state changed.",
                    column=name,
                    baseline=before.nullable,
                    current=after.nullable,
                    suggestion="Confirm whether missing values are now expected.",
                )
            )
        findings.extend(_compare_column_metrics(before, after, config))

    findings.extend(_compare_volume(baseline, current, config))
    findings.extend(_evaluate_column_rules(current, config))
    findings.sort(
        key=lambda item: (
            _SEVERITY_ORDER[item.severity],
            item.column or "",
            item.rule_id,
            item.message,
        )
    )
    summary = ReportSummary(
        errorCount=sum(item.severity == "error" for item in findings),
        warningCount=sum(item.severity == "warning" for item in findings),
        infoCount=sum(item.severity == "info" for item in findings),
        findingCount=len(findings),
    )
    return ComparisonReport(
        reportSchemaVersion="1",
        toolVersion=__version__,
        passed=summary.error_count == 0,
        baselineSnapshot=baseline_name,
        currentFile=current_name,
        summary=summary,
        findings=findings,
    )


def _compare_volume(baseline: Snapshot, current: Snapshot, config: AppConfig) -> list[Finding]:
    findings: list[Finding] = []
    before = baseline.csv.row_count
    after = current.csv.row_count
    if before != after:
        relative = _relative_change(before, after)
        if relative is None or relative > config.thresholds.row_count_relative_change:
            findings.append(
                _finding(
                    "volume.row_count_changed",
                    "warning",
                    f"Row count changed from {before} to {after}.",
                    baseline=before,
                    current=after,
                    difference=relative if relative is not None else "from-zero",
                    threshold=config.thresholds.row_count_relative_change,
                    suggestion="Verify the export window, filters, and upstream completeness.",
                )
            )
    if current.csv.column_count == 0 and current.csv.row_count == 0:
        findings.append(
            _finding(
                "volume.empty_file",
                "error",
                "The current CSV is empty.",
                baseline=baseline.csv.row_count,
                current=0,
                suggestion="Restore a valid header and data export.",
            )
        )
    elif current.csv.row_count == 0:
        findings.append(
            _finding(
                "volume.header_only",
                "warning",
                "The current CSV contains a header but no data rows.",
                baseline=baseline.csv.row_count,
                current=0,
                suggestion="Confirm whether an empty result is expected.",
            )
        )
    return findings


def _compare_column_metrics(
    before: ColumnProfile, after: ColumnProfile, config: AppConfig
) -> list[Finding]:
    findings: list[Finding] = []
    null_change = round(after.null_rate - before.null_rate, 12)
    if null_change > config.thresholds.null_rate_absolute_change:
        findings.append(
            _finding(
                "missingness.null_rate_increased",
                "error",
                f"Column '{before.name}' null rate increased.",
                column=before.name,
                baseline=before.null_rate,
                current=after.null_rate,
                difference=null_change,
                threshold=config.thresholds.null_rate_absolute_change,
                suggestion="Inspect upstream joins, mappings, and required-field validation.",
            )
        )

    if isinstance(before.metrics, NumericMetrics) and isinstance(after.metrics, NumericMetrics):
        findings.extend(_compare_numeric(before, after, config))
    if isinstance(before.metrics, StringMetrics) and isinstance(after.metrics, StringMetrics):
        findings.extend(_compare_string(before, after, config))
    if isinstance(before.metrics, TemporalMetrics) and isinstance(after.metrics, TemporalMetrics):
        if before.metrics.earliest != after.metrics.earliest:
            findings.append(
                _finding(
                    "date.earliest_changed",
                    "info",
                    f"Column '{before.name}' earliest value changed.",
                    column=before.name,
                    baseline=before.metrics.earliest,
                    current=after.metrics.earliest,
                )
            )
        if before.metrics.latest != after.metrics.latest:
            findings.append(
                _finding(
                    "date.latest_changed",
                    "info",
                    f"Column '{before.name}' latest value changed.",
                    column=before.name,
                    baseline=before.metrics.latest,
                    current=after.metrics.latest,
                )
            )
    return findings


def _compare_numeric(
    before: ColumnProfile, after: ColumnProfile, config: AppConfig
) -> list[Finding]:
    assert isinstance(before.metrics, NumericMetrics)
    assert isinstance(after.metrics, NumericMetrics)
    findings: list[Finding] = []
    for metric in ("min", "max"):
        old = getattr(before.metrics, metric)
        new = getattr(after.metrics, metric)
        if old != new:
            findings.append(
                _finding(
                    f"numeric.{metric}_changed",
                    "warning",
                    f"Column '{before.name}' numeric {metric} changed.",
                    column=before.name,
                    baseline=old,
                    current=new,
                    difference=(new - old) if old is not None and new is not None else None,
                    suggestion="Confirm the new range is valid for this field.",
                )
            )
    if before.metrics.mean is not None and after.metrics.mean is not None:
        relative = _relative_change(before.metrics.mean, after.metrics.mean)
        if relative is None or relative > config.thresholds.numeric_mean_relative_change:
            findings.append(
                _finding(
                    "numeric.mean_changed",
                    "warning",
                    f"Column '{before.name}' mean changed materially.",
                    column=before.name,
                    baseline=before.metrics.mean,
                    current=after.metrics.mean,
                    difference=relative if relative is not None else "from-zero",
                    threshold=config.thresholds.numeric_mean_relative_change,
                    suggestion="Inspect distribution shifts and upstream calculation changes.",
                )
            )
    if before.metrics.negative_count == 0 and after.metrics.negative_count > 0:
        findings.append(
            _finding(
                "numeric.negative_values_appeared",
                "error",
                f"Column '{before.name}' now contains negative values.",
                column=before.name,
                baseline=0,
                current=after.metrics.negative_count,
                suggestion="Confirm whether negative values are valid for this field.",
            )
        )
    return findings


def _compare_string(
    before: ColumnProfile, after: ColumnProfile, config: AppConfig
) -> list[Finding]:
    assert isinstance(before.metrics, StringMetrics)
    assert isinstance(after.metrics, StringMetrics)
    findings: list[Finding] = []
    metric_rules = (
        ("min_length", "string.min_length_changed"),
        ("max_length", "string.max_length_changed"),
    )
    for metric, rule in metric_rules:
        old = getattr(before.metrics, metric)
        new = getattr(after.metrics, metric)
        if old != new:
            findings.append(
                _finding(
                    rule,
                    "warning",
                    f"Column '{before.name}' {metric.replace('_', ' ')} changed.",
                    column=before.name,
                    baseline=old,
                    current=new,
                    suggestion="Review truncation, formatting, or identifier changes.",
                )
            )
    relative = _relative_change(before.distinct_count, after.distinct_count)
    if relative is None or relative > config.thresholds.distinct_count_relative_change:
        findings.append(
            _finding(
                "string.distinct_count_changed",
                "warning",
                f"Column '{before.name}' distinct count changed materially.",
                column=before.name,
                baseline=before.distinct_count,
                current=after.distinct_count,
                difference=relative if relative is not None else "from-zero",
                threshold=config.thresholds.distinct_count_relative_change,
                suggestion="Check category mappings and source population changes.",
            )
        )
    return findings


def _evaluate_column_rules(current: Snapshot, config: AppConfig) -> list[Finding]:
    current_by_name = {column.name: column for column in current.columns}
    findings: list[Finding] = []
    for name, rule in sorted(config.columns.items()):
        column = current_by_name.get(name)
        if column is None:
            continue
        findings.extend(_evaluate_rule(name, column, rule))
    return findings


def _evaluate_rule(name: str, column: ColumnProfile, rule: ColumnRule) -> list[Finding]:
    findings: list[Finding] = []
    if rule.type is not None and column.inferred_type != rule.type:
        findings.append(
            _finding(
                "quality.expected_type",
                "error",
                f"Column '{name}' does not match configured type {rule.type}.",
                column=name,
                baseline=rule.type,
                current=column.inferred_type,
                suggestion="Correct the source values or update the configured contract.",
            )
        )
    if rule.nullable is False and column.nullable:
        findings.append(
            _finding(
                "quality.not_nullable",
                "error",
                f"Column '{name}' contains configured null values.",
                column=name,
                baseline=False,
                current=True,
                suggestion="Populate the required values before publishing the CSV.",
            )
        )
    if rule.max_null_rate is not None and column.null_rate > rule.max_null_rate:
        findings.append(
            _finding(
                "quality.max_null_rate",
                "error",
                f"Column '{name}' exceeds its maximum null rate.",
                column=name,
                baseline=rule.max_null_rate,
                current=column.null_rate,
                difference=round(column.null_rate - rule.max_null_rate, 12),
                threshold=rule.max_null_rate,
                suggestion="Repair missing values or revise the explicit data contract.",
            )
        )
    if isinstance(column.metrics, NumericMetrics):
        if (
            rule.min is not None
            and column.metrics.min is not None
            and column.metrics.min < rule.min
        ):
            findings.append(
                _finding(
                    "quality.minimum",
                    "error",
                    f"Column '{name}' is below its configured minimum.",
                    column=name,
                    baseline=rule.min,
                    current=column.metrics.min,
                    suggestion="Validate the out-of-range records upstream.",
                )
            )
        if (
            rule.max is not None
            and column.metrics.max is not None
            and column.metrics.max > rule.max
        ):
            findings.append(
                _finding(
                    "quality.maximum",
                    "error",
                    f"Column '{name}' exceeds its configured maximum.",
                    column=name,
                    baseline=rule.max,
                    current=column.metrics.max,
                    suggestion="Validate the out-of-range records upstream.",
                )
            )
    return findings
