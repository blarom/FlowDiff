# FlowDiff Multi-Language Architecture

## Vision

A language-agnostic static analysis tool that:
1. Detects the language of each file
2. Uses appropriate "compilation" strategy per language (AST for Python, patterns for shell)
3. Builds separate symbol tables per language
4. Maps between symbol tables for cross-language calls (shell → HTTP → Python)
5. Produces a unified call graph spanning all languages

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FlowDiff Orchestrator                     │
│  - Discovers files                                            │
│  - Dispatches to language analyzers                           │
│  - Builds unified call graph                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Language Registry                          │
│  - Maps file extensions to analyzers                          │
│  - LanguageAnalyzer factory                                   │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Python     │  │    Shell     │  │  HTTP Bridge │
    │   Analyzer   │  │   Analyzer   │  │  (FastAPI)   │
    └──────────────┘  └──────────────┘  └──────────────┘
            │                 │                 │
            ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Python     │  │    Shell     │  │  HTTP        │
    │ Symbol Table │  │ Symbol Table │  │ Endpoint Map │
    └──────────────┘  └──────────────┘  └──────────────┘
                              │
                              ▼
            ┌─────────────────────────────────────┐
            │   Cross-Language Resolver            │
            │  - HTTP → Python function mapping    │
            │  - Shell → Python script mapping     │
            │  - Script → Script mapping           │
            └─────────────────────────────────────┘
                              │
                              ▼
            ┌─────────────────────────────────────┐
            │      Unified Call Graph              │
            │  - Language-agnostic nodes/edges     │
            │  - Supports all call types           │
            └─────────────────────────────────────┘
```

---

## Core Abstractions

### 1. Symbol (Language-Agnostic)

A callable unit in any language:

```python
@dataclass
class Symbol:
    """A callable unit (function, method, script, endpoint)."""
    name: str                    # Display name (e.g., "analyze", "analyze.sh")
    qualified_name: str          # Unique identifier (e.g., "src.api.analyze")
    language: str                # "python", "shell", "http_endpoint"
    file_path: str               # Source file path
    line_number: int             # Definition line

    # Type-specific metadata
    metadata: Dict[str, Any]     # Language-specific data

    # Call tracking
    raw_calls: List[str]         # Raw call strings before resolution
    resolved_calls: List[str]    # Qualified names after resolution
```

### 2. SymbolTable (Per-Language)

Abstract base class for language-specific symbol tables:

```python
class SymbolTable(ABC):
    """Base class for language-specific symbol tables."""

    def __init__(self, language: str):
        self.language = language
        self.symbols: Dict[str, Symbol] = {}  # qualified_name -> Symbol

    @abstractmethod
    def add_symbol(self, symbol: Symbol) -> None:
        """Add a symbol to the table."""
        pass

    @abstractmethod
    def lookup(self, name: str, context: Optional[str] = None) -> Optional[Symbol]:
        """Look up a symbol by name (with optional context)."""
        pass

    @abstractmethod
    def get_all_symbols(self) -> List[Symbol]:
        """Get all symbols in this table."""
        pass
```

### 3. LanguageAnalyzer (Per-Language)

Abstract base class for language analyzers:

```python
class LanguageAnalyzer(ABC):
    """Base class for language-specific analyzers."""

    @abstractmethod
    def can_analyze(self, file_path: Path) -> bool:
        """Return True if this analyzer can handle the file."""
        pass

    @abstractmethod
    def build_symbol_table(self, file_path: Path) -> SymbolTable:
        """Build symbol table for a single file."""
        pass

    @abstractmethod
    def merge_symbol_tables(self, tables: List[SymbolTable]) -> SymbolTable:
        """Merge multiple symbol tables (e.g., all .py files)."""
        pass

    @abstractmethod
    def resolve_calls(self, symbol_table: SymbolTable) -> None:
        """Resolve raw calls to qualified names within this language."""
        pass
```

### 4. CrossLanguageResolver

Bridges between different language symbol tables:

```python
class CrossLanguageResolver:
    """Resolves calls that cross language boundaries."""

    def __init__(self):
        self.bridges: List[LanguageBridge] = []

    def register_bridge(self, bridge: LanguageBridge) -> None:
        """Register a cross-language bridge."""
        self.bridges.append(bridge)

    def resolve_cross_language_calls(
        self,
        symbol_tables: Dict[str, SymbolTable]
    ) -> Dict[str, List[str]]:
        """
        Resolve calls that cross language boundaries.

        Returns:
            Mapping from qualified_name to list of cross-language call targets
        """
        cross_refs = {}
        for bridge in self.bridges:
            refs = bridge.resolve(symbol_tables)
            cross_refs.update(refs)
        return cross_refs
