"""Cross-language call resolver."""

from typing import Dict, List

from .language_bridge import LanguageBridge
from .symbol import SymbolTable


class CrossLanguageResolver:
    """Resolves calls that cross language boundaries.

    Uses registered LanguageBridges to map calls from one language
    to targets in another language (e.g., shell → HTTP → Python).
    """

    def __init__(self):
        self.bridges: List[LanguageBridge] = []

    def register_bridge(self, bridge: LanguageBridge) -> None:
        """Register a cross-language bridge.

        Args:
            bridge: LanguageBridge implementation
        """
        self.bridges.append(bridge)
        print(f"Registered bridge: {bridge.get_bridge_name()}")

    def resolve_cross_language_calls(
        self,
        symbol_tables: Dict[str, SymbolTable]
    ) -> Dict[str, List[str]]:
        """Resolve all cross-language calls using registered bridges.

        Args:
            symbol_tables: Map from language name to SymbolTable

        Returns:
            Map from source qualified_name to list of target qualified_names
        """
        cross_refs = {}

        for bridge in self.bridges:
            try:
                refs = bridge.resolve(symbol_tables)
                # Merge references from this bridge
                for source, targets in refs.items():
                    if source not in cross_refs:
                        cross_refs[source] = []
                    cross_refs[source].extend(targets)
            except Exception as e:
                print(f"Warning: Bridge {bridge.get_bridge_name()} failed: {e}")

        return cross_refs

    def apply_cross_refs(
        self,
        symbol_tables: Dict[str, SymbolTable],
        cross_refs: Dict[str, List[str]]
    ) -> None:
        """Apply cross-language references to symbols.

        Updates symbol.resolved_calls with cross-language targets.

        Args:
            symbol_tables: Map from language name to SymbolTable
            cross_refs: Cross-language references from resolve_cross_language_calls
        """
        for lang, table in symbol_tables.items():
            for symbol in table.get_all_symbols():
                if symbol.qualified_name in cross_refs:
                    # Add cross-language targets to resolved_calls
                    targets = cross_refs[symbol.qualified_name]
                    symbol.resolved_calls.extend(targets)
                    print(f"  {symbol.qualified_name} → {targets}")
