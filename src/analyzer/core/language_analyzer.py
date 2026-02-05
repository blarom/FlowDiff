"""Language analyzer abstract base class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from .symbol import SymbolTable


class LanguageAnalyzer(ABC):
    """Base class for language-specific analyzers.

    Each supported language implements this interface to provide:
    1. File detection (can_analyze)
    2. Symbol table construction (build_symbol_table)
    3. Symbol table merging (merge_symbol_tables)
    4. Call resolution within the language (resolve_calls)
    """

    @abstractmethod
    def can_analyze(self, file_path: Path) -> bool:
        """Return True if this analyzer can handle the file.

        Args:
            file_path: Path to file

        Returns:
            True if this analyzer supports this file type
        """
        pass

    @abstractmethod
    def build_symbol_table(self, file_path: Path) -> SymbolTable:
        """Build symbol table for a single file.

        This is where the "compilation" happens:
        - For Python: Parse AST, extract functions/classes/methods
        - For shell: Extract commands with regex patterns
        - For other languages: Use appropriate parsing strategy

        Args:
            file_path: Path to source file

        Returns:
            SymbolTable containing symbols from this file
        """
        pass

    @abstractmethod
    def merge_symbol_tables(self, tables: List[SymbolTable]) -> SymbolTable:
        """Merge multiple symbol tables (e.g., all .py files in project).

        Args:
            tables: List of symbol tables to merge

        Returns:
            Single merged symbol table
        """
        pass

    @abstractmethod
    def resolve_calls(self, symbol_table: SymbolTable) -> None:
        """Resolve raw calls to qualified names within this language.

        This operates on symbol.raw_calls and populates symbol.resolved_calls.

        For Python:
            - Use type inference to resolve obj.method() calls
            - Use imports to resolve function calls
            - Use same-module lookup for local calls

        For shell:
            - Leave most calls unresolved (handled by bridges)

        Args:
            symbol_table: Symbol table to resolve calls within
        """
        pass

    @abstractmethod
    def get_language_name(self) -> str:
        """Return the name of this language (e.g., "python", "shell").

        Returns:
            Language name
        """
        pass
