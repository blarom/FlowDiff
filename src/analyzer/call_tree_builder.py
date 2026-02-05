"""
Call tree builder for Python projects.

Builds hierarchical function call trees by analyzing:
1. Function definitions (name, parameters, return type)
2. Function calls within each function
3. Call relationships to build a tree structure
4. Cross-language calls (shell scripts → HTTP → Python)
"""

import ast
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from .llm_entry_point_filter import LLMEntryPointFilter, EntryPointCandidate
    from .llm_providers import LLMProvider, create_provider, auto_detect_provider
except ImportError:
    # LLM filtering not available
    LLMEntryPointFilter = None
    EntryPointCandidate = None
    LLMProvider = None
    create_provider = None
    auto_detect_provider = None

try:
    from .shell_parser import parse_shell_script, ShellCommand
    from .http_endpoint_detector import extract_http_endpoints, build_endpoint_map, resolve_http_call
except ImportError:
    # Cross-language analysis not available
    parse_shell_script = None
    ShellCommand = None
    extract_http_endpoints = None
    build_endpoint_map = None
    resolve_http_call = None


@dataclass
class FunctionInfo:
    """Information about a single function."""
    name: str
    qualified_name: str  # e.g., "src.analyzer.main"
    file_path: str
    file_name: str  # Just the filename (e.g., "test_sqlite_manual.py")
    line_number: int
    parameters: List[str]  # Parameter names
    return_type: Optional[str]  # Return type if annotated
    calls: List[str]  # Functions this function calls
    called_by: List[str] = field(default_factory=list)  # Functions that call this
    local_variables: List[str] = field(default_factory=list)  # Local vars
    local_bindings: Dict[str, str] = field(default_factory=dict)  # var_name -> class_name
    is_entry_point: bool = False  # True if this is a real entry point

    # Cross-language metadata
    language: str = "python"  # "python", "shell", "http_endpoint"
    http_method: Optional[str] = None  # For HTTP endpoints: "GET", "POST", etc.
    http_route: Optional[str] = None  # For HTTP endpoints: "/analyze", "/health"


@dataclass
class CallTreeNode:
    """A node in the call tree."""
    function: FunctionInfo
    children: List['CallTreeNode'] = field(default_factory=list)
    depth: int = 0
    is_expanded: bool = False  # UI state


