# FlowDiff Phase 1 Implementation Plan

## Vision

Build a **static architecture visualizer** that reveals the structural dependencies of Python codebases in a way that would take 5-10 minutes to infer from reading code alone. The tool must deliver a "wow factor" while being a practical engineering tool, not just eye candy.

**Target validation**: StockAnalysis app (70 Python files, 4-layer architecture)

**Success criterion**: Engineer looks at visualization and immediately sees:
- The layered architecture (core → data → decision_engine → reporting)
- Data flow through extraction → computation → cache → decision tree
- Logical grouping of 13 decision nodes
- Import dependencies between layers
- All in 10-15 blocks (not 70 files)

**Performance target**: <5 seconds from command execution to visualization

---

## Technical Approach

### Rendering Strategy: Web-First Hybrid
- **Layout**: Graphviz computes node positions (DOT → coordinates)
- **Rendering**: Web UI displays interactive SVG/Canvas
- **Why**: Battle-tested layout algorithms + rich browser interactivity
- **Deployment**: Local FastAPI server, auto-opens browser

### VCS Support
- **Phase 1**: Git-based projects (StockAnalysis use case)
- **Auto-detection**: Parse git diff to identify changed files
- **Future**: Perforce, manual file lists

### Architecture Philosophy
- **Coarse granularity**: 10-30 blocks max (aggressive automatic collapsing)
- **Change-first**: Future phases emphasize what changed (before/after diff)
- **Intent layer**: Defer to Phase 2+ (focus on automation first)
- **Speed over completeness**: Best-effort parsing, <60 second hard limit

---

## Component Architecture

```
CLI (Typer)
  ↓
Parser (AST-based Python import extraction)
  → FileMetadata: {path, imports, LOC, functions, classes}
  ↓
Graph Builder (networkx)
  → Graph: {nodes: modules/folders, edges: imports}
  ↓
Collapser (automatic grouping)
  → CollapsedGraph: 10-30 logical blocks
  ↓
Layout Engine (Graphviz dot)
  → Coordinates: {node positions, edge paths}
  ↓
Web Renderer (FastAPI + D3.js)
  → Interactive SVG visualization
```

### Key Design Decisions

1. **Parser**: Use Python's built-in `ast` module (no external deps)
   - Extract `import` and `from ... import` statements
   - Resolve relative imports to absolute paths
   - Skip function calls in Phase 1 (imports are sufficient signal)

2. **Graph Construction**: networkx for graph operations
   - Nodes: modules (files) and folders (collapsed groups)
   - Edges: import relationships (weighted by frequency)
   - Detect cycles using Tarjan's algorithm (annotate, don't break)

3. **Automatic Collapsing**: The killer feature
   - Group files by directory depth (e.g., `src/data/*.py` → `src.data`)
   - Filter stdlib and common third-party libs (pandas, numpy, etc.)
   - Custom rules for patterns (e.g., `decision_engine/nodes/*` → "Decision Nodes")
   - Enforce 30-node hard limit (merge smallest folders if needed)

4. **Layout**: Graphviz `dot` algorithm (hierarchical directed graph)
   - Best for layered architectures (StockAnalysis: core → data → decision → reporting)
   - Generate DOT format, run `dot -Tjson`, extract coordinates
   - Fallback to `neato` for circular/tangled codebases

5. **Web Rendering**: FastAPI + vanilla JS + D3.js
   - No React/Vue (overkill for Phase 1, adds build complexity)
   - SVG over Canvas (better for interactivity, zoom, inspect)
   - Basic interactions: zoom, pan, click node to highlight connections

---

## Critical Files to Create

### 1. `/Users/barlarom/PycharmProjects/Main/FlowDiff/flowdiff/parser/python_parser.py`
**Purpose**: Extract imports from Python files using AST

**Key functions**:
- `extract_imports(file_path) -> List[Import]`: Parse all import statements
- `resolve_relative_import(import, current_module) -> str`: Convert relative to absolute

**Test against**: StockAnalysis import patterns
- `from src.core import constants`
- `from .schemas import MetricValue` (relative)
- `from ..models import NodeResult` (parent-level relative)

### 2. `/Users/barlarom/PycharmProjects/Main/FlowDiff/flowdiff/graph/collapser.py`
**Purpose**: Collapse 70 files → 15 logical blocks

**Key functions**:
- `collapse(graph, rules) -> CollapsedGraph`: Main collapsing pipeline
- `group_by_directory(graph, depth) -> Graph`: Folder-level grouping
- `filter_external(graph) -> Graph`: Remove stdlib/third-party
- `enforce_node_limit(graph, max_nodes) -> Graph`: Merge until <30 nodes

