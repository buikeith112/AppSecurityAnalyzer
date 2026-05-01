"""Integration helpers for running the scanner from the web backend."""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from scanner.core.report import build_report, report_to_dict
from scanner.modules.dependencies import analyze_dependencies
from scanner.modules.llm_analysis import analyze_with_llm
from scanner.modules.rate_limit import analyze_rate_limits
from scanner.modules.secrets import detect_secrets
from scanner.modules.sensitive_data import detect_sensitive_data
from scanner.modules.validation import analyze_validation
from scanner.utils.file_loader import load_text_files


class ScanError(Exception):
    """Raised when a web scan request cannot be completed."""


def scan_github_repo(
    repo_url: str,
    include_llm_analysis: bool = False,
    llm_top_n: int = 5,
) -> dict[str, Any]:
    """Clone a GitHub repository into a temp directory and return a scan report."""
    validate_repo_url(repo_url)

    with TemporaryDirectory(prefix="security-scan-") as temp_dir:
        repo_path = Path(temp_dir) / "repo"
        clone_repository(repo_url, repo_path)
        return scan_project(repo_path, include_llm_analysis, llm_top_n)


def scan_zip_archive(
    zip_path: Path,
    include_llm_analysis: bool = False,
    llm_top_n: int = 5,
) -> dict[str, Any]:
    """Extract an uploaded zip into a temp directory and return a scan report."""
    with TemporaryDirectory(prefix="security-scan-") as temp_dir:
        extract_root = Path(temp_dir) / "archive"
        extract_root.mkdir()
        extract_zip_safely(zip_path, extract_root)
        project_path = find_project_root(extract_root)
        return scan_project(project_path, include_llm_analysis, llm_top_n)


def scan_project(
    project_path: Path,
    include_llm_analysis: bool = False,
    llm_top_n: int = 5,
) -> dict[str, Any]:
    """Run the existing scanner pipeline and return JSON-serializable output."""
    try:
        loaded_files = load_text_files(project_path)
    except (FileNotFoundError, NotADirectoryError, OSError) as exc:
        raise ScanError(str(exc)) from exc

    llm_analyses = (
        analyze_with_llm(loaded_files, top_n=llm_top_n)
        if include_llm_analysis
        else None
    )
    report = build_report(
        project_path=project_path,
        loaded_files=loaded_files,
        secret_findings=detect_secrets(loaded_files),
        dependency_warnings=analyze_dependencies(loaded_files),
        validation_findings=analyze_validation(loaded_files),
        rate_limit_findings=analyze_rate_limits(loaded_files),
        sensitive_data_findings=detect_sensitive_data(loaded_files),
        llm_analyses=llm_analyses,
    )

    return report_to_dict(report)


def validate_repo_url(repo_url: str) -> None:
    """Allow common GitHub clone URLs and reject ambiguous input."""
    normalized_url = repo_url.strip()
    if normalized_url.startswith("https://github.com/") and normalized_url.endswith(
        ".git"
    ):
        return

    if normalized_url.startswith("https://github.com/") and "/" in normalized_url[19:]:
        return

    raise ScanError("Only HTTPS GitHub repository URLs are supported.")


def clone_repository(repo_url: str, destination: Path) -> None:
    """Clone a repository with a shallow checkout."""
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(destination)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise ScanError("Git is not installed or is not available on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ScanError("Repository clone timed out.") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "git clone failed"
        raise ScanError(f"Could not clone repository: {detail}") from exc


def extract_zip_safely(zip_path: Path, destination: Path) -> None:
    """Extract a zip archive while preventing path traversal."""
    try:
        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.infolist():
                target_path = (destination / member.filename).resolve()
                if not is_relative_to(target_path, destination.resolve()):
                    raise ScanError("Zip archive contains an unsafe file path.")

            archive.extractall(destination)
    except zipfile.BadZipFile as exc:
        raise ScanError("Uploaded file is not a valid zip archive.") from exc


def find_project_root(extract_root: Path) -> Path:
    """Return the single top-level extracted directory when present."""
    entries = [entry for entry in extract_root.iterdir() if not entry.name.startswith(".")]
    directories = [entry for entry in entries if entry.is_dir()]

    if len(entries) == 1 and len(directories) == 1:
        return directories[0]

    return extract_root


def is_relative_to(path: Path, root: Path) -> bool:
    """Return True when path is inside root on Python 3.10."""
    try:
        path.relative_to(root)
    except ValueError:
        return False

    return True

