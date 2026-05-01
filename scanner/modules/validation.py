"""Heuristic input validation checks for Python endpoints and functions."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


PYTHON_SUFFIX = ".py"
INPUT_PARAMETER_NAMES = {
    "request",
    "input",
    "user_input",
    "data",
    "payload",
    "body",
    "query",
    "params",
    "form",
    "json",
}
ROUTE_METHOD_NAMES = {
    "route",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "api_view",
}
VALIDATION_MODULE_NAMES = {
    "pydantic",
    "marshmallow",
    "cerberus",
    "voluptuous",
    "wtforms",
    "schema",
}
VALIDATION_FUNCTION_NAMES = {
    "len",
    "isinstance",
    "issubclass",
    "type",
    "match",
    "search",
    "fullmatch",
    "compile",
}
VALIDATION_METHOD_NAMES = {
    "isdigit",
    "isalpha",
    "isalnum",
    "startswith",
    "endswith",
}


@dataclass(frozen=True)
class ValidationFinding:
    """A function or endpoint that may be missing input validation."""

    file_name: str
    function_name: str
    line_number: int
    warning: str
    evidence: str


def analyze_validation(files: dict[str, str]) -> list[ValidationFinding]:
    """Analyze Python files for input-taking functions without validation."""
    findings: list[ValidationFinding] = []

    for file_name, content in files.items():
        if Path(file_name).suffix != PYTHON_SUFFIX:
            continue

        findings.extend(analyze_python_file(file_name, content))

    return findings


def analyze_python_file(file_name: str, content: str) -> list[ValidationFinding]:
    """Parse one Python file and analyze its functions."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    validation_imports = collect_validation_imports(tree)
    findings: list[ValidationFinding] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            finding = analyze_function(file_name, node, validation_imports)
            if finding is not None:
                findings.append(finding)

    return findings


def analyze_function(
    file_name: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    validation_imports: set[str],
) -> ValidationFinding | None:
    """Return a finding when a relevant function lacks validation signals."""
    is_route = has_route_decorator(node)
    input_parameters = get_input_parameters(node)

    if not is_route and not input_parameters:
        return None

    if has_validation_signals(node, validation_imports):
        return None

    return ValidationFinding(
        file_name=file_name,
        function_name=node.name,
        line_number=node.lineno,
        warning="Function accepts input but no validation checks were found.",
        evidence=build_evidence(is_route, input_parameters),
    )


def collect_validation_imports(tree: ast.AST) -> set[str]:
    """Collect imported validation libraries used by the current file."""
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(get_import_roots(alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(get_import_root(node.module))

    return imports & VALIDATION_MODULE_NAMES


def get_input_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return function parameters that look like request or user input."""
    parameters = get_all_parameter_names(node)
    return [name for name in parameters if name.lower() in INPUT_PARAMETER_NAMES]


def get_all_parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return positional and keyword-only parameter names for a function."""
    args = node.args
    parameters = [arg.arg for arg in args.posonlyargs + args.args + args.kwonlyargs]

    if args.vararg is not None:
        parameters.append(args.vararg.arg)

    if args.kwarg is not None:
        parameters.append(args.kwarg.arg)

    return parameters


def has_route_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True for common Flask, Django, and FastAPI route decorators."""
    return any(is_route_decorator(decorator) for decorator in node.decorator_list)


def is_route_decorator(decorator: ast.AST) -> bool:
    """Check whether a decorator expression resembles a route decorator."""
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    name = get_callable_name(target)

    if name is None:
        return False

    return name.split(".")[-1] in ROUTE_METHOD_NAMES


def has_validation_signals(
    node: ast.FunctionDef | ast.AsyncFunctionDef, validation_imports: set[str]
) -> bool:
    """Return True when a function appears to validate or normalize input."""
    if validation_imports:
        return True

    return any(is_validation_node(child) for child in ast.walk(node))


def is_validation_node(node: ast.AST) -> bool:
    """Return True for simple validation patterns such as len or isinstance."""
    if isinstance(node, ast.Call):
        callable_name = get_callable_name(node.func)
        return callable_name in VALIDATION_FUNCTION_NAMES or (
            callable_name is not None
            and callable_name.split(".")[-1] in VALIDATION_METHOD_NAMES
        )

    if isinstance(node, ast.Compare):
        return True

    if isinstance(node, ast.If) and node.test is not None:
        return True

    return False


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


def get_import_roots(module_name: str) -> str:
    """Return the top-level module name from an import path."""
    return get_import_root(module_name)


def get_import_root(module_name: str) -> str:
    """Return the first component of a dotted module name."""
    return module_name.split(".", 1)[0]


def build_evidence(is_route: bool, input_parameters: list[str]) -> str:
    """Build a short explanation for why the function was inspected."""
    reasons: list[str] = []

    if is_route:
        reasons.append("route decorator")

    if input_parameters:
        reasons.append(f"input parameters: {', '.join(input_parameters)}")

    return "; ".join(reasons)
