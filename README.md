# FlowDiff

**Static architecture visualizer for Python codebases** - reveals dependencies in seconds.

FlowDiff transforms 70+ files into ~20 meaningful blocks that match your mental model of the codebase architecture. Built for engineers and LLMs.

## Features

- **Fast**: Analyzes codebases in <5 seconds
- **Smart Collapsing**: Automatically groups 74 files → 22 logical blocks
- **Interactive**: Web-based visualization with zoom, pan, click-to-highlight
- **Accurate**: Uses Python AST parsing (not regex)
- **Customizable**: Configure collapsing rules programmatically

## Quick Start

### Installation

```bash
# 1. Install Graphviz (required for layout computation)
# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get install graphviz

# Windows
# Download from https://graphviz.org/download/

# 2. Install FlowDiff
cd /path/to/FlowDiff
pip install -e .
```

### Usage

```bash
# Visualize a Python project
flowdiff snapshot /path/to/project

# More aggressive collapsing (fewer nodes, target ~15)
flowdiff snapshot /path/to/project --aggressive

# Minimal collapsing (more detail, up to 100 nodes)
flowdiff snapshot /path/to/project --minimal

# Custom port
flowdiff snapshot /path/to/project --port 9000

# Don't auto-open browser
flowdiff snapshot /path/to/project --no-browser
```

The tool will:
1. ✓ Parse all Python files using AST
2. ✓ Build dependency graph
3. ✓ Collapse to logical blocks
4. ✓ Compute layout with Graphviz
5. ✓ Open interactive visualization in browser

### Example Output

For a 74-file codebase (StockAnalysis):
- **Before**: 74 modules, 740 edges (including external dependencies)
- **After**: 22 logical blocks, 7 edges (internal only)

Key groupings:
- `decision_engine.decision_nodes` (12 files → 1 block)
- `src.data` (8 files → 1 block)
- `src.decision_engine` (6 files → 1 block)
- `src.core` (4 files → 1 block)
- `src.reporting` (4 files → 1 block)
- `tests` (17 files → 1 block)

## How It Works

FlowDiff uses a 4-stage pipeline:

### 1. Parsing (AST-based)
- Extracts `import` and `from X import Y` statements
- Resolves relative imports (`.`, `..`, `...`)
- Counts lines of code for node sizing
- Detects functions and classes

### 2. Graph Building
- Creates nodes for each Python file (MODULE type)
- Creates edges for import relationships
- Tracks edge weight (multiple imports to same module)
- Identifies external dependencies (stdlib, third-party)

### 3. Collapsing (The "Killer Feature")
Four stages, applied in sequence:

1. **Filter External**: Removes stdlib/third-party dependencies (pandas, typing, logging, etc.)
2. **Custom Rules**: Pattern-based grouping (regex matches)
   - Example: `decision_engine/nodes/*` → "Decision Nodes" (12 files → 1 FOLDER)
3. **Directory Grouping**: Collapses by directory depth (default: 2 levels)
   - `src.data.extraction` + `src.data.computation` → `src.data`
4. **Node Limit**: Enforces max nodes (default: 30) by merging smallest folders

### 4. Layout & Rendering
- **Graphviz**: Computes node positions using `dot` algorithm (left-to-right hierarchical)
- **D3.js**: Interactive SVG rendering in browser
- **Features**: Zoom, pan, click-to-highlight connections, tooltips

## Configuration

Programmatic configuration via Python:

```python
from graph.collapse_rules import CollapseConfig, CollapseRule
from graph.collapser import GraphCollapser

config = CollapseConfig(
    max_nodes=20,
    directory_depth=2,
    filter_external=True,
    custom_rules=[
        CollapseRule(
            pattern=r"src\.decision_engine\.nodes\..*",
            target_name="src.decision_engine.decision_nodes",
            target_label="Decision Nodes",
            priority=100
        )
    ]
)

collapser = GraphCollapser(config)
collapsed = collapser.collapse(raw_graph)
```

