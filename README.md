# AI Code Risk Auditor

AI Code Risk Auditor is a local-first security auditing CLI for source code and small application projects. It scans project files for common risk indicators such as hardcoded secrets, exposed sensitive data, weak dependency hygiene, missing input validation, and missing API rate limiting.

The tool is intentionally heuristic-based. It does not call external APIs, upload code, or claim to replace a full security review. It is designed to give developers quick, readable feedback in under two minutes after cloning.

## Features

- Recursively loads text files from a target project directory.
- Ignores common noisy folders such as `.git/`, `node_modules/`, `venv/`, and `__pycache__/`.
- Detects hardcoded secrets:
  - AWS access keys
  - AWS secret access keys
  - OpenAI API keys
  - Generic API keys and tokens
- Detects sensitive data exposure:
  - Email addresses
  - Basic US SSN patterns
  - Common phone number formats
- Analyzes dependencies in:
  - `requirements.txt`
  - `package.json`
- Flags dependency issues:
  - Missing version numbers
  - Very old versions using local heuristics
- Detects suspicious input handling:
  - Flask, Django, and FastAPI-style routes
  - Functions with input-like parameters
  - Missing validation signals such as `len()`, regex checks, type checks, and validation libraries
- Detects API routes without obvious rate limiting:
  - Flask-Limiter signals
  - Express `express-rate-limit` signals
- Produces a single categorized report with a `0-100` risk score.
- Supports optional JSON report export.
- Optionally runs LLM analysis on a sampled set of source files to flag AI code smells.

## Installation

Requires Python 3.10 or newer.

```bash
git clone <repo-url>
cd AppSecurityAnalyzer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

On Windows PowerShell:

```powershell
git clone <repo-url>
cd AppSecurityAnalyzer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
```

The project currently uses only the Python standard library at runtime. `pip install -e .` installs the `ai-code-risk-auditor` CLI command.

## Usage

Run with the repository wrapper:

```bash
python main.py examples/vulnerable_demo
```

Run after editable installation:

```bash
ai-code-risk-auditor examples/vulnerable_demo
```

Export JSON:

```bash
ai-code-risk-auditor examples/vulnerable_demo --json-report reports/scan_report.json
```

Run optional LLM analysis on the top 5 source files:

```bash
ai-code-risk-auditor examples/vulnerable_demo --llm-analysis
```

Limit the sampled files:

```bash
ai-code-risk-auditor examples/vulnerable_demo --llm-analysis --llm-top-n 2
```

LLM providers are configured with environment variables. When no provider key is
configured, the scanner uses an offline mock response so the command still works
in local tests and CI.

Use local Ollama:

```bash
LLM_PROVIDER=ollama LLM_MODEL=qwen2.5-coder:7b ai-code-risk-auditor examples/vulnerable_demo --llm-analysis
```

Use Gemini's hosted free tier:

```bash
LLM_PROVIDER=gemini GEMINI_API_KEY=<your-key> LLM_MODEL=gemini-2.5-flash-lite ai-code-risk-auditor examples/vulnerable_demo --llm-analysis
```

Use Groq's hosted free tier:

```bash
LLM_PROVIDER=groq GROQ_API_KEY=<your-key> LLM_MODEL=llama-3.1-8b-instant ai-code-risk-auditor examples/vulnerable_demo --llm-analysis
```

Use OpenRouter free models:

```bash
LLM_PROVIDER=openrouter OPENROUTER_API_KEY=<your-key> LLM_MODEL=openrouter/free ai-code-risk-auditor examples/vulnerable_demo --llm-analysis
```

`LLM_PROVIDER=auto` is the default. It picks Gemini, Groq, OpenRouter, or OpenAI
when the matching API key is present, otherwise it uses the offline mock.

For hosted websites such as Vercel, use Gemini, Groq, or OpenRouter. Ollama only
works there if you run a separate reachable Ollama server and set
`LLM_BASE_URL` to that server; Vercel cannot call the Ollama server running on
your laptop via `localhost`.

Run the included test scripts:

```bash
python tests/test_file_loader.py
python tests/test_secrets.py
python tests/test_dependencies.py
python tests/test_validation.py
python tests/test_rate_limit.py
python tests/test_sensitive_data.py
python tests/test_llm_analysis.py
python tests/test_report.py
```

## Web Backend

Start the FastAPI backend:

```bash
uvicorn backend.app:app --reload
```

Open the frontend:

```text
http://127.0.0.1:8000
```

Deployment instructions are in [DEPLOYMENT.md](DEPLOYMENT.md).

Scan a GitHub repository URL:

```bash
curl -X POST http://127.0.0.1:8000/scan \
  -F "repo_url=https://github.com/example/project" \
  -F "llm_analysis=false"
```

Scan a zip upload:

```bash
curl -X POST http://127.0.0.1:8000/scan \
  -F "zip_file=@project.zip" \
  -F "llm_analysis=false"
```

Enable LLM analysis for the top two source files:

```bash
curl -X POST http://127.0.0.1:8000/scan \
  -F "repo_url=https://github.com/example/project" \
  -F "llm_analysis=true" \
  -F "llm_top_n=2"
```

## Example Output

```text
Security Scan Report
Project: examples/vulnerable_demo
Risk score: 100/100
Total files scanned: 4

First 5 files:
- examples/vulnerable_demo/app.py
- examples/vulnerable_demo/package.json
- examples/vulnerable_demo/requirements.txt
- examples/vulnerable_demo/users.csv

Secrets: 1
- OpenAI API Key in examples/vulnerable_demo/app.py:5
  Detail: Potential hardcoded secret detected.
  Evidence: sk-a...3456

Dependencies: 3
- lodash in examples/vulnerable_demo/package.json:3
  Detail: Very old version detected; local heuristic expects at least 4.0.0.
  Evidence: 3.10.1

Validation: 1
- login in examples/vulnerable_demo/app.py:9
  Detail: Function accepts input but no validation checks were found.
  Evidence: route decorator; input parameters: request

Rate Limit: 1
- ROUTE /login in examples/vulnerable_demo/app.py:9
  Detail: Route exists but no Flask-Limiter style protection was found.
  Evidence: Python API

Sensitive Data: 3
- Email Address in examples/vulnerable_demo/users.csv:2
  Detail: Sensitive data pattern detected.
  Evidence: a***e@example.com
```

## Project Structure

```text
scanner/
  core/
    report.py
  modules/
    dependencies.py
    rate_limit.py
    secrets.py
    sensitive_data.py
    validation.py
    llm_analysis.py
  utils/
    file_loader.py
    patterns.py
main.py
backend/
  app.py
  start.py
  scanner_integration.py
frontend/
  build.mjs
  config.js
  index.html
  package.json
  vercel.json
examples/
  vulnerable_demo/
tests/
```

## Future Improvements

- Add SARIF export for GitHub code scanning.
- Add severity levels per finding.
- Add configurable ignore paths and rule toggles.
- Add more language support for route and validation detection.
- Add optional vulnerability database integrations for dependencies.
- Add CI workflow examples.
- Replace script-style tests with a formal `pytest` suite.
- Add baseline support to suppress known accepted risks.
