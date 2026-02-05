"""Shell script analyzer using pattern matching."""

import re
from pathlib import Path
from typing import List

from ..core.language_analyzer import LanguageAnalyzer
from ..core.symbol import Symbol, SymbolTable


class ShellSymbolTable(SymbolTable):
    """Symbol table for shell scripts."""

    def __init__(self):
        super().__init__(language="shell")

    def add_symbol(self, symbol: Symbol) -> None:
        """Add a symbol to the table."""
        self.symbols[symbol.qualified_name] = symbol

    def lookup(self, name: str, context: str = None) -> Symbol:
        """Look up a shell script by name."""
        return self.symbols.get(name)


class ShellAnalyzer(LanguageAnalyzer):
    """Pattern-based shell script analyzer.

    Extracts commands using regex patterns (no AST available for shell).

    Detects:
    - curl commands: HTTP calls
    - python invocations: python script.py, python -m module
    - script invocations: ./other.sh, bash script.sh
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    def can_analyze(self, file_path: Path) -> bool:
        """Check if file is a shell script."""
        return file_path.suffix == '.sh'

    def build_symbol_table(self, file_path: Path) -> ShellSymbolTable:
        """Build symbol table for a single shell script.

        Creates one Symbol for the script itself, with raw_calls
        containing extracted commands.

        Args:
            file_path: Path to shell script

        Returns:
            ShellSymbolTable with script symbol
        """
        table = ShellSymbolTable()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, OSError) as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return table

        # Extract commands from script
        raw_calls = self._extract_commands(content)

        # Create symbol for the script
        qualified_name = self._script_to_qualified_name(file_path)
        script_symbol = Symbol(
            name=file_path.name,
            qualified_name=qualified_name,
            language="shell",
            file_path=str(file_path),
            line_number=1,
            metadata={},
            raw_calls=raw_calls,
            resolved_calls=[],
            is_entry_point=True  # Shell scripts are entry points
        )

        table.add_symbol(script_symbol)
        return table

    def merge_symbol_tables(self, tables: List[SymbolTable]) -> ShellSymbolTable:
        """Merge multiple shell symbol tables."""
        merged = ShellSymbolTable()

        for table in tables:
            if not isinstance(table, ShellSymbolTable):
                continue
            merged.symbols.update(table.symbols)

        return merged

    def resolve_calls(self, symbol_table: SymbolTable) -> None:
        """Shell calls are kept as-is; resolved by CrossLanguageResolver.

        Shell analyzer doesn't do intra-language resolution since most
        calls go to other languages (HTTP, Python).

        Args:
            symbol_table: ShellSymbolTable
        """
        # No intra-language resolution for shell
        # Bridges will handle cross-language resolution
        pass

    def get_language_name(self) -> str:
        """Return 'shell'."""
        return "shell"

    def _extract_commands(self, content: str) -> List[str]:
        """Extract commands from shell script content.

        Returns commands in special formats:
        - HTTP calls: "HTTP:METHOD:PATH" (e.g., "HTTP:POST:/analyze")
        - Python scripts: "PYTHON:SCRIPT" (e.g., "PYTHON:script.py")
        - Python modules: "PYTHON:MODULE" (e.g., "PYTHON:src.analyzer")

        Args:
            content: Shell script content

        Returns:
            List of command strings
        """
        commands = []

        # Extract curl commands (HTTP calls)
        commands.extend(self._extract_curl_commands(content))

        # Extract Python invocations
        commands.extend(self._extract_python_invocations(content))

        return commands

    def _extract_curl_commands(self, content: str) -> List[str]:
        """Extract curl HTTP calls.

        Patterns:
        - curl http://localhost:8000/analyze
        - curl -X POST "$SERVER_URL/analyze"
        - curl -s -X POST http://localhost:8000/api/analyze

        Returns:
            List of "HTTP:METHOD:PATH" strings
        """
        commands = []
        lines = content.split('\n')

        for line in lines:
            # Skip comments
            if line.strip().startswith('#'):
                continue

            if 'curl' not in line:
                continue

            # Extract HTTP method
            method = 'GET'  # Default
            if '-X POST' in line or '--request POST' in line:
                method = 'POST'
            elif '-X PUT' in line:
                method = 'PUT'
            elif '-X DELETE' in line:
                method = 'DELETE'
            elif '-X PATCH' in line:
                method = 'PATCH'

            # Extract URL path
            url_patterns = [
                r'https?://[^\s"\']+(/[^\s"\']*)',      # http://localhost:8000/analyze
                r'\$[A-Z_]+(/[^\s"\']*)',                # $SERVER_URL/analyze
                r'"\$[A-Z_]+(/[^\s"\']*)"',              # "$SERVER_URL/analyze"
            ]

            path = None
            for pattern in url_patterns:
                match = re.search(pattern, line)
                if match:
                    path = match.group(1)
                    break

            if not path:
                # Try to extract any /path
                match = re.search(r'(/[a-zA-Z0-9_/-]+)', line)
                if match:
                    path = match.group(1)

            if path:
                commands.append(f"HTTP:{method}:{path}")

        return commands

    def _extract_python_invocations(self, content: str) -> List[str]:
        """Extract Python invocations.

        Patterns:
        - python script.py -> "PYTHON:script.py"
        - python -m module.name -> "PYTHON:module.name"
        - python3 src/analyzer.py -> "PYTHON:src/analyzer.py"

        Returns:
            List of "PYTHON:TARGET" strings
        """
        commands = []
        lines = content.split('\n')

        for line in lines:
            # Skip comments
            if line.strip().startswith('#'):
                continue

            if 'python' not in line:
                continue

            # Pattern: python -m module.name
            match = re.search(r'python[0-9.]* -m ([a-zA-Z0-9_.]+)', line)
            if match:
                module = match.group(1)
                commands.append(f"PYTHON:{module}")
                continue

            # Pattern: python script.py or python src/analyzer.py
            match = re.search(r'python[0-9.]* ([a-zA-Z0-9_/.]+\.py)', line)
            if match:
                script = match.group(1)
                commands.append(f"PYTHON:{script}")

        return commands

    def _script_to_qualified_name(self, script_path: Path) -> str:
        """Convert script path to qualified name.

        Examples:
            scripts/analyze.sh -> scripts.analyze
            tools/setup.sh -> tools.setup

        Args:
            script_path: Path to shell script

        Returns:
            Qualified name
        """
        try:
            rel_path = script_path.relative_to(self.project_root)
        except ValueError:
            rel_path = script_path

        # Convert to module-like name
        parts = list(rel_path.parts[:-1]) + [rel_path.stem]
        return '.'.join(parts)
