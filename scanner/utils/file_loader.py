"""Utilities for loading text files from a project directory."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path


IGNORED_DIRECTORY_NAMES = {".git", "node_modules", "venv", "__pycache__"}


def load_text_files(root_path: str | Path) -> dict[str, str]:
    """Recursively load readable text files from a directory.

    Returns a dictionary where each key is a file path and each value is the
    file's text content. Binary or unreadable files are skipped.
    """
    root = Path(root_path).expanduser().resolve()
    validate_directory(root)

    loaded_files: dict[str, str] = {}
    for file_path in iter_candidate_files(root):
        content = read_text_file(file_path)
        if content is None:
            continue

        loaded_files[str(file_path)] = content

    return loaded_files


def validate_directory(path: Path) -> None:
    """Raise a helpful error when the supplied path is not a directory."""
    if not path.exists():
        raise FileNotFoundError(f"Directory does not exist: {path}")

    if not path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")


def iter_candidate_files(root: Path) -> Iterator[Path]:
    """Yield files below root while skipping ignored directories."""
    for current_dir, dir_names, file_names in os.walk(root):
        dir_names[:] = [
            dir_name for dir_name in dir_names if not should_ignore_directory(dir_name)
        ]

        for file_name in file_names:
            yield Path(current_dir) / file_name


def should_ignore_directory(directory_name: str) -> bool:
    """Return True when a directory should be excluded from traversal."""
    return directory_name in IGNORED_DIRECTORY_NAMES


def read_text_file(file_path: Path) -> str | None:
    """Read a text file and return None for binary or unreadable files."""
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
    except OSError:
        return None