```

### 5. LanguageBridge (Cross-Language Mapping)

Abstract interface for mapping between languages:

```python
class LanguageBridge(ABC):
    """Bridge between two languages."""

    @abstractmethod
    def can_bridge(self, from_lang: str, to_lang: str) -> bool:
        """Check if this bridge handles these languages."""
        pass

    @abstractmethod
    def resolve(self, symbol_tables: Dict[str, SymbolTable]) -> Dict[str, List[str]]:
        """
        Resolve cross-language calls.

        Returns:
            Mapping from source qualified_name to target qualified_names
        """
        pass
```

---

## Language-Specific Implementations

### Python Analyzer (AST-Based)

**Strategy**: Use Python's AST module to build a proper symbol table with type inference.

```python
class PythonSymbolTable(SymbolTable):
    """Symbol table for Python modules."""

    def __init__(self):
        super().__init__(language="python")
        self.imports: Dict[str, str] = {}           # name -> qualified_name
        self.classes: Dict[str, ClassSymbol] = {}   # name -> ClassSymbol
        self.functions: Dict[str, Symbol] = {}      # name -> Symbol
        self.module_name: str = ""

    class ClassSymbol:
        """Represents a Python class."""
        name: str
        qualified_name: str
        methods: Dict[str, Symbol]      # method_name -> Symbol
        base_classes: List[str]         # Inheritance

class PythonAnalyzer(LanguageAnalyzer):
    """AST-based Python analyzer."""

    def can_analyze(self, file_path: Path) -> bool:
        return file_path.suffix == '.py'

    def build_symbol_table(self, file_path: Path) -> PythonSymbolTable:
        """
        Parse Python file with AST and build symbol table.

        Steps:
        1. Parse AST
        2. Extract imports (from X import Y, import Z)
        3. Extract class definitions + methods
        4. Extract top-level functions
        5. For each function/method:
           - Infer local variable types (x = ClassName())
           - Extract raw function calls
        """
        tree = ast.parse(file_path.read_text())
        table = PythonSymbolTable()

        # Extract imports, classes, functions
        visitor = PythonASTVisitor(table, file_path)
        visitor.visit(tree)

        return table

    def resolve_calls(self, symbol_table: PythonSymbolTable) -> None:
        """
        Resolve calls using symbol table + type inference.

        Examples:
        - analyzer.analyze() where analyzer: StockAnalyzer
          → Look up local scope: analyzer has type StockAnalyzer
          → Look up symbol: StockAnalyzer.analyze
          → Resolve to: src.stock_analyzer.StockAnalyzer.analyze

        - StockAnalyzer() constructor
          → Look up symbol: StockAnalyzer
          → Resolve to: src.stock_analyzer.StockAnalyzer.__init__
        """
        resolver = PythonCallResolver(symbol_table)

        for symbol in symbol_table.get_all_symbols():
            resolved = []
            for call in symbol.raw_calls:
                qualified = resolver.resolve(call, symbol)
                if qualified:
                    resolved.append(qualified)
            symbol.resolved_calls = resolved
```

**Key Components**:
1. **PythonASTVisitor**: Walks AST to extract symbols
2. **TypeInferenceEngine**: Infers types from assignments
3. **PythonCallResolver**: Resolves calls using types + symbol table

### Shell Analyzer (Pattern-Based)

**Strategy**: Use regex patterns to extract commands (no "compilation" possible).

```python
class ShellSymbolTable(SymbolTable):
    """Symbol table for shell scripts."""

    def __init__(self):
        super().__init__(language="shell")
        self.scripts: Dict[str, Symbol] = {}  # script_path -> Symbol

