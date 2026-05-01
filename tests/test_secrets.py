"""Simple verification script for hardcoded secret detection."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scanner.modules.secrets import detect_secrets
from scanner.utils.file_loader import load_text_files


def test_detect_secrets() -> None:
    """Verify fake AWS, OpenAI, and generic API keys are detected."""
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        fixture = root / "settings.py"
        fixture.write_text(
            "\n".join(
                [
                    "AWS_ACCESS_KEY_ID = 'AKIA1234567890ABCDEF'",
                    "OPENAI_API_KEY = 'sk-abcdefghijklmnopqrstuvwxyz123456'",
                    "API_KEY = 'abcDEF1234567890abcDEF1234567890'",
                    "NORMAL_VALUE = 'this-should-not-match'",
                ]
            ),
            encoding="utf-8",
        )

        loaded_files = load_text_files(root)
        findings = detect_secrets(loaded_files)
        finding_types = {finding.secret_type for finding in findings}

        assert "AWS Access Key ID" in finding_types
        assert "OpenAI API Key" in finding_types
        assert "Generic API Key" in finding_types
        assert all("..." in finding.matched_string for finding in findings)


if __name__ == "__main__":
    test_detect_secrets()
    print("Secret detection test passed.")
