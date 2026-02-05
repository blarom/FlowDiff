# FlowDiff Static Analysis Architecture Proposal

## Problem
Current approach uses text pattern matching to resolve function calls. This is brittle and doesn't truly understand code semantics.

## Solution: AST-Based Symbol Table + Type Inference

Instead of pattern matching, use proper static analysis techniques:

### 1. Symbol Table (Per Module)
Build a complete symbol table for each Python module:

```python
class SymbolTable:
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.imports = {}           # name -> qualified_name
        self.classes = {}           # class_name -> ClassSymbol
        self.functions = {}         # func_name -> FunctionSymbol
        self.variables = {}         # var_name -> type_hint

class ClassSymbol:
    def __init__(self, name: str, qualified_name: str):
        self.name = name
        self.qualified_name = qualified_name
        self.methods = {}           # method_name -> FunctionSymbol
        self.base_classes = []      # inheritance tracking

class FunctionSymbol:
    def __init__(self, name: str, qualified_name: str):
        self.name = name
        self.qualified_name = qualified_name
        self.parameters = []
        self.return_type = None
        self.local_scope = {}       # local var -> inferred type
        self.calls = []             # raw call names
```

### 2. Type Inference Engine
Infer types from assignments:

```python
class TypeInferenceEngine:
    def infer_assignment_type(self, assign_node: ast.Assign, symbol_table: SymbolTable) -> Optional[str]:
        """
        Infer type from assignment:
        - x = ClassName() -> type is ClassName
        - x = factory_func() -> look up return type annotation
        - x = imported_obj -> look up import
        """
        if isinstance(assign_node.value, ast.Call):
            # Constructor call or function call
            func_name = get_call_name(assign_node.value.func)

            # Check if it's a known class
            if func_name in symbol_table.classes:
                return symbol_table.classes[func_name].qualified_name

            # Check imports
            if func_name in symbol_table.imports:
                imported_qualified = symbol_table.imports[func_name]
                # Check if imported thing is a class
                if is_class(imported_qualified):
                    return imported_qualified

        return None
```

### 3. Call Resolution
Resolve calls using symbol table + inferred types:

```python
class CallResolver:
    def resolve(self, call_name: str, scope: Scope) -> Optional[str]:
        """
        Resolve call_name to qualified function name.

        Examples:
        - analyzer.analyze() where analyzer: StockAnalyzer
          -> resolve to src.stock_analyzer.StockAnalyzer.analyze

        - analyze_stock() in same module
          -> resolve to current_module.analyze_stock

        - StockAnalyzer() constructor
          -> resolve to src.stock_analyzer.StockAnalyzer.__init__
        """

        if '.' in call_name:
            # Method call: obj.method()
            obj_name, method_name = call_name.split('.', 1)

            # Look up obj's type in local scope
            obj_type = scope.get_variable_type(obj_name)
            if obj_type:
                # Look up method in that type's class
                class_symbol = self.get_class(obj_type)
                if class_symbol and method_name in class_symbol.methods:
                    return class_symbol.methods[method_name].qualified_name

        else:
            # Direct function call or constructor
            # Check current module
            if call_name in scope.symbol_table.functions:
                return scope.symbol_table.functions[call_name].qualified_name

            # Check imports
            if call_name in scope.symbol_table.imports:
                return scope.symbol_table.imports[call_name]

        return None
```

### 4. Analysis Pipeline

```
For each Python file:
1. Parse AST
2. Build SymbolTable:
   - Extract imports
   - Extract class definitions + methods
   - Extract top-level functions

3. For each function/method:
   - Build local scope
   - Infer types of local variables (from assignments)
   - Extract function calls (raw names)

4. Resolve all calls:
   - Use CallResolver with SymbolTable + type inference
   - Build qualified call graph
```

## Benefits

1. **Accurate**: Truly understands code structure, not guessing from patterns
2. **Maintainable**: No complex pattern rules to maintain
3. **Extensible**: Easy to add new resolution strategies
4. **Robust**: Handles OOP, local variables, complex imports naturally

## Implementation

**Phase 1**: Build SymbolTable infrastructure
- `src/analyzer/symbol_table.py` - SymbolTable, ClassSymbol, FunctionSymbol classes
- `src/analyzer/ast_walker.py` - AST visitor to build symbol tables

**Phase 2**: Type inference
- `src/analyzer/type_inference.py` - Infer types from assignments

**Phase 3**: Call resolution
- `src/analyzer/call_resolver.py` - Resolve calls using symbols + types

**Phase 4**: Integration
- Replace pattern-based logic in `call_tree_builder.py`
- Use proper static analysis pipeline

## Special Cases (Keep Pattern-Based)

For non-Python languages (shell scripts, HTTP calls), continue using pattern matching:
- Shell scripts: regex for curl/python invocations
- HTTP endpoints: decorator pattern matching

These are simple enough and don't need "compilation".
