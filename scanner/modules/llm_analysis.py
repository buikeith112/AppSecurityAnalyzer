"""LLM-backed analysis for AI code quality smells."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


DEFAULT_PROVIDER = "auto"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_OPENROUTER_MODEL = "openrouter/free"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_TOP_N = 5
MAX_CODE_CHARS = 12_000
CODE_EXTENSIONS = {
    ".c",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".ts",
    ".tsx",
}


@dataclass(frozen=True)
class LLMIssue:
    """A single issue returned by the LLM analysis."""

    title: str
    severity: str
    explanation: str


@dataclass(frozen=True)
class LLMFileAnalysis:
    """Structured LLM analysis output for one file."""

    file: str
    issues: list[LLMIssue]


class LLMClient(Protocol):
    """Minimal client interface so tests can inject a mock response."""

    def analyze(self, prompt: str) -> str:
        """Return a JSON string produced by an LLM or test double."""


class MockLLMClient:
    """Offline mock used when no API key is configured."""

    def analyze(self, prompt: str) -> str:
        """Return an empty but valid analysis response for local runs."""
        return json.dumps({"issues": []})


class OpenAICompatibleClient:
    """Small stdlib client for OpenAI-compatible Chat Completions APIs."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        provider_name: str,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.provider_name = provider_name

    def analyze(self, prompt: str) -> str:
        """Send the prompt and return the model's message content."""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise code quality reviewer. Return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return json.dumps(
                {
                    "issues": [
                        {
                            "title": "LLM analysis unavailable",
                            "severity": "low",
                            "explanation": f"{self.provider_name} request failed: {exc}",
                        }
                    ]
                }
            )

        try:
            return str(response_data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            return json.dumps(
                {
                    "issues": [
                        {
                            "title": "LLM analysis unavailable",
                            "severity": "low",
                            "explanation": f"Unexpected {self.provider_name} response: {exc}",
                        }
                    ]
                }
            )


class OllamaClient:
    """Client for a local or self-hosted Ollama server."""

    def __init__(
        self,
        model: str = DEFAULT_OLLAMA_MODEL,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    def analyze(self, prompt: str) -> str:
        """Send the prompt to Ollama and return the message content."""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise code quality reviewer. Return JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1},
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            return build_unavailable_response(f"Ollama request failed: {exc}")

        try:
            return str(response_data["message"]["content"])
        except (KeyError, TypeError) as exc:
            return build_unavailable_response(f"Unexpected Ollama response: {exc}")


def build_prompt(file_name: str, content: str) -> str:
    """Build the LLM prompt for one source file."""
    truncated_content = truncate_content(content)
    return (
        "Analyze this code for:\n\n"
        "* redundant logic\n"
        "* inefficiencies\n"
        "* bad practices\n"
        "* potential bugs\n"
        "* signs of low-quality AI-generated code\n\n"
        "Return:\n\n"
        "* list of issues\n"
        "* severity (low/medium/high)\n"
        "* explanation\n\n"
        'Return JSON in this shape: {"issues": [{"title": "...", '
        '"severity": "low|medium|high", "explanation": "..."}]}\n\n'
        f"File: {file_name}\n"
        "Code:\n"
        "```text\n"
        f"{truncated_content}\n"
        "```"
    )


def analyze_with_llm(
    files: dict[str, str],
    top_n: int = DEFAULT_TOP_N,
    client: LLMClient | None = None,
) -> list[LLMFileAnalysis]:
    """Analyze a sampled set of files with an LLM-compatible client."""
    if top_n <= 0:
        return []

    llm_client = client or build_default_client()
    results: list[LLMFileAnalysis] = []

    # Sampling limits cost, latency, and accidental source disclosure when a
    # project is large. The selected files are deterministic for repeatability.
    for file_name, content in select_files_for_analysis(files, top_n).items():
        prompt = build_prompt(file_name, content)
        response = llm_client.analyze(prompt)
        results.append(parse_llm_response(file_name, response))

    return results


def build_default_client() -> LLMClient:
    """Return a configured provider client, otherwise an offline mock."""
    provider = os.environ.get("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider == "auto":
        provider = detect_configured_provider()

    if provider == "ollama":
        return OllamaClient(
            model=get_model(DEFAULT_OLLAMA_MODEL),
            base_url=os.environ.get("LLM_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
        )

    if provider == "gemini":
        return build_openai_compatible_client(
            api_key_env="GEMINI_API_KEY",
            fallback_api_key_env="LLM_API_KEY",
            model=get_model(DEFAULT_GEMINI_MODEL),
            base_url=os.environ.get(
                "LLM_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta/openai",
            ),
            provider_name="Gemini",
        )

    if provider == "groq":
        return build_openai_compatible_client(
            api_key_env="GROQ_API_KEY",
            fallback_api_key_env="LLM_API_KEY",
            model=get_model(DEFAULT_GROQ_MODEL),
            base_url=os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            provider_name="Groq",
        )

    if provider == "openrouter":
        return build_openai_compatible_client(
            api_key_env="OPENROUTER_API_KEY",
            fallback_api_key_env="LLM_API_KEY",
            model=get_model(DEFAULT_OPENROUTER_MODEL),
            base_url=os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
            provider_name="OpenRouter",
        )

    if provider == "openai":
        return build_openai_compatible_client(
            api_key_env="OPENAI_API_KEY",
            fallback_api_key_env="LLM_API_KEY",
            model=get_model(DEFAULT_OPENAI_MODEL, legacy_env="OPENAI_MODEL"),
            base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
            provider_name="OpenAI",
        )

    return MockLLMClient()


def detect_configured_provider() -> str:
    """Pick a hosted provider from available credentials."""
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"

    return "mock"


def build_openai_compatible_client(
    api_key_env: str,
    fallback_api_key_env: str,
    model: str,
    base_url: str,
    provider_name: str,
) -> LLMClient:
    """Build a provider client or use the mock when no key is configured."""
    api_key = os.environ.get(api_key_env) or os.environ.get(fallback_api_key_env)
    if not api_key:
        return MockLLMClient()

    return OpenAICompatibleClient(
        api_key=api_key,
        model=model,
        base_url=base_url,
        provider_name=provider_name,
    )


def get_model(default_model: str, legacy_env: str | None = None) -> str:
    """Return a model override from env vars or the provider default."""
    if legacy_env is not None and os.environ.get(legacy_env):
        return str(os.environ[legacy_env])

    return os.environ.get("LLM_MODEL", default_model)


def build_unavailable_response(explanation: str) -> str:
    """Return a structured availability issue for failed provider calls."""
    return json.dumps(
        {
            "issues": [
                {
                    "title": "LLM analysis unavailable",
                    "severity": "low",
                    "explanation": explanation,
                }
            ]
        }
    )


def select_files_for_analysis(files: dict[str, str], top_n: int) -> dict[str, str]:
    """Return the highest-signal source files up to the configured limit."""
    source_files = [
        (file_name, content)
        for file_name, content in files.items()
        if Path(file_name).suffix.lower() in CODE_EXTENSIONS
    ]
    ranked_files = sorted(
        source_files,
        key=lambda item: (-len(item[1]), item[0]),
    )

    return dict(ranked_files[:top_n])


def truncate_content(content: str, max_chars: int = MAX_CODE_CHARS) -> str:
    """Bound prompt size so large files do not exceed practical API limits."""
    if len(content) <= max_chars:
        return content

    return (
        content[:max_chars]
        + "\n\n[Truncated: file content exceeded LLM analysis limit.]"
    )


def parse_llm_response(file_name: str, response: str) -> LLMFileAnalysis:
    """Parse an LLM JSON response into structured analysis."""
    try:
        payload = json.loads(response)
    except json.JSONDecodeError:
        return LLMFileAnalysis(
            file=file_name,
            issues=[
                LLMIssue(
                    title="Invalid LLM response",
                    severity="low",
                    explanation="The LLM returned non-JSON output.",
                )
            ],
        )

    issues_payload = payload.get("issues", [])
    if not isinstance(issues_payload, list):
        issues_payload = []

    issues = [parse_issue(issue) for issue in issues_payload if isinstance(issue, dict)]
    return LLMFileAnalysis(file=file_name, issues=issues)


def parse_issue(issue: dict[str, Any]) -> LLMIssue:
    """Normalize one raw issue dictionary from the LLM."""
    severity = str(issue.get("severity", "low")).lower()
    if severity not in {"low", "medium", "high"}:
        severity = "low"

    title = str(issue.get("title") or issue.get("issue") or "LLM code quality issue")
    explanation = str(issue.get("explanation") or issue.get("detail") or "")
    return LLMIssue(title=title, severity=severity, explanation=explanation)
