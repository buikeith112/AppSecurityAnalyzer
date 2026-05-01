"""Command line interface for the security scanner."""

from __future__ import annotations

import argparse
from pathlib import Path

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
    """Load project files and print a short summary for the user."""
    loaded_files = load_text_files(project_path)

    print(f"Total files found: {len(loaded_files)}")
    print("First 5 files:")

    for file_path in list(loaded_files.keys())[:5]:
        print(f"- {file_path}")

    return 0


def main() -> int:
    """Parse command line arguments and execute the scanner CLI."""
    parser = build_parser()
    args = parser.parse_args()

    return run(args.project_path)


if __name__ == "__main__":
    raise SystemExit(main())
