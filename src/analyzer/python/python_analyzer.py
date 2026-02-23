"""Python language analyzer using AST."""

import ast
from pathlib import Path
from typing import List

from ..core.language_analyzer import LanguageAnalyzer
from ..core.symbol import SymbolTable
from .python_symbol_table import PythonSymbolTable
from .ast_visitor import PythonASTVisitor
from .call_resolver import PythonCallResolver


class PythonAnalyzer(LanguageAnalyzer):
    """AST-based Python analyzer with proper symbol table and type inference."""

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    def can_analyze(self, file_path: Path) -> bool:
        """Check if file is a Python file."""
        return file_path.suffix == '.py'

    def build_symbol_table(self, file_path: Path) -> PythonSymbolTable:
        """Build symbol table for a single Python file using AST.

        Steps:
        1. Parse file with ast.parse()
        2. Visit AST to extract:
           - Imports
           - Classes and methods
           - Top-level functions
           - Function calls
           - Local variable bindings

        Args:
            file_path: Path to Python file

        Returns:
            PythonSymbolTable with all symbols from this file
        """
        # Determine module name from file path
        module_name = self._path_to_module(file_path)

        # Parse AST
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            # Return empty symbol table
            return PythonSymbolTable(module_name=module_name)

        # Build symbol table by visiting AST
        symbol_table = PythonSymbolTable(module_name=module_name)
        visitor = PythonASTVisitor(symbol_table, file_path, source)
        visitor.visit(tree)

        return symbol_table

    def merge_symbol_tables(self, tables: List[SymbolTable]) -> PythonSymbolTable:
        """Merge multiple Python symbol tables.

        Creates a project-wide symbol table by merging all per-file tables.

        Args:
            tables: List of PythonSymbolTable objects

        Returns:
            Merged PythonSymbolTable
        """
        merged = PythonSymbolTable(module_name="<project>")

        for table in tables:
            if not isinstance(table, PythonSymbolTable):
                continue

            # Merge symbols
            merged.symbols.update(table.symbols)

            # Merge imports (may have duplicates, that's OK)
            merged.imports.update(table.imports)

            # Merge classes
            merged.classes.update(table.classes)

            # Merge functions
            merged.functions.update(table.functions)

        return merged

    def resolve_calls(self, symbol_table: SymbolTable) -> None:
        """Resolve Python function calls using type inference.

        Updates symbol.resolved_calls for all symbols in the table.

        Args:
            symbol_table: PythonSymbolTable to resolve calls within
        """
        if not isinstance(symbol_table, PythonSymbolTable):
            return

        resolver = PythonCallResolver(symbol_table)

        for symbol in symbol_table.get_all_symbols():
            resolved = []
            for raw_call in symbol.raw_calls:
                qualified = resolver.resolve(raw_call, symbol)
                if qualified:
                    resolved.append(qualified)

            symbol.resolved_calls = resolved

    def mark_entry_points(self, symbol_table: SymbolTable) -> None:
        """Mark functions as entry points based on heuristics.

        Entry points include:
        - Test functions (test_* or in test_*.py files)
        - HTTP endpoint handlers
        - Functions with if __name__ == '__main__' guards

        Args:
            symbol_table: PythonSymbolTable to mark entry points in
        """
        if not isinstance(symbol_table, PythonSymbolTable):
            return

        for symbol in symbol_table.get_all_symbols():
            # Skip if already marked
            if symbol.is_entry_point:
                continue

            # HTTP endpoints are always entry points
            if symbol.metadata.get("http_method"):
                symbol.is_entry_point = True
                continue

            # Test functions: test_* prefix OR in test_*.py files
            file_name = Path(symbol.file_path).name
            if symbol.name.startswith("test_") or file_name.startswith("test_"):
                symbol.is_entry_point = True
                continue

            # Functions called from __main__ guard
            # (Would need to track this during AST parsing - for now skip)

    def get_language_name(self) -> str:
        """Return 'python'."""
        return "python"

    def _path_to_module(self, file_path: Path) -> str:
        """Convert file path to Python module name.

        Examples:
            /path/to/src/analyzer.py -> src.analyzer
            /path/to/foo/bar/baz.py -> foo.bar.baz

        Args:
            file_path: Path to Python file

        Returns:
            Dot-separated module name
        """
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            # File is outside project root
            rel_path = file_path

        # Remove .py extension and convert to module name
        parts = list(rel_path.parts[:-1]) + [rel_path.stem]
        return '.'.join(parts)