class ShellAnalyzer(LanguageAnalyzer):
    """Pattern-based shell analyzer."""

    def can_analyze(self, file_path: Path) -> bool:
        return file_path.suffix == '.sh'

    def build_symbol_table(self, file_path: Path) -> ShellSymbolTable:
        """
        Parse shell script with regex patterns.

        Extract:
        - curl commands: curl -X POST "$URL/analyze"
        - Python invocations: python script.py, python -m module
        - Script invocations: ./other.sh, bash setup.sh
        """
        content = file_path.read_text()
        table = ShellSymbolTable()

        # Create symbol for the script itself
        script_symbol = Symbol(
            name=file_path.name,
            qualified_name=self._script_to_qualified_name(file_path),
            language="shell",
            file_path=str(file_path),
            line_number=1,
            metadata={},
            raw_calls=self._extract_commands(content),
            resolved_calls=[]
        )

        table.add_symbol(script_symbol)
        return table

    def _extract_commands(self, content: str) -> List[str]:
        """Extract curl/python/script commands from shell script."""
        commands = []

        # curl -X POST /path → "HTTP:POST:/path"
        curl_pattern = r'curl.*-X\s+(GET|POST|PUT|DELETE|PATCH).*?([\/\w-]+)'
        for match in re.finditer(curl_pattern, content):
            method, path = match.groups()
            commands.append(f"HTTP:{method}:{path}")

        # python script.py → "PYTHON:script.py"
        python_pattern = r'python[0-9.]*\s+([\w\/\.]+\.py)'
        for match in re.finditer(python_pattern, content):
            commands.append(f"PYTHON:{match.group(1)}")

        # python -m module → "PYTHON:module"
        module_pattern = r'python[0-9.]*\s+-m\s+([\w\.]+)'
        for match in re.finditer(module_pattern, content):
            commands.append(f"PYTHON:{match.group(1)}")

        return commands

    def resolve_calls(self, symbol_table: ShellSymbolTable) -> None:
        """Shell calls are kept as-is; resolved by CrossLanguageResolver."""
        # Shell analyzer doesn't resolve - that's the bridge's job
        pass
```

### HTTP Bridge (Cross-Language)

**Strategy**: Map HTTP endpoints to Python handlers using decorator detection.

```python
class HTTPToPythonBridge(LanguageBridge):
    """Bridge from shell HTTP calls to Python FastAPI/Flask handlers."""

    def can_bridge(self, from_lang: str, to_lang: str) -> bool:
        return from_lang == "shell" and to_lang == "python"

    def resolve(self, symbol_tables: Dict[str, SymbolTable]) -> Dict[str, List[str]]:
        """
        Map HTTP calls to Python handlers.

        Process:
        1. Extract HTTP endpoints from Python files (@app.post("/analyze"))
        2. Build endpoint map: "POST:/analyze" -> "src.api.analyze"
        3. For each shell script, replace HTTP calls with Python handlers
        """
        python_table = symbol_tables.get("python")
        shell_table = symbol_tables.get("shell")

        if not python_table or not shell_table:
            return {}

        # Build endpoint map from Python decorators
        endpoint_map = self._build_endpoint_map(python_table)

        # Resolve shell HTTP calls
        cross_refs = {}
        for symbol in shell_table.get_all_symbols():
            resolved = []
            for call in symbol.raw_calls:
                if call.startswith("HTTP:"):
                    # "HTTP:POST:/analyze" -> look up in endpoint_map
                    parts = call.split(":", 2)
                    if len(parts) == 3:
                        method, path = parts[1], parts[2]
                        key = f"{method}:{path}"
                        if key in endpoint_map:
                            resolved.append(endpoint_map[key])

            if resolved:
                cross_refs[symbol.qualified_name] = resolved

        return cross_refs

    def _build_endpoint_map(self, python_table: PythonSymbolTable) -> Dict[str, str]:
        """
        Extract HTTP endpoints from Python symbol table.

        Look for metadata indicating FastAPI/Flask decorators:
        - @app.post("/analyze") -> "POST:/analyze"
        - @app.get("/health") -> "GET:/health"
        """
        endpoint_map = {}

        for symbol in python_table.get_all_symbols():
            if "http_method" in symbol.metadata and "http_route" in symbol.metadata:
                method = symbol.metadata["http_method"]
                route = symbol.metadata["http_route"]
                key = f"{method}:{route}"
                endpoint_map[key] = symbol.qualified_name

        return endpoint_map
