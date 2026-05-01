"""Simple verification script for the file loader utility."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scanner.utils.file_loader import load_text_files


def test_load_text_files() -> None:
    """Verify text files are loaded and ignored directories are skipped."""
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        included_file = root / "app.py"
        ignored_file = root / ".git" / "config"

        included_file.write_text("print('hello')", encoding="utf-8")
        ignored_file.parent.mkdir()
        ignored_file.write_text("ignored", encoding="utf-8")

        loaded_files = load_text_files(root)

        assert str(included_file.resolve()) in loaded_files
        assert str(ignored_file.resolve()) not in loaded_files
        assert loaded_files[str(included_file.resolve())] == "print('hello')"


if __name__ == "__main__":
    test_load_text_files()
    print("File loader test passed.")