**Critical**: This makes or breaks the "mental model match"

**Reference**: StockAnalysis structure
```
src/data/extraction_layer.py  → "src.data.extraction"
src/data/computation_layer.py → "src.data.computation"
src/decision_engine/nodes/prefilters.py → "decision_nodes" (custom group)
```

### 3. `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/layout/graphviz_runner.py`
**Purpose**: Execute Graphviz and extract coordinates

**Key functions**:
- `run(dot_content) -> Dict[str, Any]`: Run `dot -Tjson`, parse output
- `extract_coordinates(layout_data) -> Coords`: Parse node positions and edge paths

**Performance critical**: Must complete in <2 seconds
- Check Graphviz installed on startup (friendly error if missing)
- Set 10-second timeout (fail gracefully if graph too complex)

### 4. `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/web/static/viewer.js`
**Purpose**: Interactive SVG graph viewer (D3.js)

**Key features**:
- Render nodes (rounded rectangles, sized by LOC)
- Render edges (arrows, styled by type)
- Zoom and pan (smooth, performant)
- Click node → highlight connected edges
- Tooltip on hover (module name, LOC, file count)

**Wow factor**: Clean, fast, informative

### 5. `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/cli.py`
**Purpose**: User-facing CLI (Typer framework)

**Commands**:
```bash
flowdiff snapshot .                    # Visualize current directory
flowdiff snapshot /path/to/project     # Visualize specific path
flowdiff snapshot . --output graph.svg # Save SVG instead of launching browser
flowdiff init                          # Create .flowdiff.yaml config
```

**Orchestration**: Parse → Build → Collapse → Layout → Render

**UX**: Show progress (rich library), helpful errors, fast execution

---

## Project Structure

```
FlowDiff/
├── src/
│   ├── cli.py                    # CLI entry point (Typer)
│   ├── parser/
│   │   ├── python_parser.py      # AST-based import extraction
│   │   ├── import_resolver.py    # Resolve relative imports
│   │   └── models.py             # FileMetadata, Import dataclasses
│   ├── graph/
│   │   ├── models.py             # Node, Edge, Graph dataclasses
│   │   ├── builder.py            # GraphBuilder (create graph from files)
│   │   └── collapser.py          # GraphCollapser (reduce to 10-30 nodes)
│   ├── layout/
│   │   ├── dot_generator.py      # Generate Graphviz DOT format
│   │   └── graphviz_runner.py    # Execute Graphviz, parse coordinates
│   ├── web/
│   │   ├── server.py             # FastAPI server
│   │   ├── renderer.py           # Graph → SVG conversion
│   │   └── static/
│   │       ├── index.html        # Main visualization page
│   │       ├── viewer.js         # D3.js interactive viewer
│   │       └── styles.css        # Styling
│   ├── config/
│   │   ├── default_rules.py      # Default collapsing rules
│   │   └── loader.py             # Load .flowdiff.yaml
│   └── utils/
│       ├── project_finder.py     # Auto-detect project root
│       └── cache.py              # Cache parsed metadata
├── tests/
│   ├── test_parser.py            # Parser unit tests
│   ├── test_graph.py             # Graph builder tests
│   ├── test_collapser.py         # Collapsing logic tests
│   ├── test_integration.py       # End-to-end pipeline tests
│   └── fixtures/
│       └── sample_project/       # Mini StockAnalysis for testing
├── examples/
│   └── stockanalysis_snapshot.svg  # Example output
├── doc/
│   └── flowdiff_design_notes.md  # (existing design doc)
├── requirements.txt
├── setup.py
└── README.md
```

---

## Technology Stack

### Core Dependencies
- **Python 3.9+** (matches StockAnalysis)
- **networkx**: Graph algorithms (cycle detection, traversal)
- **graphviz**: Python bindings for Graphviz DOT
- **fastapi**: Modern async web framework
- **uvicorn**: ASGI server
- **typer**: CLI framework (built on click)
- **rich**: Beautiful terminal output (progress bars, colors)
- **pyyaml**: Config file parsing

### External Requirements
- **Graphviz binary**: Must be installed via system package manager
  - macOS: `brew install graphviz`
  - Ubuntu: `apt-get install graphviz`

### Frontend (No build tools)
- **Vanilla JavaScript** (no framework)
- **D3.js v7**: SVG manipulation, zoom/pan
- **Minimal CSS**: Clean, functional styling

---

## Implementation Phases

