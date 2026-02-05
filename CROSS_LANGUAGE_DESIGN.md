# Cross-Language Call Tree Design

## Problem

FlowDiff currently only analyzes Python-to-Python function calls. Real-world projects have entry points in:
- **Shell scripts** (`.sh`) that call HTTP APIs via `curl`
- **HTTP APIs** (FastAPI, Flask) that call Python functions
- **CLI tools** that invoke Python modules

**Example (StockAnalysis)**:
```
analyze.sh                              [Shell script - TRUE entry point]
  └─ curl POST http://localhost:8000/analyze
      └─ @app.post("/analyze")          [FastAPI endpoint]
          └─ analyze_stock()            [Python function]
              └─ extract_data()         [Python function]
```

FlowDiff should show this full cross-language call tree.

---

## Architecture

### Phase 1: Shell Script Parsing

**Parse `.sh` files** to detect:
- `curl` commands (HTTP requests)
- Direct Python invocations (`python script.py`, `python -m module`)
- Script-to-script calls (`./other_script.sh`, `bash script.sh`)

**Example**:
```bash
# In analyze.sh
curl -X POST "$SERVER_URL/analyze" -d "$REQUEST_DATA"
```

**Extract**:
- HTTP method: `POST`
- URL: `/analyze` (endpoint path)
- This becomes a "child call" in the tree

### Phase 2: HTTP Endpoint → Python Function Mapping

**Parse Python files** to detect HTTP route decorators:
- FastAPI: `@app.post("/analyze")`, `@app.get("/health")`
- Flask: `@app.route("/analyze", methods=["POST"])`

**Build mapping**:
```python
{
    "POST /analyze": "api.analyze",
    "GET /health": "api.health_check"
}
```

**Link HTTP calls to Python handlers**:
- Shell script calls `POST /analyze`
- Resolve to `api.py:analyze()` function
- Create call relationship: `analyze.sh` → `api.analyze`

### Phase 3: Unified Call Tree

**Extend `FunctionInfo`** to support:
- **Language type**: `python`, `shell`, `http_endpoint`
- **Cross-language calls**: Shell → HTTP, HTTP → Python, Python → Python

**Example `FunctionInfo`**:
```python
FunctionInfo(
    name="analyze.sh",
    qualified_name="scripts.analyze",
    language="shell",
    calls=["POST /analyze"],  # HTTP endpoint
    ...
)

FunctionInfo(
    name="analyze",
    qualified_name="api.analyze",
    language="python",
    http_route="POST /analyze",  # Maps to shell call
    calls=["analyzer.analyze_stock"],  # Python calls
    ...
)
```

**Call resolution**:
1. Shell script calls `POST /analyze`
2. Resolve to `api.analyze` (Python function with `@app.post("/analyze")`)
3. Build tree edge: `scripts.analyze` → `api.analyze`

---

## Implementation Steps

### Step 1: Shell Script Parser

**File**: `src/analyzer/shell_parser.py`

```python
@dataclass
class ShellCommand:
    """Represents a command in a shell script."""
    type: str  # "curl", "python", "bash"
    target: str  # URL, script path, or Python module
    method: Optional[str] = None  # HTTP method for curl
    line_number: int = 0

def parse_shell_script(file_path: Path) -> List[ShellCommand]:
    """Parse shell script and extract commands."""
    # Detect curl commands
    # Detect python invocations
    # Detect bash invocations
    ...
```

**Patterns to detect**:
- `curl ... http://localhost:8000/analyze` → HTTP call
- `python src/analyzer.py` → Direct Python invocation
- `./scripts/other.sh` → Script-to-script call

### Step 2: HTTP Endpoint Detector

**File**: `src/analyzer/http_endpoint_detector.py`

```python
@dataclass
class HTTPEndpoint:
    """Represents an HTTP endpoint handler."""
    method: str  # "GET", "POST", etc.
    path: str  # "/analyze", "/health"
    handler_function: str  # "api.analyze"
    line_number: int

def extract_http_endpoints(file_path: Path) -> List[HTTPEndpoint]:
    """Extract HTTP endpoints from Python files."""
    # Detect FastAPI decorators: @app.post("/analyze")
    # Detect Flask decorators: @app.route("/analyze", methods=["POST"])
    ...
```

### Step 3: Call Tree Builder Updates

