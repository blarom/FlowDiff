# FlowDiff

Multi-language call tree analyzer with git diff visualization.

## Features

- 📊 Interactive call tree visualization with change highlighting
- 🔀 Git diff analysis (any commit, branch, or tag)
- 🌐 Multi-language support (Python, Shell)
- 🎨 Unified split-pane UI (tree on left, changes on right)
- ⚡ Fast analysis (<5 seconds)
- 🤖 Optional LLM-powered entry point filtering

## Quick Start

### Installation

```bash
# Install dependencies
cd /path/to/FlowDiff
pip install -e .
```

### Usage

**Single unified command:**

```bash
# Analyze current directory (default: HEAD vs working directory)
flowdiff analyze .

# Analyze specific project
flowdiff analyze ../MyProject

# Compare with previous commit
flowdiff analyze . --before HEAD~1

# Compare branches
flowdiff analyze . --before main --after dev

# Compare tags
flowdiff analyze . --before v1.0 --after v2.0

# Use LLM filtering for entry points
flowdiff analyze . --llm-provider claude-code-cli

# Save reports to custom directory
flowdiff analyze . --output reports/

# Custom port
flowdiff analyze . --port 9000
```

## How It Works

**Unified View:**
- **Left pane**: Full call tree with changes highlighted in yellow
- **Right pane**: Summary of changed functions only
- **Smart defaults**: Compares HEAD vs working directory (shows your uncommitted changes)

### Git Diff Analysis

1. **Ref Resolution**: Convert git refs (HEAD, branches, tags) to commit SHAs
2. **File Detection**: Find changed files using `git diff`
3. **Symbol Mapping**: Build symbol tables at both refs and compare
4. **Tree Building**: Generate call tree with changes marked

### Change Highlighting

- 🟢 Green: Added functions
- 🟡 Yellow: Modified functions (shown in both panes)
- 🔴 Red: Deleted functions

## Architecture

```
src/
├── analyzer/         # Core analysis engine
│   ├── core/         # Symbol-based architecture
│   │   ├── symbol.py       # Symbol representation
│   │   └── symbol_table.py # Symbol storage
│   ├── parsers/      # Language-specific parsers
│   │   ├── python_parser.py  # Python AST parser
│   │   └── shell_parser.py   # Shell script parser
│   ├── bridges/      # Cross-language bridges
│   │   └── http_to_python.py # HTTP → Python bridge
│   ├── git/          # Git diff analysis
│   │   ├── ref_resolver.py      # Resolve git refs
│   │   ├── file_change_detector.py # Detect changed files
│   │   ├── symbol_change_mapper.py # Map to symbol changes
│   │   └── diff_analyzer.py     # Main diff analyzer
│   ├── llm/          # LLM integration (Phase 2)
│   │   └── interfaces.py    # DiffExplainer interface
│   ├── orchestrator.py      # Coordinates analysis
│   ├── call_tree_adapter.py # Legacy compatibility
│   └── legacy.py            # Legacy data structures
├── web/              # Web server and UI
│   ├── server.py     # FastAPI server
│   ├── export.py     # Export framework (Phase 2)
│   └── static/
│       ├── index.html    # Call tree viewer
│       ├── diff.html     # Diff viewer
│       ├── diff.css      # Diff styling
│       └── diff.js       # Diff interactions
└── cli.py            # Typer CLI

```

## How It Works

### Symbol-Based Architecture

FlowDiff uses a unified symbol representation across all languages:

1. **Parsers**: Language-specific parsers extract symbols (functions, classes, etc.)
2. **Symbol Tables**: Symbols are stored with metadata (parameters, return types, etc.)
3. **Call Resolution**: Cross-references are resolved to build call trees
4. **Bridges**: Cross-language bridges connect HTTP routes to Python handlers

### Git Diff Analysis

The diff analyzer compares two git refs:

1. **Ref Resolution**: Convert git refs (HEAD, branches, tags) to commit SHAs
2. **File Detection**: Find changed files using `git diff`
3. **Symbol Mapping**: Build symbol tables at both refs and compare
4. **Tree Building**: Generate before/after call trees with changes marked

## Status

**Phase 1 Complete** - Core diff visualization implemented

### Completed
- ✅ Symbol-based architecture
- ✅ Multi-language support (Python, Shell)
- ✅ Git diff backend
- ✅ Split-pane diff UI
- ✅ Any-vs-any comparison
- ✅ CLI integration
- ✅ Legacy code cleanup (971 lines removed)

### Planned (Phase 2)
- 📋 LLM-powered diff explanations
- 📋 Export to HTML/PDF
- 📋 Semantic diff analysis
- 📋 Multi-commit comparison
- 📋 Blame integration

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR on GitHub.

