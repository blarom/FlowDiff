"""Symbol and SymbolTable abstractions."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


@dataclass
class Symbol:
    """A callable unit in any language (function, method, script, endpoint).

    This is the universal representation of anything that can be called
    across all supported languages.
    """
    name: str                           # Display name (e.g., "analyze", "analyze.sh")
    qualified_name: str                 # Unique identifier (e.g., "src.api.analyze")
    language: str                       # "python", "shell", "http_endpoint"
    file_path: str                      # Source file path
    line_number: int                    # Definition line

    # Type-specific metadata (language-specific details)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Call tracking
    raw_calls: List[str] = field(default_factory=list)       # Raw call strings before resolution
    resolved_calls: List[str] = field(default_factory=list)  # Qualified names after resolution

    # Entry point tracking
    is_entry_point: bool = False

    # Diff/change tracking (for dynamic tree expansion)
    has_changes: bool = False                                 # True if this symbol was modified (e.g., git diff)

    # Documentation
    documentation: Optional[str] = None                       # Docstring/comments for this symbol

    # Source code content
    code_content: Optional[str] = None                        # Raw source code of the symbol (for diff detection)

    def __hash__(self):
        return hash(self.qualified_name)

    def __eq__(self, other):
        if not isinstance(other, Symbol):
            return False
        return self.qualified_name == other.qualified_name


class SymbolTable(ABC):
    """Base class for language-specific symbol tables.

    Each language implements its own symbol table to store symbols
    in a way that makes sense for that language's semantics.
    """

    def __init__(self, language: str):
        self.language = language
        self.symbols: Dict[str, Symbol] = {}  # qualified_name -> Symbol

    @abstractmethod
    def add_symbol(self, symbol: Symbol) -> None:
        """Add a symbol to the table."""
        pass

    @abstractmethod
    def lookup(self, name: str, context: Optional[str] = None) -> Optional[Symbol]:
        """Look up a symbol by name (with optional context).

        Args:
            name: Symbol name to look up
            context: Optional context (e.g., module name, class name)

        Returns:
            Symbol if found, None otherwise
        """
        pass

    def get_symbol(self, qualified_name: str) -> Optional[Symbol]:
        """Get symbol by qualified name."""
        return self.symbols.get(qualified_name)

    def get_all_symbols(self) -> List[Symbol]:
        """Get all symbols in this table."""
        return list(self.symbols.values())

    def __len__(self):
        return len(self.symbols)
