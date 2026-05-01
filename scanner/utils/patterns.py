"""Shared regex patterns used by scanner modules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern


@dataclass(frozen=True)
class SecretPattern:
    """A compiled secret regex and optional group containing the secret value."""

    name: str
    regex: Pattern[str]
    secret_group: str | None = None


# AWS access key IDs have stable public prefixes and a fixed 20-character shape.
# This detects the key ID only; it does not claim the key is active or valid.
AWS_ACCESS_KEY_ID = SecretPattern(
    name="AWS Access Key ID",
    regex=re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
)

# AWS secret access keys are 40 base64-like characters. To avoid matching any
# random 40-character string, this pattern requires an AWS-specific variable name.
AWS_SECRET_ACCESS_KEY = SecretPattern(
    name="AWS Secret Access Key",
    regex=re.compile(
        r"(?i)\baws[_-]?secret[_-]?access[_-]?key\b\s*[:=]\s*[\"']?"
        r"(?P<aws_secret>[A-Za-z0-9/+=]{40})[\"']?"
    ),
    secret_group="aws_secret",
)

# OpenAI keys start with sk-. The optional prefixes cover common modern key
# formats while requiring a long token body to avoid matching short examples.
OPENAI_API_KEY = SecretPattern(
    name="OpenAI API Key",
    regex=re.compile(r"\bsk-(?:proj-|admin-)?[A-Za-z0-9_-]{20,}\b"),
)

# Generic secrets are intentionally context-sensitive: they must be assigned to
# a key/token/secret-like name and contain a long high-variance token value.
GENERIC_API_KEY = SecretPattern(
    name="Generic API Key",
    regex=re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|client[_-]?secret|"
        r"access[_-]?token)\b\s*[:=]\s*[\"']?"
        r"(?P<generic_secret>[A-Za-z0-9_-]{32,128})[\"']?"
    ),
    secret_group="generic_secret",
)


SECRET_PATTERNS = [
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    OPENAI_API_KEY,
    GENERIC_API_KEY,
]