**File**: `src/analyzer/call_tree_builder.py`

**Add shell script analysis**:
```python
def analyze_project(self, python_files: List[Path]) -> List[CallTreeNode]:
    # Step 0: Find and parse shell scripts
    shell_scripts = self._find_shell_scripts()
    for script in shell_scripts:
        self._parse_shell_script(script)

    # Step 1: Parse Python files (existing)
    for file_path in python_files:
        self._parse_file(file_path)

    # Step 2: Build HTTP endpoint map
    self.http_endpoints = self._build_http_endpoint_map()

    # Step 3: Resolve cross-language calls
    self._resolve_http_calls()

    # ... rest of existing logic
```

**HTTP endpoint mapping**:
```python
def _build_http_endpoint_map(self) -> Dict[str, str]:
    """Map HTTP endpoints to Python functions.

    Returns:
        Dict mapping "METHOD /path" to "module.function"
    """
    endpoint_map = {}

    for func_info in self.functions.values():
        if func_info.http_route:
            key = f"{func_info.http_method} {func_info.http_route}"
            endpoint_map[key] = func_info.qualified_name

    return endpoint_map
```

**Cross-language call resolution**:
```python
def _resolve_http_calls(self):
    """Resolve HTTP calls from shell scripts to Python handlers."""
    for func_info in self.functions.values():
        if func_info.language == "shell":
            # Resolve each HTTP call to Python function
            resolved_calls = []
            for call in func_info.calls:
                if call.startswith("POST ") or call.startswith("GET "):
                    # Look up endpoint in map
                    handler = self.http_endpoints.get(call)
                    if handler:
                        resolved_calls.append(handler)
                else:
                    resolved_calls.append(call)

            func_info.calls = resolved_calls
```

### Step 4: UI Updates

**Display cross-language nodes differently**:
- Shell scripts: `🐚 analyze.sh [script]`
- HTTP endpoints: `🌐 POST /analyze`
- Python functions: `📦 analyze_stock()`

**Color coding**:
- Shell: Green background
- HTTP: Blue background
- Python: Default

---

## Example Output

**Call Tree for StockAnalysis**:
```
🐚 analyze.sh [shell script]
    ├── 🌐 POST /analyze
    │   └── 📦 api.analyze()
    │       └── 📦 analyzer.analyze_stock()
    │           ├── 📦 extraction_layer.extract_data()
    │           ├── 📦 computation_layer.compute_metrics()
    │           └── 📦 evaluator.evaluate()
    │               └── 📦 decision_nodes.PF1Node.evaluate()
    └── 🌐 GET /health
        └── 📦 api.health_check()

🐚 start_server.sh [shell script]
    └── 📦 server.py [script]
        └── 📦 uvicorn.run() [external]
```

---

## Benefits

1. **True entry point detection** - Shell scripts are the real starting points
2. **Full system understanding** - See how shell → HTTP → Python flows
3. **API visualization** - Understand which endpoints exist and what they call
4. **Cross-team clarity** - DevOps can see shell scripts, backend devs see Python

---

## Future Extensions

### Phase 2: More Languages
- **JavaScript/TypeScript** - Frontend calling backend APIs
- **Makefile** - Build scripts calling Python tools
- **Docker/Compose** - Container orchestration scripts

### Phase 3: Bi-directional Analysis
- **From Python → Shell** - Which shell scripts call this Python function?
- **API dependency graph** - Which endpoints depend on each other?

### Phase 4: Dynamic Call Detection
- **Runtime tracing** - Capture actual HTTP calls during execution
- **Log analysis** - Parse logs to find real-world call patterns

---

## Implementation Priority

1. **HIGH**: Shell script parsing + curl detection (enables StockAnalysis use case)
2. **HIGH**: HTTP endpoint mapping (FastAPI decorators)
3. **MEDIUM**: Direct Python invocations from shell (`python -m module`)
4. **LOW**: Flask support (if needed)
5. **LOW**: Script-to-script calls

---

## Success Criteria

✅ `analyze.sh` appears as top-level entry point
✅ `POST /analyze` shown as child of `analyze.sh`
✅ `api.analyze()` shown as child of `POST /analyze`
✅ `analyze_stock()` shown as child of `api.analyze()`
✅ Full tree from shell → HTTP → Python visible
✅ UI clearly distinguishes shell, HTTP, and Python nodes
