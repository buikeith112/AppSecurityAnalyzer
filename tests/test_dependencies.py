"""Simple verification script for dependency analysis."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scanner.modules.dependencies import analyze_dependencies
from scanner.utils.file_loader import load_text_files


def test_analyze_requirements_file() -> None:
    """Verify missing and stale sample dependencies are flagged."""
    sample_project = PROJECT_ROOT / "tests" / "fixtures" / "sample_project"
    loaded_files = load_text_files(sample_project)
    warnings = analyze_dependencies(loaded_files)
    warning_names = {warning.dependency_name for warning in warnings}

    assert "requests" in warning_names
    assert "flask" in warning_names
    assert "internal-lib" in warning_names
    assert "lodash" in warning_names
    assert "axios" in warning_names
    assert "pytest" not in warning_names
    assert "react" not in warning_names


if __name__ == "__main__":
    test_analyze_requirements_file()
    print("Dependency analysis test passed.")
