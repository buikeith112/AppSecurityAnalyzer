"""Simple verification script for sensitive data detection."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scanner.modules.sensitive_data import detect_sensitive_data
from scanner.utils.file_loader import load_text_files


def test_detect_sensitive_data() -> None:
    """Verify fake emails, SSNs, and phone numbers are detected and masked."""
    sample_project = PROJECT_ROOT / "tests" / "fixtures" / "sensitive_data_project"
    loaded_files = load_text_files(sample_project)
    findings = detect_sensitive_data(loaded_files)
    finding_types = {finding.data_type for finding in findings}

    assert "Email Address" in finding_types
    assert "Social Security Number" in finding_types
    assert "Phone Number" in finding_types
    assert all("alex.fake@example.com" != finding.matched_value for finding in findings)
    assert all("123-45-6789" != finding.matched_value for finding in findings)


if __name__ == "__main__":
    test_detect_sensitive_data()
    print("Sensitive data detection test passed.")
