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

Run the included test scripts:

```bash
python tests/test_file_loader.py
python tests/test_secrets.py
python tests/test_dependencies.py
python tests/test_validation.py
python tests/test_rate_limit.py
python tests/test_sensitive_data.py
python tests/test_report.py
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
  utils/
    file_loader.py
    patterns.py
main.py
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
