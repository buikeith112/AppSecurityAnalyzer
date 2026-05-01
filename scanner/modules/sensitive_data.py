"""Detection logic for exposed sensitive user data."""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern


@dataclass(frozen=True)
class SensitiveDataPattern:
    """A regex pattern for one category of sensitive data."""

    name: str
    regex: Pattern[str]


@dataclass(frozen=True)
class SensitiveDataFinding:
    """A sensitive data match found in a project file."""

    file_name: str
    line_number: int
    data_type: str
    matched_value: str


# Email detection requires a normal local part, domain labels, and a 2+ letter
# TLD. This avoids many incidental strings while still catching common emails.
EMAIL_PATTERN = SensitiveDataPattern(
    name="Email Address",
    regex=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)

# This catches basic US SSN formatting. It excludes impossible area/group/serial
# blocks of all zeroes, which reduces obvious false positives in mock data.
SSN_PATTERN = SensitiveDataPattern(
    name="Social Security Number",
    regex=re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b"),
)

# Phone detection focuses on common US-style formats with separators or an area
# code wrapper. Requiring formatting keeps random 10-digit IDs from matching.
PHONE_PATTERN = SensitiveDataPattern(
    name="Phone Number",
    regex=re.compile(
        r"(?<!\d)(?:\+1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]\d{3}[-.\s]\d{4}(?!\d)"
    ),
)

SENSITIVE_DATA_PATTERNS = [
    EMAIL_PATTERN,
    SSN_PATTERN,
    PHONE_PATTERN,
]


def detect_sensitive_data(files: dict[str, str]) -> list[SensitiveDataFinding]:
    """Scan loaded files and return exposed sensitive data findings."""
    findings: list[SensitiveDataFinding] = []

    for file_name, content in files.items():
        findings.extend(scan_file_for_sensitive_data(file_name, content))

    return findings


def scan_file_for_sensitive_data(
    file_name: str, content: str
) -> list[SensitiveDataFinding]:
    """Scan one file line-by-line so findings include source line numbers."""
    findings: list[SensitiveDataFinding] = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        findings.extend(scan_line_for_sensitive_data(file_name, line_number, line))

    return findings


def scan_line_for_sensitive_data(
    file_name: str, line_number: int, line: str
) -> list[SensitiveDataFinding]:
    """Scan one line for sensitive data and mask each reported value."""
    findings: list[SensitiveDataFinding] = []

    for pattern in SENSITIVE_DATA_PATTERNS:
        for match in pattern.regex.finditer(line):
            findings.append(
                SensitiveDataFinding(
                    file_name=file_name,
                    line_number=line_number,
                    data_type=pattern.name,
                    matched_value=mask_sensitive_value(pattern.name, match.group(0)),
                )
            )

    return findings


def mask_sensitive_value(data_type: str, value: str) -> str:
    """Mask a sensitive value while keeping it recognizable for triage."""
    if data_type == "Email Address":
        return mask_email(value)

    if data_type == "Social Security Number":
        return f"***-**-{value[-4:]}"

    if data_type == "Phone Number":
        return mask_phone(value)

    return mask_generic(value)


def mask_email(email: str) -> str:
    """Mask the local part of an email address."""
    local_part, domain = email.split("@", 1)
    if len(local_part) <= 2:
        masked_local = "*" * len(local_part)
    else:
        masked_local = f"{local_part[0]}***{local_part[-1]}"

    return f"{masked_local}@{domain}"


def mask_phone(phone_number: str) -> str:
    """Mask all phone digits except the last four."""
    digits_seen = 0
    total_digits = sum(character.isdigit() for character in phone_number)
    characters: list[str] = []

    for character in phone_number:
        if not character.isdigit():
            characters.append(character)
            continue

        digits_seen += 1
        characters.append(character if total_digits - digits_seen < 4 else "*")

    return "".join(characters)


def mask_generic(value: str) -> str:
    """Fallback masking for unexpected sensitive data categories."""
    if len(value) <= 4:
        return "*" * len(value)

    return f"{value[:2]}...{value[-2:]}"
