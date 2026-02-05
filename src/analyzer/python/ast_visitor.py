"""Python AST visitor for extracting symbols."""

import ast
from pathlib import Path
from typing import Dict, Set, Optional, List

from ..core.symbol import Symbol
from .python_symbol_table import PythonSymbolTable, ClassSymbol


class PythonASTVisitor(ast.NodeVisitor):
    """AST visitor that extracts symbols from Python code.

    Extracts:
    - Imports
    - Class definitions
    - Methods within classes
    - Top-level functions
    - Function calls
    - Local variable bindings (type inference)
    """

    def __init__(self, symbol_table: PythonSymbolTable, file_path: Path):
        self.symbol_table = symbol_table
        self.file_path = file_path
        self.current_class: Optional[str] = None  # Track current class context

    def visit_Import(self, node: ast.Import):
        """Extract import statements: import foo, import bar as baz"""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.symbol_table.add_import(name, alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Extract from imports: from foo import bar, from foo import baz as qux"""
        module = node.module or ''
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            qualified = f"{module}.{alias.name}" if module else alias.name
            self.symbol_table.add_import(name, qualified)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        """Extract class definition and its methods."""
        class_name = node.name
        qualified_name = f"{self.symbol_table.module_name}.{class_name}"

        # Extract base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)

        # Create class symbol
        class_symbol = ClassSymbol(
            name=class_name,
            qualified_name=qualified_name,
            base_classes=base_classes
        )

        # Extract methods
        old_class = self.current_class
        self.current_class = class_name

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_symbol = self._extract_function_symbol(
                    item,
                    is_method=True,
                    class_name=class_name
                )
                class_symbol.methods[method_symbol.name] = method_symbol

        self.current_class = old_class

        # Add class to symbol table
        self.symbol_table.add_class(class_symbol)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract top-level function definition."""
        # Only process if not inside a class
        if self.current_class is None:
            func_symbol = self._extract_function_symbol(node, is_method=False)
            self.symbol_table.add_symbol(func_symbol)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Extract async function definition."""
        if self.current_class is None:
            func_symbol = self._extract_function_symbol(node, is_method=False)
            self.symbol_table.add_symbol(func_symbol)

    def _extract_function_symbol(
        self,
        node: ast.FunctionDef,
        is_method: bool,
        class_name: Optional[str] = None
    ) -> Symbol:
        """Extract a function/method as a Symbol.

        Args:
            node: AST node for function definition
            is_method: True if this is a class method
            class_name: Name of parent class (if method)

        Returns:
            Symbol representing this function/method
        """
        func_name = node.name

        # Build qualified name
        if is_method and class_name:
            qualified_name = f"{self.symbol_table.module_name}.{class_name}.{func_name}"
        else:
            qualified_name = f"{self.symbol_table.module_name}.{func_name}"

        # Extract parameters
        parameters = [arg.arg for arg in node.args.args]

        # Extract return type if annotated
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)

        # Extract function-local imports (imports inside the function body)
        function_local_imports = self._extract_function_local_imports(node)

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Extract function calls
        raw_calls = self._extract_calls(node)

        # Extract local variable bindings for type inference
        local_bindings = self._extract_local_bindings(node)

        # Check for HTTP decorators (FastAPI/Flask)
        http_method, http_route = self._extract_http_decorator(node)

        # Build metadata
        metadata = {
            "parameters": parameters,
            "return_type": return_type,
            "is_class_method": is_method,
            "local_bindings": local_bindings,
            "function_local_imports": function_local_imports,  # NEW: function-local imports
        }

        if http_method:
            metadata["http_method"] = http_method
            metadata["http_route"] = http_route

        return Symbol(
            name=func_name,
            qualified_name=qualified_name,
            language="python",
            file_path=str(self.file_path),
            line_number=node.lineno,
            metadata=metadata,
            raw_calls=raw_calls,
            resolved_calls=[],
            is_entry_point=False,  # Will be determined later
            has_changes=False,     # Will be populated by diff detection
            documentation=docstring
        )

    def _extract_calls(self, func_node: ast.FunctionDef) -> List[str]:
        """Extract all function/method calls within a function."""
        calls = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node.func)
                if call_name:
                    calls.append(call_name)
        return calls

    def _get_call_name(self, node: ast.expr) -> Optional[str]:
        """Get the name of a function call.

        Examples:
        - foo() -> "foo"
        - obj.method() -> "obj.method"
        - module.func() -> "module.func"
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_call_name(node.value)
            if value_name:
                return f"{value_name}.{node.attr}"
            return node.attr
        return None

    def _extract_local_bindings(self, func_node: ast.FunctionDef) -> Dict[str, str]:
        """Extract local variable bindings (for type inference).

        Tracks patterns like:
            analyzer = StockAnalyzer()
            request = AnalysisRequest(...)

        Returns:
            Dict mapping variable name to type/class name
        """
        bindings = {}
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assign):
                # Handle simple assignment: var = Constructor()
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    var_name = node.targets[0].id
                    if isinstance(node.value, ast.Call):
                        constructor_name = self._get_call_name(node.value.func)
                        if constructor_name:
                            bindings[var_name] = constructor_name
        return bindings

    def _extract_function_local_imports(self, func_node: ast.FunctionDef) -> Dict[str, str]:
        """Extract imports that occur inside a function body.

        Handles patterns like:
            def my_function():
                from src.analyzer import analyze_stock
                result = analyze_stock()

        Also handles imports inside try/except or if statements:
            def my_function():
                try:
                    from src.analyzer import analyze_stock
                except ImportError:
                    pass

        Returns:
            Dict mapping name to qualified import path
        """
        local_imports = {}

        # Walk the entire function body (including nested blocks)
        for node in ast.walk(func_node):
            # Skip nested function definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node is not func_node:
                    continue

            if isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    qualified = f"{module}.{alias.name}" if module else alias.name
                    local_imports[name] = qualified

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    local_imports[name] = alias.name

        return local_imports

    def _extract_http_decorator(self, func_node: ast.FunctionDef) -> tuple[Optional[str], Optional[str]]:
        """Extract HTTP method and route from FastAPI/Flask decorators.

        Examples:
        - @app.post("/analyze") -> ("POST", "/analyze")
        - @app.get("/health") -> ("GET", "/health")
        - @app.route("/analyze", methods=["POST"]) -> ("POST", "/analyze")

        Returns:
            (method, route) tuple, or (None, None) if no HTTP decorator
        """
        for decorator in func_node.decorator_list:
            # FastAPI: @app.post("/path")
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    # Check for app.post, app.get, etc.
                    if decorator.func.attr in ('post', 'get', 'put', 'delete', 'patch'):
                        method = decorator.func.attr.upper()
                        path = self._extract_path_from_args(decorator)
                        if path:
                            return method, path

                    # Flask: @app.route("/path", methods=["POST"])
                    elif decorator.func.attr == 'route':
                        path = self._extract_path_from_args(decorator)
                        method = self._extract_method_from_flask_route(decorator) or "GET"
                        if path:
                            return method, path

        return None, None

    def _extract_path_from_args(self, call_node: ast.Call) -> Optional[str]:
        """Extract path string from decorator call arguments."""
        # First positional argument is usually the path
        if call_node.args and isinstance(call_node.args[0], ast.Constant):
            return call_node.args[0].value

        # Check keyword arguments for 'path'
        for keyword in call_node.keywords:
            if keyword.arg == 'path' and isinstance(keyword.value, ast.Constant):
                return keyword.value.value

        return None

    def _extract_method_from_flask_route(self, call_node: ast.Call) -> Optional[str]:
        """Extract HTTP method from Flask @app.route decorator."""
        for keyword in call_node.keywords:
            if keyword.arg == 'methods':
                # methods=["POST", "GET"]
                if isinstance(keyword.value, ast.List):
                    # Return first method in list
                    if keyword.value.elts and isinstance(keyword.value.elts[0], ast.Constant):
                        return keyword.value.elts[0].value
        return None
