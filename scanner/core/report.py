"""Report aggregation, scoring, and rendering for scan results."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scanner.modules.dependencies import DependencyWarning
from scanner.modules.llm_analysis import LLMFileAnalysis
from scanner.modules.rate_limit import RateLimitFinding
from scanner.modules.secrets import SecretFinding
from scanner.modules.sensitive_data import SensitiveDataFinding
from scanner.modules.validation import ValidationFinding


CATEGORY_WEIGHTS = {
    "secrets": 25,
    "sensitive_data": 15,
    "validation": 10,
    "rate_limit": 8,
    "dependencies": 6,
    "llm_analysis": 4,
}


@dataclass(frozen=True)
class ReportFinding:
    """A normalized finding used by the final report."""

    category: str
    title: str
    file_name: str
    line_number: int | None
    detail: str
    evidence: str


@dataclass(frozen=True)
class ScanReport:
    """The complete scanner report shown in CLI and JSON output."""

    project_path: str
    total_files: int
    first_files: list[str]
    risk_score: int
    findings_by_category: dict[str, list[ReportFinding]]


def build_report(
    project_path: Path,
    loaded_files: dict[str, str],
    secret_findings: list[SecretFinding],
    dependency_warnings: list[DependencyWarning],
    validation_findings: list[ValidationFinding],
    rate_limit_findings: list[RateLimitFinding],
    sensitive_data_findings: list[SensitiveDataFinding],
    llm_analyses: list[LLMFileAnalysis] | None = None,
) -> ScanReport:
    """Aggregate module outputs into one scored report."""
    findings_by_category = {
        "secrets": normalize_secret_findings(secret_findings),
        "dependencies": normalize_dependency_warnings(dependency_warnings),
        "validation": normalize_validation_findings(validation_findings),
        "rate_limit": normalize_rate_limit_findings(rate_limit_findings),
        "sensitive_data": normalize_sensitive_data_findings(sensitive_data_findings),
    }
    if llm_analyses is not None:
        findings_by_category["llm_analysis"] = normalize_llm_analyses(llm_analyses)

    return ScanReport(
        project_path=str(project_path),
        total_files=len(loaded_files),
        first_files=list(loaded_files.keys())[:5],
        risk_score=calculate_risk_score(findings_by_category),
        findings_by_category=findings_by_category,
    )


def calculate_risk_score(
    findings_by_category: dict[str, list[ReportFinding]]
) -> int:
    """Calculate a capped 0-100 risk score from categorized findings."""
    score = 0

    for category, findings in findings_by_category.items():
        score += len(findings) * CATEGORY_WEIGHTS.get(category, 5)

    return min(score, 100)


def render_cli_report(report: ScanReport) -> str:
    """Render a clean human-readable CLI report."""
    lines = [
        "Security Scan Report",
        f"Project: {report.project_path}",
        f"Risk score: {report.risk_score}/100",
        f"Total files scanned: {report.total_files}",
        "",
        "First 5 files:",
    ]

    lines.extend(format_first_files(report.first_files))
    lines.append("")

    for category, findings in report.findings_by_category.items():
        lines.extend(render_category(category, findings))
        lines.append("")

    return "\n".join(lines).rstrip()


def export_report_json(report: ScanReport, output_path: Path) -> None:
    """Write the report to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report_to_dict(report), indent=2),
        encoding="utf-8",
    )


def report_to_dict(report: ScanReport) -> dict[str, Any]:
    """Convert a report dataclass into JSON-serializable dictionaries."""
    return {
        "project_path": report.project_path,
        "total_files": report.total_files,
        "first_files": report.first_files,
        "risk_score": report.risk_score,
        "findings_by_category": {
            category: [asdict(finding) for finding in findings]
            for category, findings in report.findings_by_category.items()
        },
    }


def render_category(category: str, findings: list[ReportFinding]) -> list[str]:
    """Render one report category with its findings."""
    label = format_category_label(category)
    lines = [f"{label}: {len(findings)}"]

    if not findings:
        lines.append("- None")
        return lines

    for finding in findings:
        location = format_location(finding.file_name, finding.line_number)
        lines.append(f"- {finding.title} in {location}")
        lines.append(f"  Detail: {finding.detail}")
        lines.append(f"  Evidence: {finding.evidence}")

    return lines


def format_first_files(first_files: list[str]) -> list[str]:
    """Format the first scanned files section."""
    if not first_files:
        return ["- None"]

    return [f"- {file_name}" for file_name in first_files]


def format_category_label(category: str) -> str:
    """Convert a category key into a display label."""
    if category == "llm_analysis":
        return "LLM Analysis"

    return category.replace("_", " ").title()


def format_location(file_name: str, line_number: int | None) -> str:
    """Format a file location with an optional line number."""
    if line_number is None:
        return file_name

    return f"{file_name}:{line_number}"


def normalize_secret_findings(findings: list[SecretFinding]) -> list[ReportFinding]:
    """Normalize secret scanner findings for the report."""
    return [
        ReportFinding(
            category="secrets",
            title=finding.secret_type,
            file_name=finding.file_name,
            line_number=finding.line_number,
            detail="Potential hardcoded secret detected.",
            evidence=finding.matched_string,
        )
        for finding in findings
    ]


def normalize_dependency_warnings(
    warnings: list[DependencyWarning],
) -> list[ReportFinding]:
    """Normalize dependency warnings for the report."""
    report_findings: list[ReportFinding] = []

    for warning in warnings:
        version = warning.version if warning.version is not None else "unversioned"
        report_findings.append(
            ReportFinding(
                category="dependencies",
                title=warning.dependency_name,
                file_name=warning.file_name,
                line_number=warning.line_number,
                detail=warning.warning,
                evidence=version,
            )
        )

    return report_findings


def normalize_validation_findings(
    findings: list[ValidationFinding],
) -> list[ReportFinding]:
    """Normalize validation findings for the report."""
    return [
        ReportFinding(
            category="validation",
            title=finding.function_name,
            file_name=finding.file_name,
            line_number=finding.line_number,
            detail=finding.warning,
            evidence=finding.evidence,
        )
        for finding in findings
    ]


def normalize_rate_limit_findings(
    findings: list[RateLimitFinding],
) -> list[ReportFinding]:
    """Normalize rate limit findings for the report."""
    return [
        ReportFinding(
            category="rate_limit",
            title=finding.endpoint,
            file_name=finding.file_name,
            line_number=finding.line_number,
            detail=finding.warning,
            evidence=finding.framework,
        )
        for finding in findings
    ]


def normalize_sensitive_data_findings(
    findings: list[SensitiveDataFinding],
) -> list[ReportFinding]:
    """Normalize sensitive data findings for the report."""
    return [
        ReportFinding(
            category="sensitive_data",
            title=finding.data_type,
            file_name=finding.file_name,
            line_number=finding.line_number,
            detail="Sensitive data pattern detected.",
            evidence=finding.matched_value,
        )
        for finding in findings
    ]


def normalize_llm_analyses(analyses: list[LLMFileAnalysis]) -> list[ReportFinding]:
    """Normalize LLM analysis issues for the report."""
    report_findings: list[ReportFinding] = []

    for analysis in analyses:
        for issue in analysis.issues:
            report_findings.append(
                ReportFinding(
                    category="llm_analysis",
                    title=issue.title,
                    file_name=analysis.file,
                    line_number=None,
                    detail=f"Severity: {issue.severity}. {issue.explanation}",
                    evidence="LLM analysis",
                )
            )

    return report_findings