### Phase 1A: Foundation (Week 1)
**Goal**: Parse StockAnalysis and build raw graph

**Tasks**:
1. Set up project structure (directories, setup.py, requirements.txt)
2. Implement `python_parser.py`:
   - `extract_imports()` using Python AST
   - Handle absolute and relative imports
3. Implement `graph/builder.py`:
   - Create nodes for each Python file
   - Resolve imports to absolute paths
   - Create edges for import relationships
4. Write unit tests for parser and builder
5. **Validation**: Parse StockAnalysis, print raw graph (expect ~70 nodes, ~150 edges)

### Phase 1B: Collapsing (Week 2)
**Goal**: Reduce StockAnalysis to 15 logical blocks

**Tasks**:
1. Implement `graph/collapser.py`:
   - `group_by_directory()`: Collapse to folder level
   - `filter_external()`: Remove stdlib/third-party
   - `apply_custom_rules()`: Custom groupings (e.g., "decision_nodes")
   - `enforce_node_limit()`: Merge until <30 nodes
2. Implement `config/default_rules.py`:
   - Default stdlib filtering list
   - Default collapse depth (2 levels)
3. Write tests for collapsing logic
4. **Validation**: Collapse StockAnalysis graph, verify ~15 nodes with meaningful labels

### Phase 1C: Layout (Week 2)
**Goal**: Generate Graphviz layout coordinates

**Tasks**:
1. Implement `layout/dot_generator.py`:
   - Convert Graph to DOT format
   - Configure `dot` algorithm (rankdir=LR, rounded boxes)
2. Implement `layout/graphviz_runner.py`:
   - Execute `dot -Tjson input.dot`
   - Parse JSON output to extract node positions and edge paths
   - Handle errors (Graphviz not installed, timeout)
3. Write tests for DOT generation and coordinate parsing
4. **Validation**: Generate layout for StockAnalysis, verify logical flow (core → data → decision → reporting)

### Phase 1D: Web Rendering (Week 3)
**Goal**: Display interactive graph in browser

**Tasks**:
1. Implement `web/server.py`:
   - FastAPI server with `/` (HTML) and `/api/graph` (JSON) endpoints
   - Load pre-computed graph from cache
   - Auto-open browser on startup
2. Create `web/static/index.html`:
   - Simple HTML page with SVG container
   - Load D3.js from CDN
3. Create `web/static/viewer.js`:
   - D3.js SVG renderer (nodes, edges, arrows)
   - Zoom and pan behavior
   - Click node → highlight connections
   - Hover tooltip (module name, LOC)
4. Create `web/static/styles.css`:
   - Clean, minimal styling
   - Color scheme: blue nodes, gray edges, white text
5. **Validation**: Render StockAnalysis graph, verify interactivity works smoothly

### Phase 1E: CLI & Integration (Week 4)
**Goal**: Polished end-to-end CLI tool

**Tasks**:
1. Implement `cli.py`:
   - `flowdiff snapshot <path>` command
   - Auto-detect project root (look for .git, setup.py)
   - Show progress: "Parsing... Building graph... Collapsing... Rendering..."
   - Error handling (Graphviz missing, no Python files found)
2. Implement `config/loader.py`:
   - Load `.flowdiff.yaml` if present
   - Merge with default rules
3. Add `flowdiff init` command:
   - Generate sample `.flowdiff.yaml` with comments
4. Write integration tests:
   - Full pipeline on sample project fixture
   - Verify output matches expectations
5. **Validation**: Run `flowdiff snapshot /path/to/StockAnalysis`, verify <5 seconds, browser opens with correct graph

### Phase 1F: Polish & Documentation (Week 5)
**Goal**: Production-ready tool

**Tasks**:
1. Performance optimization:
   - Cache parsed file metadata (only re-parse changed files)
   - Optimize Graphviz parameters for speed
   - Measure end-to-end time, target <3 seconds for StockAnalysis
2. Error handling:
   - Graceful failures (missing imports, circular deps, Graphviz timeout)
   - Helpful error messages with suggestions
3. Documentation:
   - README with installation, usage, examples
   - Screenshot of StockAnalysis visualization
   - Configuration guide (.flowdiff.yaml options)
4. User feedback:
   - Show visualization to project author
   - Iterate on collapsing rules based on feedback
5. **Final validation**: Does the visualization match the mental model? Does it deliver "wow factor"?

---

## Model Selection Strategy

### Recommended Models by Component

**Use Sonnet 4.5** for 80% of implementation (cost-effective, fast, sufficient):

