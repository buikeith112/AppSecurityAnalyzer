"""Simple verification script for LLM code smell analysis."""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scanner.core.report import build_report, report_to_dict
from scanner.modules.dependencies import analyze_dependencies
from scanner.modules.llm_analysis import (
    MockLLMClient,
    OllamaClient,
    analyze_with_llm,
    build_default_client,
    select_files_for_analysis,
    truncate_content,
)
from scanner.modules.rate_limit import analyze_rate_limits
from scanner.modules.secrets import detect_secrets
from scanner.modules.sensitive_data import detect_sensitive_data
from scanner.modules.validation import analyze_validation
from scanner.utils.file_loader import load_text_files


class StaticLLMClient:
    """Test double that returns a predictable LLM JSON response."""

    def analyze(self, prompt: str) -> str:
        return json.dumps(
            {
                "issues": [
                    {
                        "title": "Redundant branch",
                        "severity": "medium",
                        "explanation": "Two branches return the same value.",
                    }
                ]
            }
        )


LLM_ENV_NAMES = [
    "LLM_PROVIDER",
    "LLM_API_KEY",
    "LLM_MODEL",
    "LLM_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "OPENROUTER_API_KEY",
]


def clear_llm_env() -> dict[str, str]:
    """Remove LLM env vars and return their original values."""
    original_values: dict[str, str] = {}
    for env_name in LLM_ENV_NAMES:
        value = os.environ.pop(env_name, None)
        if value is not None:
            original_values[env_name] = value

    return original_values


def restore_env(original_values: dict[str, str]) -> None:
    """Restore env vars removed by clear_llm_env."""
    for env_name in LLM_ENV_NAMES:
        os.environ.pop(env_name, None)

    os.environ.update(original_values)


def test_analyze_with_mock_llm_response() -> None:
    """Verify mock LLM output is parsed into structured file issues."""
    files = {"app.py": "def f(x):\n    if x:\n        return 1\n    return 1\n"}

    analyses = analyze_with_llm(files, top_n=1, client=StaticLLMClient())

    assert len(analyses) == 1
    assert analyses[0].file == "app.py"
    assert analyses[0].issues[0].title == "Redundant branch"
    assert analyses[0].issues[0].severity == "medium"


def test_select_files_for_analysis_limits_to_top_n() -> None:
    """Verify only top N source files are selected for LLM analysis."""
    files = {
        "small.py": "x = 1",
        "large.py": "x = 1\n" * 100,
        "notes.txt": "not source code",
    }

    selected = select_files_for_analysis(files, top_n=1)

    assert list(selected.keys()) == ["large.py"]


def test_truncate_content_bounds_large_files() -> None:
    """Verify large file content is truncated before prompt construction."""
    truncated = truncate_content("abcdef", max_chars=3)

    assert truncated.startswith("abc")
    assert "Truncated" in truncated


def test_report_includes_llm_analysis_without_api_key() -> None:
    """Verify LLM analysis integrates into JSON report with a mock client."""
    sample_project = PROJECT_ROOT / "tests" / "fixtures" / "full_scan_project"
    loaded_files = load_text_files(sample_project)
    llm_analyses = analyze_with_llm(
        loaded_files,
        top_n=1,
        client=StaticLLMClient(),
    )
    report = build_report(
        project_path=sample_project,
        loaded_files=loaded_files,
        secret_findings=detect_secrets(loaded_files),
        dependency_warnings=analyze_dependencies(loaded_files),
        validation_findings=analyze_validation(loaded_files),
        rate_limit_findings=analyze_rate_limits(loaded_files),
        sensitive_data_findings=detect_sensitive_data(loaded_files),
        llm_analyses=llm_analyses,
    )
    report_data = report_to_dict(report)

    assert "llm_analysis" in report_data["findings_by_category"]
    assert report_data["findings_by_category"]["llm_analysis"][0]["title"] == "Redundant branch"


def test_default_llm_analysis_works_without_api_key() -> None:
    """Verify the default client falls back to an offline mock."""
    original_values = clear_llm_env()
    try:
        analyses = analyze_with_llm({"app.py": "print('hello')"}, top_n=1)
    finally:
        restore_env(original_values)

    assert len(analyses) == 1
    assert analyses[0].issues == []


def test_default_provider_auto_uses_mock_without_keys() -> None:
    """Verify auto provider stays offline when no provider key is configured."""
    original_values = clear_llm_env()
    try:
        client = build_default_client()
    finally:
        restore_env(original_values)

    assert isinstance(client, MockLLMClient)


def test_ollama_provider_builds_local_client() -> None:
    """Verify Ollama can be selected explicitly for local analysis."""
    original_values = clear_llm_env()
    try:
        os.environ["LLM_PROVIDER"] = "ollama"
        os.environ["LLM_MODEL"] = "qwen2.5-coder:7b"
        client = build_default_client()
    finally:
        restore_env(original_values)

    assert isinstance(client, OllamaClient)


def test_hosted_provider_without_key_uses_mock() -> None:
    """Verify hosted free-tier providers do not fail when a key is absent."""
    original_values = clear_llm_env()
    try:
        os.environ["LLM_PROVIDER"] = "gemini"
        client = build_default_client()
    finally:
        restore_env(original_values)

    assert isinstance(client, MockLLMClient)


if __name__ == "__main__":
    test_analyze_with_mock_llm_response()
    test_select_files_for_analysis_limits_to_top_n()
    test_truncate_content_bounds_large_files()
    test_report_includes_llm_analysis_without_api_key()
    test_default_llm_analysis_works_without_api_key()
    test_default_provider_auto_uses_mock_without_keys()
    test_ollama_provider_builds_local_client()
    test_hosted_provider_without_key_uses_mock()
    print("LLM analysis test passed.")
