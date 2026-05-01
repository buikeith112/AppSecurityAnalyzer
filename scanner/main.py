"""Command line interface for the security scanner."""

from __future__ import annotations

import argparse
from pathlib import Path

from scanner.core.report import (
    build_report,
    export_report_json,
    render_cli_report,
)
from scanner.modules.dependencies import analyze_dependencies
from scanner.modules.rate_limit import analyze_rate_limits
from scanner.modules.secrets import detect_secrets
from scanner.modules.sensitive_data import detect_sensitive_data
from scanner.modules.validation import analyze_validation
from scanner.utils.file_loader import load_text_files


def build_parser() -> argparse.ArgumentParser:
    """Create and configure the command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Load text files from a project directory for future scanning."
    )
    parser.add_argument(
        "project_path",
        type=Path,
        help="Path to the project directory to inspect.",
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        help="Optional path to write the full report as JSON.",
    )
    return parser


def run(project_path: Path, json_report_path: Path | None = None) -> int:
    """Load project files, run scanners, and print the aggregate report."""
    loaded_files = load_text_files(project_path)
    secret_findings = detect_secrets(loaded_files)
    dependency_warnings = analyze_dependencies(loaded_files)
    validation_findings = analyze_validation(loaded_files)
    rate_limit_findings = analyze_rate_limits(loaded_files)
    sensitive_data_findings = detect_sensitive_data(loaded_files)

    report = build_report(
        project_path=project_path,
        loaded_files=loaded_files,
        secret_findings=secret_findings,
        dependency_warnings=dependency_warnings,
        validation_findings=validation_findings,
        rate_limit_findings=rate_limit_findings,
        sensitive_data_findings=sensitive_data_findings,
    )

    print(render_cli_report(report))
    if json_report_path is not None:
        export_report_json(report, json_report_path)
        print(f"\nJSON report written to: {json_report_path}")

    return 0


def main() -> int:
    """Parse command line arguments and execute the scanner CLI."""
    parser = build_parser()
    args = parser.parse_args()

    return run(args.project_path, args.json_report)


if __name__ == "__main__":
    raise SystemExit(main())
