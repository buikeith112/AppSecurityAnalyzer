"""Simple verification script for aggregate report generation."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scanner.core.report import build_report, render_cli_report
from scanner.modules.dependencies import analyze_dependencies
from scanner.modules.rate_limit import analyze_rate_limits
from scanner.modules.secrets import detect_secrets
from scanner.modules.sensitive_data import detect_sensitive_data
from scanner.modules.validation import analyze_validation
from scanner.utils.file_loader import load_text_files


def test_build_report() -> None:
    """Verify all scanner outputs are grouped into one scored report."""
    sample_project = PROJECT_ROOT / "tests" / "fixtures" / "full_scan_project"
    loaded_files = load_text_files(sample_project)
    report = build_report(
        project_path=sample_project,
        loaded_files=loaded_files,
        secret_findings=detect_secrets(loaded_files),
        dependency_warnings=analyze_dependencies(loaded_files),
        validation_findings=analyze_validation(loaded_files),
        rate_limit_findings=analyze_rate_limits(loaded_files),
        sensitive_data_findings=detect_sensitive_data(loaded_files),
    )
    rendered = render_cli_report(report)

    assert 0 <= report.risk_score <= 100
    assert report.findings_by_category["secrets"]
    assert report.findings_by_category["dependencies"]
    assert report.findings_by_category["validation"]
    assert report.findings_by_category["rate_limit"]
    assert report.findings_by_category["sensitive_data"]
    assert "Security Scan Report" in rendered


if __name__ == "__main__":
    test_build_report()
    print("Report generation test passed.")