1. **Phase 1A - Foundation**
   - Parser (`python_parser.py`, `import_resolver.py`)
   - Graph Builder (`graph/builder.py`, `graph/models.py`)
   - Well-defined: Extract imports using AST, create graph data structures
   - Clear inputs/outputs, standard patterns

2. **Phase 1C - Layout**
   - Layout Engine (`layout/dot_generator.py`, `graphviz_runner.py`)
   - Mostly integration code (call Graphviz, parse output)
   - Standard subprocess/JSON handling

3. **Phase 1D - Web Rendering**
   - Web UI (`viewer.js`, `server.py`, HTML/CSS)
   - Frontend is well-defined (D3.js patterns, FastAPI boilerplate)
   - Interaction patterns are standard

4. **Phase 1E - CLI & Utilities**
   - CLI (`cli.py`, project finder, config loader)
   - Typer framework is straightforward
   - Error handling, progress bars are mechanical

**Use Opus 4.5** for 20% of implementation (critical reasoning, makes/breaks the tool):

1. **Phase 1B - Collapser** ⭐ **This is the killer feature**
   - Component: `graph/collapser.py`
   - **Why Opus?**
     - Complex reasoning: Deciding *how* to group 70 files → 15 meaningful blocks
     - Heuristic refinement: Rules need to be smart, not just mechanical
     - Mental model matching: This is where "wow factor" lives or dies
     - Requires understanding architectural patterns (layering, pipelines, similar-file-groups)
     - Must balance competing constraints (node count, logical coherence, signal preservation)

2. **Phase 1F - Validation & Refinement**
   - Review StockAnalysis output: "Does this match the mental model?"
   - Suggest collapser rule improvements
   - Identify edge cases and architectural patterns missed
   - **Why Opus?** Needs senior engineering judgment on architecture quality

### Cost/Benefit Analysis

**Collapser with Opus vs Sonnet**:
- Opus cost: ~5x more, but only 20% of implementation time
- Value: This component determines if FlowDiff succeeds or fails
- Sonnet might get it 80% right, Opus will get it 95% right
- **Worth it**: The difference between "okay" and "wow factor"

**Everything else with Sonnet**:
- Parser, layout, web UI are straightforward
- Well-defined patterns, no complex reasoning
- Sonnet is fast, cost-effective, and sufficient

### Practical Implementation Workflow

```
Phase 1A (Foundation)           → Sonnet 4.5
  - Implement parser, graph builder, models
  - Get raw graph working (70 nodes, 150 edges)

Phase 1B (Collapsing)           → Opus 4.5 ⭐
  - Design and implement collapser logic
  - Validate on StockAnalysis (iterative refinement)
  - This is the hard part - needs strongest reasoning

Phase 1C (Layout)               → Sonnet 4.5
  - Graphviz integration (mechanical)

Phase 1D (Web UI)               → Sonnet 4.5
  - D3.js rendering, FastAPI server

Phase 1E (CLI)                  → Sonnet 4.5
  - Typer CLI, integration

Phase 1F (Polish)               → Opus 4.5 for validation, Sonnet for fixes
  - Opus: Review end-to-end, suggest improvements
  - Sonnet: Implement performance optimizations, error handling
```

### Import Extraction Clarification

**What we extract**: Internal imports (project file → project file)
```python
# In StockAnalysis/src/decision_engine/evaluator.py
from src.data.extraction_layer import extract_data  # Internal - keep
from src.core.metrics import METRIC_DEFINITIONS      # Internal - keep
from .nodes.prefilters import PF1Node                # Internal - keep
```

**What we filter out**: External imports (stdlib, third-party)
```python
import pandas as pd          # External - filter in collapsing phase
from typing import List      # External - filter in collapsing phase
import yfinance              # External - filter in collapsing phase
```

**Why extract everything first, then filter?**
- At parse time, we don't know the full set of project modules yet
- Easier to determine "internal vs external" after we've seen all files
- Allows user to optionally show external deps (`--show-external` flag)
- Internal imports reveal architecture, external imports don't

---

## Verification Strategy

### End-to-End Test: StockAnalysis Snapshot

**Command**:
```bash
cd /Users/barlarom/PycharmProjects/Main
flowdiff snapshot StockAnalysis/
```

**Expected output** (console):
```
FlowDiff v0.1.0

📁 Project: StockAnalysis
   Root: /Users/barlarom/PycharmProjects/Main/StockAnalysis

🔍 Parsing Python files... ████████████████ 70/70 (0.4s)
📊 Building dependency graph... done (132 edges)
🗜️  Collapsing to logical blocks... 70 → 15 nodes (0.2s)
📐 Computing layout (Graphviz dot)... done (0.9s)
🌐 Starting web server at http://localhost:8080
🚀 Opening browser...

Press Ctrl+C to stop server.
```

