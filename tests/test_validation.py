"""Simple verification script for input validation heuristics."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scanner.modules.validation import analyze_validation
from scanner.utils.file_loader import load_text_files


def test_analyze_validation() -> None:
    """Verify vulnerable-looking functions are flagged and checked ones are not."""
    sample_project = PROJECT_ROOT / "tests" / "fixtures" / "validation_project"
    loaded_files = load_text_files(sample_project)
    findings = analyze_validation(loaded_files)
    finding_names = {finding.function_name for finding in findings}

    assert "login" in finding_names
    assert "process_payload" in finding_names
    assert "get_user" not in finding_names
    assert "process_checked_input" not in finding_names


if __name__ == "__main__":
    test_analyze_validation()
    print("Validation analysis test passed.")
