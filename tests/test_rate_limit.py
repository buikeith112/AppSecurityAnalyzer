"""Simple verification script for rate limiting heuristics."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scanner.modules.rate_limit import analyze_rate_limits
from scanner.utils.file_loader import load_text_files


def test_analyze_rate_limits() -> None:
    """Verify API routes without limiter signals are flagged."""
    sample_project = PROJECT_ROOT / "tests" / "fixtures" / "rate_limit_project"
    loaded_files = load_text_files(sample_project)
    findings = analyze_rate_limits(loaded_files)
    endpoints = {finding.endpoint for finding in findings}

    assert "ROUTE /login" in endpoints
    assert "GET /status" in endpoints
    assert "POST /api/login" in endpoints
    assert "GET /api/status" in endpoints


if __name__ == "__main__":
    test_analyze_rate_limits()
    print("Rate limiting analysis test passed.")