class CallTreeBuilder:
    """Builds function call trees from Python source files."""

    def __init__(self, project_root: Path, use_llm_filtering: bool = True, llm_provider: Optional['LLMProvider'] = None):
        """Initialize the call tree builder.

        Args:
            project_root: Root directory of the Python project
            use_llm_filtering: Use LLM to filter entry points (default: True)
            llm_provider: LLM provider to use (if None, auto-detects)
        """
        self.project_root = project_root.resolve()
        self.functions: Dict[str, FunctionInfo] = {}  # qualified_name -> FunctionInfo
        self.module_imports: Dict[str, Dict[str, str]] = {}  # module -> {name: source}
        self.use_llm_filtering = use_llm_filtering
        self.llm_provider = llm_provider
        self.http_endpoint_map: Dict[str, str] = {}  # "METHOD /path" -> "module.function"

    @staticmethod
    def should_exclude_from_entry_points(file_path: Path) -> bool:
        """Determine if file should be DEPRIORITIZED in entry point detection.

        These files can still be entry points, but are candidates for filtering.
        Used to give hints to LLM about what's likely not a production entry point.

        Args:
            file_path: Path to Python file

        Returns:
            True if file is likely test/debug/example code
        """
        path_str = str(file_path).lower()

        # Deprioritize patterns (tests, debug, examples, archive, admin tools)
        deprioritize_patterns = [
            '/tests/',
            '/test/',
            'test_',
            '/debug/',
            '/archive/',
            '/archived/',
            '/testing/',
            '/examples/',
            'example_',
            '/backtesting/',  # Backtesting is example code
            '/tools/',
            '/management/',
            '/scripts/',
            '/admin/',
            'conftest.py',
            '/old/',
            '/backup/',
        ]

        return any(pattern in path_str for pattern in deprioritize_patterns)

    def analyze_project(self, python_files: List[Path]) -> List[CallTreeNode]:
        """Analyze a Python project and build call trees.

        Args:
            python_files: List of .py files to analyze

        Returns:
            List of root CallTreeNode objects (entry points)
        """
        # Step 0: Find and parse shell scripts (cross-language support)
        if parse_shell_script is not None:
            shell_scripts = self._find_shell_scripts()
            print(f"Found {len(shell_scripts)} shell scripts")
            for script_path in shell_scripts:
                self._parse_shell_script(script_path)

        # Step 1: Parse all Python functions
        for file_path in python_files:
            self._parse_file(file_path)

        # Step 2: Build HTTP endpoint map (for cross-language HTTP → Python resolution)
        if extract_http_endpoints is not None:
            self._build_http_endpoint_map(python_files)

        # Step 3: Resolve function calls to qualified names
        self._resolve_calls()

        # Step 4: Resolve cross-language calls (shell → HTTP → Python)
        if parse_shell_script is not None:
            self._resolve_http_calls()

        # Step 5: Build call-by relationships
        self._build_relationships()

        # Step 6: Identify entry points (functions not called by anyone)
        self._identify_entry_points()

        # Step 7: Build trees from entry points
        trees = self._build_trees()

        return trees

    def _parse_file(self, file_path: Path) -> None:
        """Parse a Python file and extract function information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
                tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return

        # Get module name from file path
        module_name = self._path_to_module(file_path)

        # Extract imports for this module
        self.module_imports[module_name] = self._extract_imports(tree)

        # Check if file has __main__ guard and what it calls
        main_guard_calls = self._find_main_guard_calls(tree)

        # Check if this is a script entry point (e.g., server.py with uvicorn.run)
        # BEFORE excluding based on path
        script_entry = self._detect_script_entry_point(file_path, source, tree)
        if script_entry:
            self.functions[script_entry.qualified_name] = script_entry

        # Extract functions and methods
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Process both top-level functions and class methods
                if self._is_top_level(node, tree):
                    # Top-level function
                    func_info = self._extract_function_info(
                        node, module_name, file_path, main_guard_calls, class_name=None
                    )
                    self.functions[func_info.qualified_name] = func_info
                elif self._is_class_method(node, tree):
                    # Class method - extract with class name
                    class_name = self._get_parent_class_name(node, tree)
                    if class_name:
                        func_info = self._extract_function_info(
                            node, module_name, file_path, main_guard_calls, class_name=class_name
                        )
                        self.functions[func_info.qualified_name] = func_info

    def _is_top_level(self, func_node: ast.FunctionDef, tree: ast.Module) -> bool:
        """Check if a function is defined at module level (not nested)."""
        for node in tree.body:
            if node is func_node:
                return True
        return False

    def _is_class_method(self, func_node: ast.FunctionDef, tree: ast.Module) -> bool:
        """Check if a function is defined inside a class."""
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for class_node in node.body:
                    if class_node is func_node:
                        return True
        return False

    def _get_parent_class_name(self, func_node: ast.FunctionDef, tree: ast.Module) -> Optional[str]:
        """Get the name of the class that contains this method."""
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for class_node in node.body:
                    if class_node is func_node:
                        return node.name
        return None

    def _extract_function_info(self, node: ast.FunctionDef, module_name: str,
                              file_path: Path, main_guard_calls: Set[str],
                              class_name: Optional[str] = None) -> FunctionInfo:
        """Extract information from a function definition.

        Args:
            node: AST node for the function
            module_name: Module name (e.g., "src.analyzer")
            file_path: Path to the source file
            main_guard_calls: Set of functions called in __main__ block
            class_name: If this is a class method, the class name
        """
        func_name = node.name

        # Build qualified name: module.function or module.ClassName.method
        if class_name:
            qualified_name = f"{module_name}.{class_name}.{func_name}"
        else:
            qualified_name = f"{module_name}.{func_name}"

        # Extract parameters
        parameters = [arg.arg for arg in node.args.args]

        # Extract return type if annotated
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)

        # Extract function calls
        calls = self._extract_calls(node)

        # Extract local variables
        local_vars = self._extract_local_vars(node)

        # Extract local bindings (var = Constructor())
        local_bindings = self._extract_local_bindings(node)

        # Check if this looks like a CLI script
        uses_argparse = self._uses_cli_parsing(node, calls)

        # Determine if this is a real entry point
        # NOTE: We don't exclude test files here - let them be entry points
        # The LLM and UI "Hide Tests" button will handle filtering
        is_entry = self._is_real_entry_point(func_name, main_guard_calls, uses_argparse)

        return FunctionInfo(
            name=func_name,
            qualified_name=qualified_name,
            file_path=str(file_path),
            file_name=file_path.name,
            line_number=node.lineno,
            parameters=parameters,
            return_type=return_type,
            calls=calls,
            local_variables=local_vars,
            local_bindings=local_bindings,
            is_entry_point=is_entry
        )

    def _extract_calls(self, func_node: ast.FunctionDef) -> List[str]:
        """Extract function calls from a function body."""
        calls = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node.func)
                if call_name:
                    calls.append(call_name)
        return calls

    def _get_call_name(self, node: ast.expr) -> Optional[str]:
        """Get the name of a function call."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_call_name(node.value)
            if value_name:
                return f"{value_name}.{node.attr}"
            return node.attr
        return None

    def _extract_local_vars(self, func_node: ast.FunctionDef) -> List[str]:
        """Extract local variable names from a function."""
        local_vars = []
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        local_vars.append(target.id)
        return list(set(local_vars))  # Deduplicate

    def _extract_local_bindings(self, func_node: ast.FunctionDef) -> Dict[str, str]:
        """Extract local variable bindings (constructor calls).

        Tracks patterns like:
            analyzer = StockAnalyzer()
            request = AnalysisRequest(...)

        Returns:
            Dict mapping variable name to constructor/class name
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

    def _extract_imports(self, tree: ast.Module) -> Dict[str, str]:
        """Extract import mappings for a module."""
        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = alias.name
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports[name] = f"{module}.{alias.name}" if module else alias.name
        return imports

    def _path_to_module(self, file_path: Path) -> str:
        """Convert file path to module name."""
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            rel_path = file_path

        parts = list(rel_path.parts[:-1]) + [rel_path.stem]
        return '.'.join(parts)

    def _resolve_calls(self) -> None:
        """Resolve function call names to qualified names.

        Only processes Python functions - shell scripts are handled separately.
        """
        for func_info in self.functions.values():
            # Skip non-Python functions (shell scripts, etc.)
            if func_info.language != "python":
                continue

            module_name = '.'.join(func_info.qualified_name.split('.')[:-1])
            imports = self.module_imports.get(module_name, {})

            resolved_calls = []
            for call_name in func_info.calls:
                qualified = self._resolve_call_name(
                    call_name, module_name, imports, func_info.local_bindings
                )
                if qualified:
                    resolved_calls.append(qualified)

            func_info.calls = resolved_calls

    def _resolve_call_name(self, call_name: str, current_module: str,
                          imports: Dict[str, str],
                          local_bindings: Dict[str, str]) -> Optional[str]:
        """Resolve a call name to a qualified function name.

        Args:
            call_name: Raw call name (e.g., "analyze", "analyzer.analyze", "AnalysisRequest")
            current_module: Current module name
            imports: Import mappings for current module
            local_bindings: Local variable bindings (var_name -> class_name)

        Returns:
            Qualified function name or None if not resolvable
        """
        # Handle instance method calls: obj.method()
        # Check if obj is a local variable bound to a class
        if '.' in call_name:
            parts = call_name.split('.')
            obj_name = parts[0]

            # Check if obj is a local variable
            if obj_name in local_bindings:
                class_name = local_bindings[obj_name]
                method_name = '.'.join(parts[1:])

                # Try to resolve the class name first
                resolved_class = self._resolve_call_name(class_name, current_module, imports, {})
                if resolved_class:
                    # Build class.method qualified name
                    candidate = f"{resolved_class}.{method_name}"
                    if candidate in self.functions:
                        return candidate

        # Direct match in imports
        if call_name in imports:
            imported_module = imports[call_name]
            # Check if this is a function we know about
            if imported_module in self.functions:
                return imported_module

        # Check if it's a function in the same module
        qualified = f"{current_module}.{call_name}"
        if qualified in self.functions:
            return qualified

        # Try resolving qualified calls (obj.method)
        parts = call_name.split('.')
        for i in range(len(parts), 0, -1):
            prefix = '.'.join(parts[:i])
            if prefix in imports:
                module = imports[prefix]
                suffix = '.'.join(parts[i:])
                candidate = f"{module}.{suffix}" if suffix else module
                if candidate in self.functions:
                    return candidate

        return None

    def _build_relationships(self) -> None:
        """Build called-by relationships."""
        for func_info in self.functions.values():
            for called_func in func_info.calls:
                if called_func in self.functions:
                    self.functions[called_func].called_by.append(func_info.qualified_name)

    def _identify_entry_points(self) -> None:
        """Mark functions that are real entry points.

        Entry points are:
        1. Functions explicitly marked during parsing (main() with __main__ guard, test functions)
        2. Functions not called by other functions in the project (but only if not utility-like)
        3. If LLM filtering enabled, use Claude to determine from user's perspective

        NOTE: Test/debug/example files are NOT excluded - they appear as entry points
              and can be hidden via the UI "Hide Tests" button or filtered by LLM
        """
        # First pass: keep explicitly marked entry points
        # Second pass: for functions not called, only mark as entry if they look like entry points
        for func_info in self.functions.values():
            if func_info.is_entry_point:
                # Already marked as entry point
                continue

            if not func_info.called_by:
                # Not called by anyone - check if it looks like a utility function
                # Utility functions typically have descriptive names suggesting reusability
                if self._looks_like_entry_point(func_info.name):
                    func_info.is_entry_point = True

        # Third pass: Use LLM filtering if enabled
        # The LLM will use the deprioritization hints to filter test/debug/examples
        if self.use_llm_filtering:
            self._apply_llm_filtering()

    def _apply_llm_filtering(self) -> None:
        """Use LLM to filter entry points from user's perspective."""
        if LLMEntryPointFilter is None:
            print("Warning: LLM filtering requested but llm_entry_point_filter not available")
            return

        # Build list of candidates (all functions currently marked as entry points)
        candidates = []
        for func_info in self.functions.values():
            if func_info.is_entry_point:
                # Check if uses CLI parsing
                uses_cli = False
                try:
                    # Re-parse to check for CLI usage
                    with open(func_info.file_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                        tree = ast.parse(source, filename=func_info.file_path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef) and node.name == func_info.name:
                                uses_cli = self._uses_cli_parsing(node, func_info.calls)
                                break
                except Exception:
                    pass

                # Check if called in main guard
                called_in_main = False
                try:
                    with open(func_info.file_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                        tree = ast.parse(source, filename=func_info.file_path)
                        main_calls = self._find_main_guard_calls(tree)
                        called_in_main = func_info.name in main_calls
                except Exception:
                    pass

                candidate = EntryPointCandidate(
                    name=func_info.name,
                    qualified_name=func_info.qualified_name,
                    file_name=func_info.file_name,
                    file_path=func_info.file_path,
                    parameters=func_info.parameters,
                    uses_cli_parsing=uses_cli,
                    called_in_main_guard=called_in_main,
                    is_test=func_info.name.startswith('test_'),
                    is_private=self._is_private_or_internal(func_info.name),
                    called_by=func_info.called_by,
                    calls=func_info.calls
                )
                candidates.append(candidate)

        if not candidates:
            return

        # Call LLM filter
        try:
            llm_filter = LLMEntryPointFilter(provider=self.llm_provider)
            project_name = self.project_root.name

            provider_name = llm_filter.provider.get_name()
            print(f"\n🤖 Using {provider_name} to filter {len(candidates)} entry point candidates...")
            filtered_qualified_names = llm_filter.filter_entry_points(candidates, project_name)
            print(f"✓ LLM selected {len(filtered_qualified_names)} entry points\n")

            # Update entry point flags based on LLM decision
            for func_info in self.functions.values():
                if func_info.qualified_name in filtered_qualified_names:
                    func_info.is_entry_point = True
                else:
                    func_info.is_entry_point = False

        except ValueError as e:
            print(f"Warning: LLM filtering failed: {e}")
            print("Continuing with hard-coded rules only")
        except Exception as e:
            print(f"Warning: Unexpected error in LLM filtering: {e}")
            print("Continuing with hard-coded rules only")

    def _is_real_entry_point(self, func_name: str, main_guard_calls: Set[str],
                            uses_argparse: bool) -> bool:
        """Determine if a function is a real entry point.

        Conservative but recognizes CLI scripts.

        Args:
            func_name: Name of the function
            main_guard_calls: Set of function names called in __main__ block
            uses_argparse: Whether function uses argparse/sys.argv (CLI script)

        Returns:
            True if this is definitely an entry point
        """
        # NEVER treat private/internal functions as entry points
        if self._is_private_or_internal(func_name):
            return False

        # Test functions (pytest, unittest patterns)
        if func_name.startswith('test_'):
            return True

        # Setup/teardown functions for tests
        if func_name in ('setUp', 'tearDown', 'setUpClass', 'tearDownClass',
                        'setup_method', 'teardown_method', 'setup_class', 'teardown_class'):
            return True

        # Function called in __main__ block
        if func_name in main_guard_calls:
            return True

        # Function uses CLI argument parsing (command-line script)
        if uses_argparse:
            return True

        # Exact matches only (not run_something, just "run")
        if func_name in ('main', 'run', 'execute', 'start', 'init', 'initialize'):
            return True

        # Default: NOT an entry point (be skeptical)
        return False

    def _uses_cli_parsing(self, func_node: ast.FunctionDef, calls: List[str]) -> bool:
        """Check if function uses command-line argument parsing.

        Detects:
        - argparse.ArgumentParser
        - sys.argv usage
        - click decorators
        - typer decorators

        Returns:
            True if function appears to be a CLI script
        """
        # Check function calls for argparse/CLI parsing
        cli_patterns = ['ArgumentParser', 'parse_args', 'add_argument']
        for call in calls:
            for pattern in cli_patterns:
                if pattern in call:
                    return True

        # Check for sys.argv access in function body
        for node in ast.walk(func_node):
            # sys.argv access
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    if node.value.id == 'sys' and node.attr == 'argv':
                        return True

            # Subscript like sys.argv[1]
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Attribute):
                    attr = node.value
                    if isinstance(attr.value, ast.Name):
                        if attr.value.id == 'sys' and attr.attr == 'argv':
                            return True

        # Check for click/typer decorators
        if hasattr(func_node, 'decorator_list'):
            for decorator in func_node.decorator_list:
                decorator_name = None
                if isinstance(decorator, ast.Name):
                    decorator_name = decorator.id
                elif isinstance(decorator, ast.Attribute):
                    decorator_name = decorator.attr
                elif isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Name):
                        decorator_name = decorator.func.id
                    elif isinstance(decorator.func, ast.Attribute):
                        decorator_name = decorator.func.attr

                if decorator_name in ('command', 'group', 'option', 'argument'):
                    return True

        return False

    def _is_private_or_internal(self, func_name: str) -> bool:
        """Check if function name indicates it's private/internal.

        Returns True for functions that should NEVER be entry points.
        """
        # Starts with underscore (private/internal)
        if func_name.startswith('_'):
            return True

        # Dunder methods (special methods)
        if func_name.startswith('__') and func_name.endswith('__'):
            return True

        return False

    def _looks_like_entry_point(self, func_name: str) -> bool:
        """Check if an uncalled function looks like it could be an entry point.

        VERY CONSERVATIVE - default to False.
        Better to miss an entry point than show noise.

        This is only called for functions that:
        - Are NOT already marked as entry points
        - Are NOT called by any other function

        These are "orphaned" functions - be VERY skeptical.
        """
        # NEVER private/internal
        if self._is_private_or_internal(func_name):
            return False

        # Test functions (only remaining legitimate case)
        if func_name.startswith('test_'):
            return True

        # Only these EXACT names (last resort for orphaned functions)
        if func_name in ('main', 'run', 'execute', 'start', 'init', 'initialize'):
            return True

        # Everything else: NOT an entry point
        # This includes functions like:
        # - check_aapl_peg (utility function, should be called by something)
        # - detect_conglomerate (utility function, should be called by something)
        # - calculate_metrics (utility function)
        # - Any other orphaned utilities
        #
        # If they're legitimate entry points, they should either:
        # 1. Use argparse/sys.argv (CLI scripts)
        # 2. Be called in __main__ block
        # 3. Be named exactly: main, run, execute, start, init, initialize
        return False

    def _detect_script_entry_point(self, file_path: Path, source: str, tree: ast.Module) -> Optional[FunctionInfo]:
        """Detect if a file is a script entry point (e.g., server.py with uvicorn.run).

        Script entry points are files that:
        - Have a __main__ guard
        - Call server startup functions directly (not through a function)
        - Should be treated as entry points even without function definitions

        Args:
            file_path: Path to the Python file
            source: Source code of the file
            tree: Parsed AST tree

        Returns:
            FunctionInfo representing the script entry point, or None if not a script entry point
        """
        # Only check production files (not tests/debug/examples)
        if self.should_exclude_from_entry_points(file_path):
            return None

        # Must have __main__ guard
        if 'if __name__ == "__main__"' not in source and "if __name__ == '__main__'" not in source:
            return None

        # Look for server startup patterns in the source
        server_patterns = [
            'uvicorn.run',
            'app.run(',
            'flask.run(',
            'gunicorn',
            'waitress.serve',
            'fastapi',
            'starlette',
        ]

        # Check if any server patterns exist
        has_server_pattern = any(pattern in source for pattern in server_patterns)

        if not has_server_pattern:
            return None

        # This is a script entry point - create synthetic function
        module_name = self._path_to_module(file_path)
        script_name = file_path.stem  # e.g., "server" from "server.py"

        # Create synthetic function info
        qualified_name = f"{module_name}.{script_name}"

        return FunctionInfo(
            name=f"<script:{script_name}>",  # Mark as script
            qualified_name=qualified_name,
            file_path=str(file_path),
            file_name=file_path.name,
            line_number=1,
            parameters=[],
            return_type=None,
            calls=[],  # Scripts typically don't call project functions directly
            local_variables=[],
            is_entry_point=True  # Scripts are always entry points
        )

    def _find_main_guard_calls(self, tree: ast.Module) -> Set[str]:
        """Find function names called inside if __name__ == "__main__": block.

        Returns:
            Set of function names that are explicitly called in __main__ block
        """
        main_calls = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if condition is: __name__ == "__main__"
                if isinstance(node.test, ast.Compare):
                    comp = node.test
                    if (isinstance(comp.left, ast.Name) and comp.left.id == '__name__' and
                        len(comp.ops) == 1 and isinstance(comp.ops[0], ast.Eq) and
                        len(comp.comparators) == 1 and
                        isinstance(comp.comparators[0], ast.Constant) and
                        comp.comparators[0].value == '__main__'):

                        # Found __main__ block, extract function calls from it
                        for stmt in node.body:
                            main_calls.update(self._extract_call_names_from_node(stmt))

        return main_calls

    def _extract_call_names_from_node(self, node: ast.AST) -> Set[str]:
        """Extract all function call names from an AST node."""
        calls = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child.func)
                if call_name and '.' not in call_name:  # Only direct function calls, not methods
                    calls.add(call_name)
        return calls

    def _has_main_guard(self, tree: ast.Module) -> bool:
        """Check if the module has if __name__ == "__main__": guard."""
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check if condition is: __name__ == "__main__"
                if isinstance(node.test, ast.Compare):
                    comp = node.test
                    if (isinstance(comp.left, ast.Name) and comp.left.id == '__name__' and
                        len(comp.ops) == 1 and isinstance(comp.ops[0], ast.Eq) and
                        len(comp.comparators) == 1 and
                        isinstance(comp.comparators[0], ast.Constant) and
                        comp.comparators[0].value == '__main__'):
                        return True
        return False

    def _find_shell_scripts(self) -> List[Path]:
        """Find all shell scripts (.sh files) in the project."""
        shell_scripts = []
        for path in self.project_root.rglob('*.sh'):
            # Skip hidden directories, venv, node_modules, etc.
            if any(part.startswith('.') or part in ('venv', 'node_modules', '__pycache__')
                   for part in path.parts):
                continue
            shell_scripts.append(path)
        return shell_scripts

    def _parse_shell_script(self, script_path: Path) -> None:
        """Parse a shell script and create FunctionInfo for it.

        This creates a FunctionInfo entry for the shell script itself,
        with calls populated from extracted commands (curl, python, bash).
        """
        # Parse shell script to extract commands
        commands = parse_shell_script(script_path)

        if not commands:
            return

        # Create qualified name for the shell script
        try:
            rel_path = script_path.relative_to(self.project_root)
        except ValueError:
            rel_path = script_path

        # Convert scripts/analyze.sh -> scripts.analyze
        module_name = '.'.join(rel_path.parts[:-1] + (rel_path.stem,))
        qualified_name = module_name

        # Build calls list from extracted commands
        calls = []
        for cmd in commands:
            if cmd.type == "http_call":
                # HTTP call: represent as "METHOD /path"
                http_call = f"{cmd.method} {cmd.target}"
                calls.append(http_call)
            elif cmd.type == "python_invoke":
                # Direct Python invocation: add as call
                # e.g., "python -m module" -> "module"
                # e.g., "python script.py" -> "script"
                calls.append(cmd.target)
            elif cmd.type == "script_invoke":
                # Script-to-script call
                calls.append(cmd.target)

        # Create FunctionInfo for the shell script
        func_info = FunctionInfo(
            name=script_path.name,  # e.g., "analyze.sh"
            qualified_name=qualified_name,
            file_path=str(script_path),
            file_name=script_path.name,
            line_number=1,
            parameters=[],
            return_type=None,
            calls=calls,
            called_by=[],
            local_variables=[],
            is_entry_point=True,  # Shell scripts are always entry points
            language="shell"
        )

        self.functions[qualified_name] = func_info

    def _build_http_endpoint_map(self, python_files: List[Path]) -> None:
        """Build mapping from HTTP endpoints to Python functions.

        Scans Python files for FastAPI/Flask route decorators and builds
        a mapping from "METHOD /path" to "module.function".
        """
        # Extract HTTP endpoints from all Python files
        for file_path in python_files:
            module_name = self._path_to_module(file_path)
            endpoints = extract_http_endpoints(file_path, module_name)

            for endpoint in endpoints:
                key = f"{endpoint.method} {endpoint.path}"
                self.http_endpoint_map[key] = endpoint.handler_function

                # Also annotate the function info with HTTP metadata
                if endpoint.handler_function in self.functions:
                    func_info = self.functions[endpoint.handler_function]
                    func_info.http_method = endpoint.method
                    func_info.http_route = endpoint.path

        print(f"Found {len(self.http_endpoint_map)} HTTP endpoints")

    def _resolve_http_calls(self) -> None:
        """Resolve HTTP calls from shell scripts to Python handlers.

        Replaces "POST /analyze" with "api.analyze" in shell script calls.
        """
        for func_info in self.functions.values():
            if func_info.language == "shell":
                resolved_calls = []
                for call in func_info.calls:
                    # Check if this is an HTTP call pattern
                    if call.startswith(("GET ", "POST ", "PUT ", "DELETE ", "PATCH ")):
                        # Try to resolve to Python function
                        handler = self.http_endpoint_map.get(call)
                        if handler:
                            resolved_calls.append(handler)
                            print(f"  Resolved {call} → {handler}")
                        else:
                            # Keep unresolved HTTP call as-is
                            resolved_calls.append(call)
                    else:
                        # Not an HTTP call, keep as-is
                        resolved_calls.append(call)

                func_info.calls = resolved_calls

    def _build_trees(self) -> List[CallTreeNode]:
        """Build call trees from entry points."""
        entry_points = [f for f in self.functions.values() if f.is_entry_point]

        trees = []
        for entry in entry_points:
            tree = self._build_tree_recursive(entry, depth=0, visited=set())
            trees.append(tree)

        return trees

    def _build_tree_recursive(self, func_info: FunctionInfo, depth: int, visited: Set[str]) -> CallTreeNode:
        """Recursively build a call tree."""
        node = CallTreeNode(function=func_info, depth=depth)

        # Prevent infinite recursion (circular calls)
        if func_info.qualified_name in visited:
            return node

        visited.add(func_info.qualified_name)

        # Build children from called functions
        for called_name in func_info.calls:
            if called_name in self.functions:
                child_func = self.functions[called_name]
                child_node = self._build_tree_recursive(child_func, depth + 1, visited.copy())
                node.children.append(child_node)

        return node
