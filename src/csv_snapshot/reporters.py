"""Terminal, JSON, and Markdown reporters over one comparison model."""

from __future__ import annotations

from .models import ComparisonReport
from .serialization import json_text


def render_terminal(report: ComparisonReport) -> str:
    status = "PASS" if report.passed else "FAIL"
    lines = [
        f"CSV Snapshot: {status}",
        f"Findings: {report.summary.error_count} error(s), "
        f"{report.summary.warning_count} warning(s), {report.summary.info_count} info",
    ]
    for finding in report.findings:
        location = f" [{finding.column}]" if finding.column else ""
        lines.append(f"- {finding.severity.upper()} {finding.rule_id}{location}: {finding.message}")
        if finding.suggestion:
            lines.append(f"  Suggestion: {finding.suggestion}")
    return "\n".join(lines) + "\n"


def render_markdown(report: ComparisonReport) -> str:
    status = "PASS" if report.passed else "FAIL"
    lines = [
        "# CSV Snapshot Report",
        "",
        f"**Status:** {status}",
        "",
        f"- Errors: {report.summary.error_count}",
        f"- Warnings: {report.summary.warning_count}",
        f"- Info: {report.summary.info_count}",
        "",
        "## Findings",
        "",
    ]
    if not report.findings:
        lines.append("No drift findings.")
    else:
        lines.extend(
            [
                "| Severity | Rule | Column | Message |",
                "|---|---|---|---|",
            ]
        )
        for finding in report.findings:
            message = finding.message.replace("|", "\\|")
            lines.append(
                f"| {finding.severity} | `{finding.rule_id}` | "
                f"{finding.column or '—'} | {message} |"
            )
            if finding.suggestion:
                lines.append(f"\n**Suggestion ({finding.rule_id}):** {finding.suggestion}\n")
    return "\n".join(lines).rstrip() + "\n"


def render_report(report: ComparisonReport, output_format: str) -> str:
    if output_format == "terminal":
        return render_terminal(report)
    if output_format == "json":
        return json_text(report)
    if output_format == "markdown":
        return render_markdown(report)
    raise ValueError(f"unsupported report format: {output_format}")