Presets available:
- `get_default_config()` - General purpose (max 30 nodes)
- `get_aggressive_config()` - Maximum reduction (max 15 nodes)
- `get_minimal_config()` - Debugging (max 100 nodes)
- `get_stockanalysis_config()` - StockAnalysis-specific

## Architecture

```
src/
├── parser/           # AST-based Python parsing
│   ├── models.py     # Import, FileMetadata dataclasses
│   ├── python_parser.py  # Extract imports, functions, classes
│   └── import_resolver.py  # Resolve relative imports
├── graph/            # Graph construction & collapsing
│   ├── models.py     # Node, Edge, Graph dataclasses
│   ├── builder.py    # Build dependency graph
│   ├── collapser.py  # 4-stage collapsing pipeline
│   └── collapse_rules.py  # CollapseRule, CollapseConfig
├── layout/           # Graphviz integration
│   ├── dot_generator.py  # Generate DOT format
│   └── graphviz_runner.py  # Execute dot, parse JSON
├── web/              # FastAPI + D3.js viewer
│   ├── server.py     # FastAPI server
│   └── static/
│       ├── index.html    # Main page
│       ├── viewer.js     # D3.js interactive viewer
│       └── styles.css    # Styling
├── config/           # Default collapsing rules
│   └── default_rules.py
└── cli.py            # Typer CLI
```

## Development

### Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt
```

### Run Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_parser.py

# With coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format
black src/ tests/

# Type check
mypy src/
```

## Requirements

- **Python**: >=3.9
- **Graphviz**: System package (for layout computation)
- **Dependencies**:
  - networkx==3.1
  - graphviz==0.20.1 (Python bindings)
  - fastapi==0.104.1
  - uvicorn[standard]==0.24.0
  - typer==0.9.0
  - rich==13.7.0
  - pyyaml==6.0.1

## Troubleshooting

### Graphviz not found

```
Error: Graphviz not found. Please install it:
  macOS:   brew install graphviz
  Ubuntu:  apt-get install graphviz
```

**Solution**: Install the Graphviz binary (not just the Python package). Verify with `dot -V`.

### Empty graph / No Python files found

**Solution**: Make sure you're pointing to a directory containing `.py` files. FlowDiff skips `__pycache__`, `venv`, `.git` directories.

### Too many nodes

**Solution**: Use `--aggressive` flag or create custom config with lower `max_nodes`.

## Status

**Alpha** - Core functionality complete, polish in progress.

### Completed (Phases 1A-1D)
- ✅ Parser (AST-based import extraction)
- ✅ Graph builder (MODULE nodes, IMPORT edges)
- ✅ Collapser (4-stage pipeline with custom rules)
- ✅ Layout (Graphviz DOT generation and execution)
- ✅ Web viewer (FastAPI + D3.js interactive SVG)
- ✅ CLI (basic commands)
- ✅ Tests (38 test methods across parser, graph, collapser)

### In Progress (Phase 1E-1F)
- ⏳ YAML config file support (`.flowdiff.yaml`)
- ⏳ Performance optimization (caching parsed files)
- ⏳ Project root auto-detection

### Planned (Phase 2+)
- 📋 Before/after diff visualization
- 📋 Git integration (detect changed files)
- 📋 Structured LLM feedback export
- 📋 Intent layer (user-defined architectural boundaries)
- 📋 Coupling metrics and drift detection

## License

MIT

## Contributing

Contributions welcome! Open an issue or PR on GitHub.

## Validation

Tested on:
- **StockAnalysis**: 74 Python files, 30k LOC
  - Raw: 74 MODULE nodes, 242 EXTERNAL nodes, 740 edges
  - Collapsed: 22 nodes, 7 edges
  - Time: <2 seconds

Collapsing correctly identifies:
- Data layer architecture (extraction → computation → cache)
- Decision engine with 13 decision nodes
- Reporting layer components
- Core utilities and configuration
