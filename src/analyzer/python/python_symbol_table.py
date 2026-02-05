"""Python-specific symbol table with AST-based analysis."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..core.symbol import Symbol, SymbolTable


@dataclass
class ClassSymbol:
    """Represents a Python class in the symbol table."""
    name: str                               # Class name (e.g., "StockAnalyzer")
    qualified_name: str                     # Full name (e.g., "src.stock_analyzer.StockAnalyzer")
    methods: Dict[str, Symbol] = field(default_factory=dict)  # method_name -> Symbol
    base_classes: List[str] = field(default_factory=list)     # Base class names


class PythonSymbolTable(SymbolTable):
    """Symbol table for Python modules with proper AST-based semantics."""

    def __init__(self, module_name: str = ""):
        super().__init__(language="python")
        self.module_name = module_name
        self.imports: Dict[str, str] = {}           # name -> qualified_name
        self.classes: Dict[str, ClassSymbol] = {}   # class_name -> ClassSymbol
        self.functions: Dict[str, Symbol] = {}      # function_name -> Symbol

    def add_symbol(self, symbol: Symbol) -> None:
        """Add a symbol to the table."""
        self.symbols[symbol.qualified_name] = symbol

        # Also track in appropriate category
        if "is_class_method" in symbol.metadata and symbol.metadata["is_class_method"]:
            # This is a method, already handled in ClassSymbol
            pass
        else:
            # Top-level function
            self.functions[symbol.name] = symbol

    def add_class(self, class_symbol: ClassSymbol) -> None:
        """Add a class to the symbol table."""
        self.classes[class_symbol.name] = class_symbol

        # Add class methods to main symbol table
        for method in class_symbol.methods.values():
            self.symbols[method.qualified_name] = method

    def add_import(self, name: str, qualified_name: str) -> None:
        """Add an import mapping.

        Args:
            name: Name used in code (e.g., "StockAnalyzer" or "sa")
            qualified_name: Fully qualified name (e.g., "src.stock_analyzer.StockAnalyzer")
        """
        self.imports[name] = qualified_name

    def lookup(self, name: str, context: Optional[str] = None) -> Optional[Symbol]:
        """Look up a symbol by name.

        Args:
            name: Symbol name (function/class/method)
            context: Optional context (module or class name)

        Returns:
            Symbol if found, None otherwise
        """
        # Try exact qualified name
        if context:
            qualified = f"{context}.{name}"
            if qualified in self.symbols:
                return self.symbols[qualified]

        # Try current module
        qualified = f"{self.module_name}.{name}"
        if qualified in self.symbols:
            return self.symbols[qualified]

        # Try imports
        if name in self.imports:
            imported_name = self.imports[name]
            if imported_name in self.symbols:
                return self.symbols[imported_name]

        # Try direct function lookup
        if name in self.functions:
            return self.functions[name]

        return None

    def get_class(self, name: str) -> Optional[ClassSymbol]:
        """Get a class symbol by name.

        Args:
            name: Class name (simple or qualified)

        Returns:
            ClassSymbol if found, None otherwise
        """
        # Try direct lookup
        if name in self.classes:
            return self.classes[name]

        # Try imports
        if name in self.imports:
            imported_name = self.imports[name]
            # Extract class name from qualified name
            class_name = imported_name.split('.')[-1]
            if class_name in self.classes:
                return self.classes[class_name]

        # Try qualified name
        for class_symbol in self.classes.values():
            if class_symbol.qualified_name == name:
                return class_symbol

        return None

    def resolve_type(self, type_name: str) -> Optional[str]:
        """Resolve a type name to its qualified name.

        Used for type inference: when we see x = ClassName(), resolve ClassName.

        Args:
            type_name: Type name (e.g., "StockAnalyzer")

        Returns:
            Qualified name if found, None otherwise
        """
        # Check if it's a class in this module
        if type_name in self.classes:
            return self.classes[type_name].qualified_name

        # Check imports
        if type_name in self.imports:
            return self.imports[type_name]

        return None
