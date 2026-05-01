"""Command line interface for the security scanner."""

from __future__ import annotations

import argparse
from pathlib import Path

from scanner.modules.secrets import SecretFinding, detect_secrets
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
    return parser


def run(project_path: Path) -> int:
    """Load project files, run secret detection, and print a readable summary."""
    loaded_files = load_text_files(project_path)
    findings = detect_secrets(loaded_files)

    print(f"Total files found: {len(loaded_files)}")
    print("First 5 files:")

    for file_path in list(loaded_files.keys())[:5]:
        print(f"- {file_path}")

    print_findings(findings)

    return 0


def print_findings(findings: list[SecretFinding]) -> None:
    """Print secret findings in a compact human-readable format."""
    print(f"\nSecrets found: {len(findings)}")

    if not findings:
        return

    for finding in findings:
        print(
            f"- {finding.secret_type} in {finding.file_name}:"
            f"{finding.line_number} -> {finding.matched_string}"
        )


def main() -> int:
    """Parse command line arguments and execute the scanner CLI."""
    parser = build_parser()
    args = parser.parse_args()

    return run(args.project_path)


if __name__ == "__main__":
    raise SystemExit(main())
