"""HTTP to Python bridge for cross-language resolution."""

from typing import Dict, List

from ..core.language_bridge import LanguageBridge
from ..core.symbol import SymbolTable
from ..python.python_symbol_table import PythonSymbolTable
from ..shell.shell_analyzer import ShellSymbolTable


class HTTPToPythonBridge(LanguageBridge):
    """Bridge from shell HTTP calls to Python FastAPI/Flask handlers.

    Maps:
        "HTTP:POST:/analyze" -> "src.api.analyze"

    by detecting FastAPI decorators:
        @app.post("/analyze")
        def analyze(...): ...
    """

    def can_bridge(self, from_lang: str, to_lang: str) -> bool:
        """Check if this bridges shell HTTP calls to Python handlers."""
        return from_lang == "shell" and to_lang == "python"

    def resolve(
        self,
        symbol_tables: Dict[str, SymbolTable]
    ) -> Dict[str, List[str]]:
        """Resolve shell HTTP calls to Python handlers.

        Process:
        1. Build endpoint map from Python decorators
        2. Match shell HTTP calls against endpoints
        3. Return mapping from shell symbol to Python handler

        Args:
            symbol_tables: Map from language name to SymbolTable

        Returns:
            Map from shell script qualified_name to list of Python handlers
        """
        python_table = symbol_tables.get("python")
        shell_table = symbol_tables.get("shell")

        if not python_table or not shell_table:
            return {}

        # Build endpoint map from Python
        endpoint_map = self._build_endpoint_map(python_table)

        if not endpoint_map:
            return {}

        print(f"Built endpoint map with {len(endpoint_map)} entries")
        for key, handler in endpoint_map.items():
            print(f"  {key} -> {handler}")

        # Resolve shell HTTP calls
        cross_refs = {}

        for symbol in shell_table.get_all_symbols():
            resolved = []

            for raw_call in symbol.raw_calls:
                if raw_call.startswith("HTTP:"):
                    # Parse "HTTP:METHOD:PATH"
                    parts = raw_call.split(":", 2)
                    if len(parts) == 3:
                        _, method, path = parts
                        key = f"{method}:{path}"

                        if key in endpoint_map:
                            handler = endpoint_map[key]
                            resolved.append(handler)
                            print(f"  Resolved {raw_call} -> {handler}")

            if resolved:
                cross_refs[symbol.qualified_name] = resolved

        return cross_refs

    def _build_endpoint_map(self, python_table: PythonSymbolTable) -> Dict[str, str]:
        """Build map from HTTP endpoints to Python handlers.

        Looks for symbols with http_method and http_route metadata
        (extracted from @app.post decorators, etc.).

        Args:
            python_table: PythonSymbolTable with HTTP endpoints

        Returns:
            Map from "METHOD:PATH" to qualified function name
        """
        endpoint_map = {}

        for symbol in python_table.get_all_symbols():
            http_method = symbol.metadata.get("http_method")
            http_route = symbol.metadata.get("http_route")

            if http_method and http_route:
                key = f"{http_method}:{http_route}"
                endpoint_map[key] = symbol.qualified_name

        return endpoint_map
