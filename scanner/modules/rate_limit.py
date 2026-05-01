"""Heuristic rate limiting checks for API route handlers."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


PYTHON_SUFFIX = ".py"
JAVASCRIPT_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}
PYTHON_ROUTE_METHODS = {"route", "get", "post", "put", "patch", "delete"}
EXPRESS_ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "all", "use"}
RATE_LIMIT_PATTERNS = [
    # Flask-Limiter is commonly imported from flask_limiter and configured with
    # Limiter(...), or applied per endpoint with @limiter.limit(...).
    re.compile(r"\bflask_limiter\b"),
    re.compile(r"\bLimiter\s*\("),
    re.compile(r"@\s*\w*limiter\.limit\s*\("),
    # Express rate limiting usually appears as express-rate-limit or rateLimit().
    re.compile(r"express-rate-limit"),
    re.compile(r"\brateLimit\s*\("),
]
EXPRESS_ROUTE_PATTERN = re.compile(
    r"\b(?P<router>\w+)\s*\.\s*(?P<method>get|post|put|patch|delete|all|use)"
    r"\s*\(\s*[\"'`](?P<path>[^\"'`]+)[\"'`]",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RateLimitFinding:
    """An API endpoint that appears to be missing rate limiting."""

    file_name: str
    endpoint: str
    line_number: int
    framework: str
    warning: str


def analyze_rate_limits(files: dict[str, str]) -> list[RateLimitFinding]:
    """Find route handlers that lack obvious rate limiting protection."""
    if project_has_rate_limiter(files):
        return []

    findings: list[RateLimitFinding] = []
    for file_name, content in files.items():
        suffix = Path(file_name).suffix.lower()

        if suffix == PYTHON_SUFFIX:
            findings.extend(analyze_python_routes(file_name, content))
        elif suffix in JAVASCRIPT_SUFFIXES:
            findings.extend(analyze_express_routes(file_name, content))

    return findings


def project_has_rate_limiter(files: dict[str, str]) -> bool:
    """Return True when known rate limiting libraries or calls appear anywhere."""
    return any(has_rate_limiter_signal(content) for content in files.values())


def has_rate_limiter_signal(content: str) -> bool:
    """Return True when content contains a known rate limiting signal."""
    return any(pattern.search(content) for pattern in RATE_LIMIT_PATTERNS)


def analyze_python_routes(file_name: str, content: str) -> list[RateLimitFinding]:
    """Parse a Python file and report Flask/FastAPI-style route decorators."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    findings: list[RateLimitFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            endpoint = get_python_route_endpoint(decorator)
            if endpoint is None:
                continue

            findings.append(
                RateLimitFinding(
                    file_name=file_name,
                    endpoint=endpoint,
                    line_number=node.lineno,
                    framework="Python API",
                    warning="Route exists but no Flask-Limiter style protection was found.",
                )
            )

    return findings


def get_python_route_endpoint(decorator: ast.AST) -> str | None:
    """Return a route endpoint string from a supported Python route decorator."""
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    decorator_name = get_callable_name(target)

    if decorator_name is None:
        return None

    method = decorator_name.split(".")[-1]
    if method not in PYTHON_ROUTE_METHODS:
        return None

    path = get_first_string_argument(decorator) if isinstance(decorator, ast.Call) else None
    if path is None:
        return f"{method.upper()} <unknown path>"

    return f"{method.upper()} {path}"


def get_first_string_argument(call: ast.Call) -> str | None:
    """Return the first string literal argument from a decorator call."""
    if not call.args:
        return None

    first_argument = call.args[0]
    if isinstance(first_argument, ast.Constant) and isinstance(first_argument.value, str):
        return first_argument.value

    return None


def analyze_express_routes(file_name: str, content: str) -> list[RateLimitFinding]:
    """Scan a JavaScript/TypeScript file for Express route declarations."""
    findings: list[RateLimitFinding] = []

    for line_number, line in enumerate(content.splitlines(), start=1):
        for match in EXPRESS_ROUTE_PATTERN.finditer(line):
            method = match.group("method").upper()
            path = match.group("path")
            if method == "USE" and path == "/":
                continue

            findings.append(
                RateLimitFinding(
                    file_name=file_name,
                    endpoint=f"{method} {path}",
                    line_number=line_number,
                    framework="Express",
                    warning="Route exists but no express-rate-limit protection was found.",
                )
            )

    return findings


def get_callable_name(node: ast.AST) -> str | None:
    """Return a dotted callable name from Name or Attribute AST nodes."""
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent_name = get_callable_name(node.value)
        if parent_name is None:
            return node.attr

        return f"{parent_name}.{node.attr}"

    return None
