"""Local dependency analysis for supported manifest files."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIREMENTS_FILE_NAME = "requirements.txt"
PACKAGE_JSON_FILE_NAME = "package.json"

# These minimums are intentionally small and local. They are not vulnerability
# data; they only catch obviously stale versions for common dependencies.
KNOWN_MINIMUM_VERSIONS = {
    "django": (3, 0, 0),
    "flask": (2, 0, 0),
    "requests": (2, 20, 0),
    "urllib3": (1, 26, 0),
    "numpy": (1, 20, 0),
    "react": (17, 0, 0),
    "express": (4, 0, 0),
    "lodash": (4, 0, 0),
    "axios": (1, 0, 0),
}


@dataclass(frozen=True)
class DependencyWarning:
    """A dependency issue found in a manifest file."""

    file_name: str
    dependency_name: str
    warning: str
    version: str | None = None
    line_number: int | None = None


@dataclass(frozen=True)
class ParsedDependency:
    """A dependency parsed from a supported manifest file."""

    file_name: str
    dependency_name: str
    version_spec: str | None
    line_number: int | None = None


def analyze_dependencies(files: dict[str, str]) -> list[DependencyWarning]:
    """Analyze supported dependency manifests and return local warnings."""
    warnings: list[DependencyWarning] = []

    for file_name, content in files.items():
        for dependency in parse_dependency_file(file_name, content):
            warnings.extend(analyze_dependency(dependency))

    return warnings


def parse_dependency_file(file_name: str, content: str) -> list[ParsedDependency]:
    """Parse dependencies from a supported file based on its basename."""
    base_name = Path(file_name).name

    if base_name == REQUIREMENTS_FILE_NAME:
        return parse_requirements_file(file_name, content)

    if base_name == PACKAGE_JSON_FILE_NAME:
        return parse_package_json(file_name, content)

    return []


def parse_requirements_file(file_name: str, content: str) -> list[ParsedDependency]:
    """Parse plain package entries from requirements.txt content."""
    dependencies: list[ParsedDependency] = []

    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        line = strip_requirement_comment(raw_line).strip()
        if should_skip_requirement_line(line):
            continue

        dependencies.append(parse_requirement_line(file_name, line_number, line))

    return dependencies


def parse_requirement_line(
    file_name: str, line_number: int, line: str
) -> ParsedDependency:
    """Parse one requirements.txt dependency line into name and version spec."""
    match = re.match(r"^\s*([A-Za-z0-9_.-]+)\s*([<>=!~]=?.*)?$", line)
    if not match:
        return ParsedDependency(file_name, line, None, line_number)

    dependency_name = normalize_dependency_name(match.group(1))
    version_spec = match.group(2).strip() if match.group(2) else None

    return ParsedDependency(file_name, dependency_name, version_spec, line_number)


def parse_package_json(file_name: str, content: str) -> list[ParsedDependency]:
    """Parse dependencies and devDependencies from package.json content."""
    try:
        package_data = json.loads(content)
    except json.JSONDecodeError:
        return []

    dependencies: list[ParsedDependency] = []
    for section_name in ("dependencies", "devDependencies"):
        section = package_data.get(section_name, {})
        if not isinstance(section, dict):
            continue

        dependencies.extend(parse_package_json_section(file_name, content, section))

    return dependencies


def parse_package_json_section(
    file_name: str, content: str, section: dict[str, Any]
) -> list[ParsedDependency]:
    """Convert one package.json dependency section into parsed dependencies."""
    dependencies: list[ParsedDependency] = []

    for dependency_name, version_spec in section.items():
        if not isinstance(version_spec, str):
            version_spec = None

        dependencies.append(
            ParsedDependency(
                file_name=file_name,
                dependency_name=normalize_dependency_name(dependency_name),
                version_spec=version_spec,
                line_number=find_json_dependency_line(content, dependency_name),
            )
        )

    return dependencies


def analyze_dependency(dependency: ParsedDependency) -> list[DependencyWarning]:
    """Return warnings for one parsed dependency."""
    warnings: list[DependencyWarning] = []

    if is_missing_version(dependency.version_spec):
        warnings.append(build_warning(dependency, "Missing version number."))
        return warnings

    pinned_version = extract_exact_version(dependency.version_spec or "")
    if pinned_version is None:
        return warnings

    old_version_warning = get_old_version_warning(dependency.dependency_name, pinned_version)
    if old_version_warning is not None:
        warnings.append(build_warning(dependency, old_version_warning))

    return warnings


def build_warning(dependency: ParsedDependency, warning: str) -> DependencyWarning:
    """Create a dependency warning while preserving source location details."""
    return DependencyWarning(
        file_name=dependency.file_name,
        dependency_name=dependency.dependency_name,
        version=dependency.version_spec,
        line_number=dependency.line_number,
        warning=warning,
    )


def strip_requirement_comment(line: str) -> str:
    """Remove trailing requirements.txt comments from a line."""
    return line.split("#", 1)[0]


def should_skip_requirement_line(line: str) -> bool:
    """Return True for blank, option, include, or URL-style requirement lines."""
    return (
        not line
        or line.startswith("-")
        or "://" in line
        or line.startswith("git+")
    )


def is_missing_version(version_spec: str | None) -> bool:
    """Return True when no meaningful dependency version was supplied."""
    if version_spec is None:
        return True

    return version_spec.strip().lower() in {"", "*", "latest"}


def extract_exact_version(version_spec: str) -> tuple[int, ...] | None:
    """Extract versions only from exact pins to keep old-version checks precise."""
    match = re.match(r"^\s*(?:==?)?\s*v?(\d+(?:\.\d+){0,2})\s*$", version_spec)
    if match is None:
        return None

    return tuple(int(part) for part in match.group(1).split("."))


def get_old_version_warning(
    dependency_name: str, version: tuple[int, ...]
) -> str | None:
    """Return a stale-version warning using simple local heuristics."""
    if version[0] == 0:
        return "Very old/pre-1.0 version detected."

    minimum_version = KNOWN_MINIMUM_VERSIONS.get(dependency_name)
    if minimum_version is not None and compare_versions(version, minimum_version) < 0:
        return f"Very old version detected; local heuristic expects at least {format_version(minimum_version)}."

    return None


def compare_versions(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    """Compare two version tuples after padding missing components with zeroes."""
    max_length = max(len(left), len(right))
    padded_left = left + (0,) * (max_length - len(left))
    padded_right = right + (0,) * (max_length - len(right))

    if padded_left < padded_right:
        return -1

    if padded_left > padded_right:
        return 1

    return 0


def format_version(version: tuple[int, ...]) -> str:
    """Format a version tuple for display in warnings."""
    return ".".join(str(part) for part in version)


def normalize_dependency_name(dependency_name: str) -> str:
    """Normalize dependency names for stable matching against local heuristics."""
    return dependency_name.strip().lower()


def find_json_dependency_line(content: str, dependency_name: str) -> int | None:
    """Find the line number where a package.json dependency name appears."""
    needle = f'"{dependency_name}"'
    for line_number, line in enumerate(content.splitlines(), start=1):
        if needle in line:
            return line_number

    return None