**Expected visualization** (browser):
- **15 nodes** (logical blocks):
  1. `core` (constants, metrics, stock_analysis)
  2. `data.extraction` (extraction_layer.py)
  3. `data.computation` (computation_layer.py)
  4. `data.cache` (cache_integration.py, ticker_database_sql.py)
  5. `data.schemas` (schemas.py)
  6. `data.red_flag_metrics` (red_flag_metrics_collector.py)
  7. `decision_engine.evaluator` (evaluator.py)
  8. `decision_engine.metrics_panel` (metrics_panel.py)
  9. `decision_engine.sector_classifier` (sector_classifier.py)
  10. `decision_nodes` (all 13 node files collapsed)
  11. `reporting.html` (html_template.py)
  12. `reporting.viz` (decision_tree_visualizer.py)
  13. `reporting.text` (text_report.py)
  14. `analyzer` (stock_analyzer.py)
  15. `server` (server.py)

- **Key edges** (data flow):
  - `analyzer` → `data.extraction`
  - `data.extraction` → `data.cache`
  - `data.extraction` → `data.computation`
  - `data.computation` → `core`
  - `analyzer` → `decision_engine.evaluator`
  - `decision_engine.evaluator` → `decision_nodes`
  - `decision_engine.evaluator` → `decision_engine.metrics_panel`
  - `analyzer` → `reporting.*`
  - `server` → `analyzer`

- **Layout**:
  - Left-to-right flow showing architectural layers
  - `core` on the left (foundation)
  - `data.*` in the middle-left (data pipeline)
  - `decision_engine.*` in the middle-right (business logic)
  - `reporting.*` on the right (output)
  - `analyzer` and `server` on the far right (orchestration)

- **Interactivity**:
  - Smooth zoom and pan
  - Click `data.extraction` → highlights edges to `data.cache` and `data.computation`
  - Hover shows tooltip: "data.extraction (1 file, 273 LOC)"

### Success Criteria

✅ **Mental model match**: Engineer immediately recognizes the architecture
✅ **Performance**: <5 seconds from command to visualization
✅ **Clarity**: 15 nodes (not 70), each with clear purpose
✅ **Data flow**: Obvious pipeline from extraction → computation → decision → reporting
✅ **Wow factor**: Visual impact - "I can see the whole system at a glance"
✅ **Utility**: Reveals what would take 5-10 minutes to infer from code

---

## Risks & Mitigations

### Risk 1: Diagram doesn't match mental model
**Mitigation**: Validate early on StockAnalysis, iterate on collapsing rules, allow configuration

### Risk 2: Too slow (>60 seconds)
**Mitigation**: Aggressive node limit (30 max), cache parsed metadata, timeout Graphviz (10s)

### Risk 3: Graphviz not installed
**Mitigation**: Check on startup, show helpful install instructions, document requirement clearly

### Risk 4: Import resolution fails
**Mitigation**: Test on diverse projects, log ambiguous cases, provide manual override in config

### Risk 5: Graph too dense for large codebases
**Mitigation**: Focus mode (visualize subset), adaptive collapsing, warn user and recommend options

---

## Next Steps After Phase 1

**Phase 2**: Before/after diff visualization
- Parse git diff to detect changed files
- Highlight added/removed/modified nodes and edges
- Side-by-side comparison view
- Structured feedback export (for LLM consumption)

**Phase 3**: Intent layer
- YAML-based architectural definitions
- User-defined logical blocks and boundaries
- Override automatic collapsing
- Version-controlled architectural rules

**Phase 4**: Advanced signals
- Coupling metrics (increased/decreased)
- Responsibility growth detection
- Architectural violation warnings
- Integration with git hooks (pre-commit visualization)

---

## Summary

FlowDiff Phase 1 creates a **static architecture snapshot visualizer** that transforms 70 Python files into 15 meaningful logical blocks, revealing the architectural structure in <5 seconds. The visualization must match the engineer's mental model and deliver a "wow factor" by making architectural patterns immediately visible - something that would take 5-10 minutes to infer from reading code.

**Core innovation**: Aggressive automatic collapsing combined with Graphviz layout and web-based interactivity creates a tool that's both fast and informative.

**Validation target**: StockAnalysis app - if the visualization correctly shows the 4-layer pipeline architecture, we've succeeded.
