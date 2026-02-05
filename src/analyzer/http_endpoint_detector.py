"""
HTTP endpoint detector for FlowDiff.

Parses Python files to extract HTTP route decorators:
- FastAPI: @app.post("/analyze"), @app.get("/health")
- Flask: @app.route("/analyze", methods=["POST"])

Builds mapping from HTTP endpoints to Python functions.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class HTTPEndpoint:
    """Represents an HTTP endpoint handler."""
    method: str  # "GET", "POST", etc.
    path: str  # "/analyze", "/health"
    handler_function: str  # "api.analyze"
    file_path: str
    line_number: int


def extract_http_endpoints(file_path: Path, module_name: str = None) -> List[HTTPEndpoint]:
    """Extract HTTP endpoints from Python files.

    Args:
        file_path: Path to Python file
        module_name: Qualified module name (e.g., "src.api")

    Returns:
        List of HTTPEndpoint objects
    """
    if not file_path.exists() or not file_path.suffix == '.py':
        return []

    # If no module name provided, infer from file path
    if module_name is None:
        module_name = _infer_module_name(file_path)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except (UnicodeDecodeError, OSError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    endpoints = []

    # Walk through all function definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Check decorators for HTTP route patterns
            endpoint = _extract_endpoint_from_decorators(
                node,
                module_name,
                str(file_path)
            )
            if endpoint:
                endpoints.append(endpoint)

    return endpoints


def _infer_module_name(file_path: Path) -> str:
    """Infer module name from file path.

    Examples:
        /path/to/src/api.py -> src.api
        /path/to/server.py -> server
    """
    parts = file_path.parts

    # Find 'src' in path or use last few parts
    try:
        src_idx = parts.index('src')
        module_parts = parts[src_idx:]
    except ValueError:
        # No 'src', use last 2 parts
        module_parts = parts[-2:] if len(parts) > 1 else parts[-1:]

    # Remove .py extension
    module_str = '.'.join(module_parts)
    module_str = module_str.replace('.py', '')

    return module_str


def _extract_endpoint_from_decorators(
    func_node: ast.FunctionDef,
    module_name: str,
    file_path: str
) -> Optional[HTTPEndpoint]:
    """Extract HTTP endpoint from function decorators.

    Supports:
        FastAPI: @app.post("/analyze"), @app.get("/health")
        Flask: @app.route("/analyze", methods=["POST"])
    """
    for decorator in func_node.decorator_list:
        # FastAPI: @app.post("/path")
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                # Check for app.post, app.get, app.put, app.delete, app.patch
                if decorator.func.attr in ('post', 'get', 'put', 'delete', 'patch'):
                    method = decorator.func.attr.upper()
                    path = _extract_path_from_args(decorator)

                    if path:
                        return HTTPEndpoint(
                            method=method,
                            path=path,
                            handler_function=f"{module_name}.{func_node.name}",
                            file_path=file_path,
                            line_number=func_node.lineno
                        )

                # Flask: @app.route("/path", methods=["POST"])
                elif decorator.func.attr == 'route':
                    path = _extract_path_from_args(decorator)
                    method = _extract_method_from_flask_route(decorator)

                    if path:
                        return HTTPEndpoint(
                            method=method or 'GET',  # Flask defaults to GET
                            path=path,
                            handler_function=f"{module_name}.{func_node.name}",
                            file_path=file_path,
                            line_number=func_node.lineno
                        )

    return None


def _extract_path_from_args(call_node: ast.Call) -> Optional[str]:
    """Extract path string from decorator call arguments.

    Examples:
        @app.post("/analyze") -> "/analyze"
        @app.route("/health") -> "/health"
    """
    # First positional argument is usually the path
    if call_node.args and isinstance(call_node.args[0], ast.Constant):
        return call_node.args[0].value

    # Check keyword arguments for 'path'
    for keyword in call_node.keywords:
        if keyword.arg == 'path' and isinstance(keyword.value, ast.Constant):
            return keyword.value.value

    return None


def _extract_method_from_flask_route(call_node: ast.Call) -> Optional[str]:
    """Extract HTTP method from Flask @app.route decorator.

    Example:
        @app.route("/analyze", methods=["POST"]) -> "POST"
    """
    for keyword in call_node.keywords:
        if keyword.arg == 'methods':
            # methods=["POST", "GET"]
            if isinstance(keyword.value, ast.List):
                # Return first method in list
                if keyword.value.elts and isinstance(keyword.value.elts[0], ast.Constant):
                    return keyword.value.elts[0].value

    return None


def build_endpoint_map(file_paths: List[Path]) -> Dict[str, str]:
    """Build mapping from HTTP endpoints to Python functions.

    Args:
        file_paths: List of Python files to scan

    Returns:
        Dict mapping "METHOD /path" to "module.function"

    Example:
        {
            "POST /analyze": "api.analyze",
            "GET /health": "api.health_check"
        }
    """
    endpoint_map = {}

    for file_path in file_paths:
        endpoints = extract_http_endpoints(file_path)

        for endpoint in endpoints:
            key = f"{endpoint.method} {endpoint.path}"
            endpoint_map[key] = endpoint.handler_function

    return endpoint_map


def resolve_http_call(
    method: str,
    path: str,
    endpoint_map: Dict[str, str]
) -> Optional[str]:
    """Resolve HTTP call to Python function.

    Args:
        method: HTTP method (POST, GET, etc.)
        path: URL path (/analyze, /health, etc.)
        endpoint_map: Mapping from "METHOD /path" to function

    Returns:
        Qualified function name or None

    Example:
        resolve_http_call("POST", "/analyze", endpoint_map)
        -> "api.analyze"
    """
    key = f"{method} {path}"
    return endpoint_map.get(key)