```

---

## Project Structure

```
src/analyzer/
├── core/
│   ├── __init__.py
│   ├── symbol.py              # Symbol, SymbolTable base classes
│   ├── language_analyzer.py   # LanguageAnalyzer base class
│   ├── language_bridge.py     # LanguageBridge base class
│   ├── call_graph.py          # Unified call graph
│   └── orchestrator.py        # Main FlowDiff orchestrator
│
├── python/
│   ├── __init__.py
│   ├── python_analyzer.py     # PythonAnalyzer
│   ├── python_symbol_table.py # PythonSymbolTable
│   ├── ast_visitor.py         # PythonASTVisitor
│   ├── type_inference.py      # Type inference engine
│   └── call_resolver.py       # PythonCallResolver
│
├── shell/
│   ├── __init__.py
│   ├── shell_analyzer.py      # ShellAnalyzer
│   └── shell_symbol_table.py  # ShellSymbolTable
│
├── bridges/
│   ├── __init__.py
│   ├── http_to_python.py      # HTTPToPythonBridge
│   └── python_to_python.py    # PythonToPythonBridge (imports)
│
├── registry.py                # Language registry
└── cross_language_resolver.py # CrossLanguageResolver
```

---

## Orchestration Flow

```python
class FlowDiffOrchestrator:
    """Main orchestrator for multi-language analysis."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.registry = LanguageRegistry()
        self.resolver = CrossLanguageResolver()

        # Register analyzers
        self.registry.register(PythonAnalyzer())
        self.registry.register(ShellAnalyzer())

        # Register bridges
        self.resolver.register_bridge(HTTPToPythonBridge())

    def analyze(self) -> CallGraph:
        """
        Full analysis pipeline.

        1. Discover files
        2. Group by language
        3. Build symbol tables per language
        4. Resolve intra-language calls
        5. Resolve cross-language calls
        6. Build unified call graph
        """

        # Step 1: Discover files
        files = self._discover_files()

        # Step 2: Group by language
        files_by_lang = self._group_by_language(files)

        # Step 3: Build symbol tables
        symbol_tables = {}
        for lang, lang_files in files_by_lang.items():
            analyzer = self.registry.get_analyzer(lang)
            tables = [analyzer.build_symbol_table(f) for f in lang_files]
            symbol_tables[lang] = analyzer.merge_symbol_tables(tables)

        # Step 4: Resolve intra-language calls
        for lang, table in symbol_tables.items():
            analyzer = self.registry.get_analyzer(lang)
            analyzer.resolve_calls(table)

        # Step 5: Resolve cross-language calls
        cross_refs = self.resolver.resolve_cross_language_calls(symbol_tables)

        # Step 6: Build unified call graph
        call_graph = self._build_call_graph(symbol_tables, cross_refs)

        return call_graph
```

---

## Benefits

1. **Language-Agnostic**: Core abstractions work for any language
2. **Proper Analysis**: Uses "compilation" (AST) where possible, patterns where needed
3. **Extensible**: Add new languages by implementing LanguageAnalyzer
4. **Cross-Language**: Explicit bridges for shell → HTTP → Python
5. **Maintainable**: Clear separation of concerns, no monolithic logic
6. **Accurate**: Type inference + symbol tables = definitive resolution

## Adding New Languages

To add a new language (e.g., JavaScript):

```python
# 1. Implement LanguageAnalyzer
class JavaScriptAnalyzer(LanguageAnalyzer):
    def can_analyze(self, file_path: Path) -> bool:
        return file_path.suffix == '.js'

    def build_symbol_table(self, file_path: Path) -> SymbolTable:
        # Use Esprima, Acorn, or regex patterns
        pass

# 2. Implement SymbolTable
class JavaScriptSymbolTable(SymbolTable):
    # Track JS functions, classes, imports
    pass

# 3. Implement Bridge (if needed)
class HTTPToJavaScriptBridge(LanguageBridge):
    # Map Express.js routes to handlers
    pass

# 4. Register
orchestrator.registry.register(JavaScriptAnalyzer())
orchestrator.resolver.register_bridge(HTTPToJavaScriptBridge())
```

---

## Next Steps

1. Implement core abstractions (Symbol, SymbolTable, LanguageAnalyzer)
2. Implement PythonAnalyzer with AST + type inference
3. Implement ShellAnalyzer with pattern matching
4. Implement HTTPToPythonBridge
5. Implement FlowDiffOrchestrator
6. Test on StockAnalysis (shell → HTTP → Python flow)
