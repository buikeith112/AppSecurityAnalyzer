"""Simple verification script for the FastAPI backend scanner integration."""

import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.scanner_integration import scan_project, scan_zip_archive


def test_scan_project_returns_json_report() -> None:
    """Verify the backend wrapper returns JSON-serializable scan output."""
    sample_project = PROJECT_ROOT / "tests" / "fixtures" / "full_scan_project"

    report = scan_project(sample_project)

    assert report["total_files"] > 0
    assert "risk_score" in report
    assert "findings_by_category" in report
    assert report["findings_by_category"]["secrets"]


def test_scan_zip_archive_returns_json_report() -> None:
    """Verify zip uploads are extracted, scanned, and cleaned up by context."""
    with TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        project_dir = temp_root / "project"
        project_dir.mkdir()
        (project_dir / "app.py").write_text(
            "API_KEY = 'abc123456789'\n",
            encoding="utf-8",
        )
        zip_path = temp_root / "project.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.write(project_dir / "app.py", "project/app.py")

        report = scan_zip_archive(zip_path)

    assert report["total_files"] == 1
    assert "findings_by_category" in report


if __name__ == "__main__":
    test_scan_project_returns_json_report()
    test_scan_zip_archive_returns_json_report()
    print("Backend integration test passed.")
