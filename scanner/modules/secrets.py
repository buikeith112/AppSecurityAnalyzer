"""Detection logic for hardcoded API keys and secrets."""

from __future__ import annotations

from dataclasses import dataclass
from re import Match

from scanner.utils.patterns import SECRET_PATTERNS, SecretPattern


@dataclass(frozen=True)
class SecretFinding:
    """A single hardcoded secret finding reported by the scanner."""

    file_name: str
    line_number: int
    secret_type: str
    matched_string: str


def detect_secrets(files: dict[str, str]) -> list[SecretFinding]:
    """Scan loaded file contents and return possible hardcoded secrets."""
    findings: list[SecretFinding] = []

    for file_name, content in files.items():
        findings.extend(scan_file_for_secrets(file_name, content))

    return findings


def scan_file_for_secrets(file_name: str, content: str) -> list[SecretFinding]:
    """Scan one file line-by-line so each finding has an accurate line number."""
    findings: list[SecretFinding] = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        findings.extend(scan_line_for_secrets(file_name, line_number, line))

    return findings


def scan_line_for_secrets(
    file_name: str, line_number: int, line: str
) -> list[SecretFinding]:
    """Scan one line and avoid duplicate findings from overlapping patterns."""
    findings: list[SecretFinding] = []
    matched_spans: list[tuple[int, int]] = []

    for pattern in SECRET_PATTERNS:
        for match in pattern.regex.finditer(line):
            secret_value = extract_secret_value(pattern, match)
            value_span = get_secret_span(pattern, match)

            if has_overlap(value_span, matched_spans):
                continue

            matched_spans.append(value_span)
            findings.append(
                SecretFinding(
                    file_name=file_name,
                    line_number=line_number,
                    secret_type=pattern.name,
                    matched_string=mask_secret(secret_value),
                )
            )

    return findings


def extract_secret_value(pattern: SecretPattern, match: Match[str]) -> str:
    """Return the secret value from a named group or the full regex match."""
    if pattern.secret_group is None:
        return match.group(0)

    return match.group(pattern.secret_group)


def get_secret_span(pattern: SecretPattern, match: Match[str]) -> tuple[int, int]:
    """Return the span of the actual secret value for overlap checks."""
    if pattern.secret_group is None:
        return match.span(0)

    return match.span(pattern.secret_group)


def has_overlap(span: tuple[int, int], previous_spans: list[tuple[int, int]]) -> bool:
    """Return True when a match overlaps an already reported secret."""
    start, end = span
    return any(
        start < previous_end and end > previous_start
        for previous_start, previous_end in previous_spans
    )


def mask_secret(secret: str) -> str:
    """Mask a secret while preserving enough characters to identify it."""
    if len(secret) <= 8:
        return "*" * len(secret)

    return f"{secret[:4]}...{secret[-4:]}"
