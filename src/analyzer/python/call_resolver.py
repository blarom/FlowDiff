"""Python call resolver with type inference."""

from typing import Optional, Dict

from ..core.symbol import Symbol
from .python_symbol_table import PythonSymbolTable


class PythonCallResolver:
    """Resolves Python function calls using symbol table and type inference.

    Resolution strategies:
    1. Instance method calls (obj.method where obj is a local variable)
    2. Direct imports (imported_func())
    3. Same-module calls (local_func())
    4. Qualified calls (module.func())
    5. Constructor calls (ClassName())
    """

    def __init__(self, symbol_table: PythonSymbolTable):
        self.symbol_table = symbol_table

    def resolve(self, call_name: str, calling_symbol: Symbol) -> Optional[str]:
        """Resolve a call name to its qualified name.

        Args:
            call_name: Raw call name (e.g., "analyze", "analyzer.analyze", "self.layer.method")
            calling_symbol: The symbol making the call (for context)

        Returns:
            Qualified name if resolved, None otherwise
        """
        # Get local bindings from calling symbol's metadata
        local_bindings = calling_symbol.metadata.get("local_bindings", {})

        # Get function-local imports from calling symbol's metadata
        function_local_imports = calling_symbol.metadata.get("function_local_imports", {})

        # Get class instance variables if this is a method
        instance_vars = {}
        if calling_symbol.metadata.get("is_class_method"):
            # Extract class name from qualified name
            # e.g., "src.analyzer.StockAnalyzer.analyze" -> "StockAnalyzer"
            parts = calling_symbol.qualified_name.split('.')
            if len(parts) >= 2:
                class_name = parts[-2]
                class_symbol = self.symbol_table.get_class(class_name)
                if class_symbol:
                    instance_vars = class_symbol.instance_vars

        # Strategy 1: Instance method calls (obj.method() or self.attr.method())
        if '.' in call_name:
            result = self._resolve_method_call(call_name, local_bindings, instance_vars)
            if result:
                return result

        # Strategy 2: Function-local imports (NEW!)
        if call_name in function_local_imports:
            imported_name = function_local_imports[call_name]
            if imported_name in self.symbol_table.symbols:
                return imported_name

        # Strategy 3: Constructor calls (ClassName())
        type_name = self.symbol_table.resolve_type(call_name)
        if type_name:
            # It's a class constructor
            # Check if class has __init__ method
            class_symbol = self.symbol_table.get_class(call_name)
            if class_symbol and "__init__" in class_symbol.methods:
                return class_symbol.methods["__init__"].qualified_name
            # No explicit __init__, but it's still a valid call
            return type_name

        # Strategy 4: Direct import match (module-level imports)
        if call_name in self.symbol_table.imports:
            imported_name = self.symbol_table.imports[call_name]
            if imported_name in self.symbol_table.symbols:
                return imported_name

        # Strategy 5: Same-module function
        qualified = f"{self.symbol_table.module_name}.{call_name}"
        if qualified in self.symbol_table.symbols:
            return qualified

        # Strategy 6: Qualified calls (module.func or obj.method via imports)
        result = self._resolve_qualified_call(call_name)
        if result:
            return result

        return None

    def _resolve_method_call(
        self,
        call_name: str,
        local_bindings: Dict[str, str],
        instance_vars: Dict[str, str]
    ) -> Optional[str]:
        """Resolve instance method call using type inference.

        Example:
            analyzer.analyze() where analyzer = StockAnalyzer()
            -> local_bindings: {"analyzer": "StockAnalyzer"}
            -> Look up StockAnalyzer class
            -> Find analyze method
            -> Return: src.stock_analyzer.StockAnalyzer.analyze

            self.computation_layer.compute_all_metrics()
            -> instance_vars: {"computation_layer": "ComputationLayer"}
            -> Look up ComputationLayer class
            -> Find compute_all_metrics method
            -> Return: src.data.computation_layer.ComputationLayer.compute_all_metrics

        Args:
            call_name: Call like "obj.method" or "self.attr.method"
            local_bindings: Map from variable names to type names
            instance_vars: Map from instance variable names to type names (from class's __init__)

        Returns:
            Qualified method name if resolved
        """
        parts = call_name.split('.', 1)
        if len(parts) != 2:
            return None

        obj_name, rest = parts

        # Handle self.attr.method() pattern
        if obj_name == "self" and '.' in rest:
            attr_parts = rest.split('.', 1)
            if len(attr_parts) == 2:
                attr_name, method_name = attr_parts
                # Look up instance variable type
                if attr_name in instance_vars:
                    type_name = instance_vars[attr_name]
                    return self._resolve_type_method(type_name, method_name)

        # Handle obj.method() pattern
        method_name = rest

        # Check if obj is a local variable with known type
        if obj_name in local_bindings:
            type_name = local_bindings[obj_name]
            return self._resolve_type_method(type_name, method_name)

        # Check if obj is self and rest is an instance variable's method
        if obj_name == "self" and method_name in instance_vars:
            # This shouldn't happen, but handle it gracefully
            return None

        return None

    def _resolve_type_method(self, type_name: str, method_name: str) -> Optional[str]:
        """Resolve a method on a given type.

        Args:
            type_name: Type/class name (e.g., "ComputationLayer" or "get_computation_layer")
            method_name: Method to call (e.g., "compute_all_metrics")

        Returns:
            Qualified method name if resolved
        """
        # First, resolve the type_name to a qualified name
        # type_name could be:
        # 1. A class name: "ComputationLayer"
        # 2. A function name: "get_computation_layer"
        # 3. Already qualified: "src.data.computation_layer.ComputationLayer"

        # Try to resolve as a type (class)
        qualified_type = self.symbol_table.resolve_type(type_name)
        if qualified_type:
            # It's a class, look up the method
            class_symbol = self.symbol_table.get_class(qualified_type.split('.')[-1])
            if class_symbol and method_name in class_symbol.methods:
                return class_symbol.methods[method_name].qualified_name
            # Don't return None here - continue to try other strategies

        # Try to resolve as a function that returns a type
        # Check if it's in imports
        if type_name in self.symbol_table.imports:
            qualified_func = self.symbol_table.imports[type_name]
            if qualified_func in self.symbol_table.symbols:
                symbol = self.symbol_table.symbols[qualified_func]
                return_type = symbol.metadata.get("return_type")
                if return_type:
                    # Recursively resolve using the return type
                    return self._resolve_type_method(return_type, method_name)

        # Try as same-module function
        qualified_func = f"{self.symbol_table.module_name}.{type_name}"
        if qualified_func in self.symbol_table.symbols:
            symbol = self.symbol_table.symbols[qualified_func]
            return_type = symbol.metadata.get("return_type")
            if return_type:
                # Recursively resolve using the return type
                return self._resolve_type_method(return_type, method_name)

        # Try looking it up directly in symbols (might already be qualified)
        if type_name in self.symbol_table.symbols:
            symbol = self.symbol_table.symbols[type_name]
            return_type = symbol.metadata.get("return_type")
            if return_type:
                # Recursively resolve using the return type
                return self._resolve_type_method(return_type, method_name)

        return None

    def _resolve_qualified_call(self, call_name: str) -> Optional[str]:
        """Resolve qualified call like module.func or package.module.func.

        Strategy:
        - Try progressively shorter prefixes in imports
        - Build candidate qualified names

        Args:
            call_name: Qualified call name

        Returns:
            Resolved qualified name if found
        """
        parts = call_name.split('.')

        # Try each prefix length
        for i in range(len(parts), 0, -1):
            prefix = '.'.join(parts[:i])

            # Check if prefix is in imports
            if prefix in self.symbol_table.imports:
                module = self.symbol_table.imports[prefix]
                suffix = '.'.join(parts[i:])
                candidate = f"{module}.{suffix}" if suffix else module

                if candidate in self.symbol_table.symbols:
                    return candidate

        return None
