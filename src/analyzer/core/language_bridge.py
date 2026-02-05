"""Language bridge for cross-language call resolution."""

from abc import ABC, abstractmethod
from typing import Dict, List

from .symbol import SymbolTable


class LanguageBridge(ABC):
    """Bridge between two languages for cross-language call resolution.

    Examples:
    - HTTPToPythonBridge: Maps HTTP calls in shell scripts to Python FastAPI handlers
    - PythonToShellBridge: Maps subprocess.run() to shell scripts
    """

    @abstractmethod
    def can_bridge(self, from_lang: str, to_lang: str) -> bool:
        """Check if this bridge handles calls from from_lang to to_lang.

        Args:
            from_lang: Source language (e.g., "shell")
            to_lang: Target language (e.g., "python")

        Returns:
            True if this bridge can resolve calls from -> to
        """
        pass

    @abstractmethod
    def resolve(
        self,
        symbol_tables: Dict[str, SymbolTable]
    ) -> Dict[str, List[str]]:
        """Resolve cross-language calls.

        This is called after all intra-language resolution is complete.

        Args:
            symbol_tables: Map from language name to SymbolTable

        Returns:
            Map from source qualified_name to list of target qualified_names

            Example:
            {
                "scripts.analyze": ["src.api.analyze"],  # shell → Python
            }
        """
        pass

    def get_bridge_name(self) -> str:
        """Return descriptive name for this bridge."""
        return self.__class__.__name__
