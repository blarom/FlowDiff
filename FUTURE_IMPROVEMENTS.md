# FlowDiff Future Improvements

This document tracks planned enhancements and features for FlowDiff.

## Status Legend
- 🔴 **CRITICAL** - Must have for production readiness
- 🟡 **HIGH** - Significantly improves usability/reliability
- 🟢 **MEDIUM** - Nice to have, enhances user experience
- 🔵 **LOW** - Future polish, not urgent

---

## 🔴 CRITICAL: Comprehensive Test Suite

### Motivation
Currently, FlowDiff has no automated tests. This creates risk that future changes could break core functionality without detection. Need comprehensive test coverage for both backend data generation and frontend UI interactions.

### Test Categories

#### 1. Backend Data Generation Tests
**Purpose**: Ensure analysis produces correct data structures for visualization

**Test Areas**:
- **Symbol Extraction**: Verify Python analyzer correctly extracts functions, parameters, return types
- **Call Tree Building**: Test tree construction from entry points with correct parent-child relationships
- **Git Diff Integration**: Verify before/after tree generation with correct change markers
- **Change Detection**: Test `has_changes` flag accurately marks modified/added/deleted functions
- **Deleted Function Extraction**: Verify `extract_deleted_functions()` correctly identifies deletions
- **Tree Serialization**: Test JSON serialization produces valid structure for web display
- **Edge Cases**:
  - Empty projects
  - Projects with no changes
  - Large projects (100+ functions)
  - Circular dependencies
  - Script entry points
  - Multi-file modules

**Example Tests**:
```python
def test_python_analyzer_extracts_functions():
    """Test that PythonAnalyzer correctly extracts function metadata."""
    code = '''
def calculate_roic(net_income: float, capital: float) -> float:
    """Calculate return on invested capital."""
    return net_income / capital
    '''
    analyzer = PythonAnalyzer(Path("test.py"))
    symbols = analyzer.analyze_file(code)

    assert len(symbols) == 1
    assert symbols[0].name == "calculate_roic"
    assert symbols[0].parameters == ["net_income: float", "capital: float"]
    assert symbols[0].return_type == "float"
    assert "Calculate return" in symbols[0].documentation

def test_diff_analyzer_marks_changes():
    """Test that git diff correctly marks changed functions."""
    # Setup: Create temp git repo with before/after commits
    with temp_git_repo() as repo:
        # Commit 1: Original function
        repo.commit("def foo(): pass")

        # Commit 2: Modified function
        repo.commit("def foo(): return 42")

        # Analyze diff
        analyzer = GitDiffAnalyzer(repo.path)
        result = analyzer.analyze_diff("HEAD~1", "HEAD")

        # Verify change detection
        assert result.functions_modified == 1
        assert result.symbol_changes["test::foo"].change_type == "M"

def test_extract_deleted_functions():
    """Test deleted function extraction utility."""
    symbol_changes = {
        "test::deleted_fn": SymbolChange(
            change_type=ChangeType.DELETED,
            before_symbol=Symbol(name="deleted_fn", ...)
        ),
        "test::modified_fn": SymbolChange(
            change_type=ChangeType.MODIFIED,
            ...
        )
    }

    deleted = extract_deleted_functions(symbol_changes)

    assert len(deleted) == 1
    assert deleted[0]["name"] == "deleted_fn"
```

#### 2. Frontend UI Interaction Tests
**Purpose**: Ensure UI elements function correctly and data displays properly

**Test Areas**:
- **Tree Rendering**: Verify tree view correctly displays before/after trees
- **Click Navigation**: Test clicking changed functions in changes panel navigates to tree
- **Deleted Function Clicks**: Verify deleted functions switch to before view
- **Tree Toggle**: Test before/after view toggle button
- **Expand/Collapse**: Verify tree node expansion/collapse
- **Search Functionality**: Test tree search with regex
- **Filter Controls**: Test include/exclude filters
- **Keyboard Navigation**: Test arrow keys, n/p for changes
- **Diff Display**: Verify diff modal shows correct content
- **Toast Messages**: Test informational messages for deleted functions not in tree

**Test Framework**: Selenium/Playwright for browser automation

**Example Tests**:
```python
@pytest.mark.integration
def test_click_changed_function_navigates_to_tree(browser):
    """Test that clicking a changed function in the panel navigates to it."""
    # Load diff view
    browser.get("http://localhost:8080/diff.html")

    # Click first changed function in right panel
    changed_function = browser.find_element(".changed-function")
    changed_function.click()

    # Verify tree node is selected and visible
    selected_node = browser.find_element(".tree-node.selected")
    assert selected_node.is_displayed()
    assert selected_node.text == changed_function.text

@pytest.mark.integration
def test_deleted_function_switches_to_before_view(browser):
    """Test clicking deleted function switches to before tree."""
    browser.get("http://localhost:8080/diff.html")

    # Click deleted function
    deleted_fn = browser.find_element(".deleted-function")
    deleted_fn.click()

    # Verify toggle button shows "Before (Reference)"
    toggle_btn = browser.find_element("#toggle-tree-view")
    assert "Before" in toggle_btn.text

    # Verify tree shows function
    assert browser.find_element(".tree-node.selected").is_displayed()

@pytest.mark.integration
def test_deleted_function_not_in_tree_shows_toast(browser):
    """Test toast appears for deleted functions not in call tree."""
    browser.get("http://localhost:8080/diff.html")

    # Click deleted function that wasn't in tree
    orphan_fn = browser.find_element("[data-qualified-name='orphan::fn']")
    orphan_fn.click()

    # Verify toast message appears
    toast = browser.find_element(".toast")
    assert "wasn't part of any active flow" in toast.text
```

#### 3. Integration Tests
**Test Areas**:
- Full CLI workflow: `flowdiff analyze . --before HEAD~1`
- Server startup and shutdown
- Report generation (JSON, text, markdown, HTML)
- Multiple concurrent analyses

### Test Infrastructure

**Required Setup**:
- `pytest` as test runner
- `pytest-cov` for coverage reporting
- `playwright` or `selenium` for browser tests
- Fixtures for creating temp git repos
- Mock data for common scenarios

**Test Organization**:
```
tests/
├── unit/
│   ├── test_python_analyzer.py
│   ├── test_call_tree_adapter.py
│   ├── test_diff_analyzer.py
│   ├── test_serialization.py
│   └── test_utils.py
├── integration/
│   ├── test_cli_workflow.py
│   ├── test_server_endpoints.py
│   └── test_ui_interactions.py
├── fixtures/
│   ├── sample_projects/
│   │   ├── simple_project/
│   │   ├── complex_project/
│   │   └── edge_cases/
│   └── conftest.py
└── README.md
```

**Coverage Goal**: 80%+ for critical paths

**CI Integration**: Run tests on every commit, block PRs if tests fail

---

## 🟡 HIGH: Interactive Architecture Block Diagram

### Motivation
Users need a high-level visual understanding of how their codebase is structured and how functions relate to each other architecturally. When exploring the call tree, seeing the architectural context helps navigate complex codebases.

### Feature Description

**Visual Representation**:
- Block diagram showing up to 10-15 architectural components for the currently selected flow tree only
- Blocks represent major functional areas (API layer, data processing, utilities, etc.)
- Arrows show flow/dependencies between blocks
- When a function is selected in the tree, the corresponding architectural block highlights
- The high-level block diagrams should be cached when created, and their re-creation should be done upon user request as a flowdiff script argument

**Implementation Approach**:

#### 1. AI-Powered Architecture Analysis
Use LLM to analyze codebase and generate architecture:

```python
def generate_architecture_blocks(symbol_table, call_tree):
    """
    Use LLM to analyze code and generate architectural blocks.

    Returns:
        {
            "blocks": [
                {
                    "id": "api_layer",
                    "label": "API Layer",
                    "description": "FastAPI endpoints and request handling",
                    "functions": ["api::analyze", "api::get_diff", ...],
                    "color": "#3498db"
                },
                {
                    "id": "analyzer",
                    "label": "Code Analyzer",
                    "description": "AST parsing and symbol extraction",
                    "functions": ["analyzer::parse", "analyzer::extract", ...],
                    "color": "#2ecc71"
                },
                ...
            ],
            "connections": [
                {"from": "api_layer", "to": "analyzer", "label": "analyzes"},
                {"from": "analyzer", "to": "git_integration", "label": "uses"},
                ...
            ]
        }
    """
    prompt = f"""
    Analyze this Python codebase and identify 10-15 high-level architectural blocks.

    Symbol Table: {symbol_table}
    Call Tree: {call_tree}

    Group functions into architectural components based on:
    - Directory structure (e.g., src/web/, src/analyzer/)
    - Functional purpose (e.g., "API Layer", "Data Processing", "Utilities")
    - Dependency patterns

    Provide:
    1. Block name and description
    2. List of functions in each block
    3. Connections between blocks (data flow, dependencies)

    Special handling:
    - Map tests to a single "Tests" block
    - Map standalone utilities to "Utilities" block
    - Main entry points go to their respective workflow blocks

    Return as JSON.
    """

    return llm.analyze(prompt)
```

#### 2. Graphviz Diagram Generation

```python
def generate_diagram(arch_blocks):
    """Generate Graphviz DOT diagram from architecture blocks."""
    dot = """
    digraph Architecture {
        rankdir=LR;
        node [shape=box, style=filled, fillcolor="#f0f0f0"];

        // Blocks
        api_layer [label="API Layer\\nFastAPI endpoints", fillcolor="#3498db"];
        analyzer [label="Code Analyzer\\nAST parsing", fillcolor="#2ecc71"];
        git_integration [label="Git Integration\\nDiff analysis", fillcolor="#e74c3c"];
        ...

        // Connections
        api_layer -> analyzer [label="analyzes"];
        analyzer -> git_integration [label="uses"];
        ...
    }
    """

    # Render to SVG for web embedding
    return graphviz.render(dot, format='svg')
```

#### 3. Interactive Highlighting

**Frontend (JavaScript)**:
```javascript
// When user selects function in tree
function onFunctionSelect(qualifiedName) {
    // Find which architectural block contains this function
    const block = architecture.blocks.find(b =>
        b.functions.includes(qualifiedName)
    );

    if (block) {
        // Highlight block in diagram
        const svgElement = document.querySelector(`#block_${block.id}`);
        svgElement.classList.add('highlighted');

        // Show block description in sidebar
        showBlockDescription(block);
    }
}
```

**Diagram Display**:
- Embedded SVG in left sidebar (collapsible panel)
- Hover over blocks shows function count
- Click block to filter tree to that architectural area
- Responsive design: collapse diagram on mobile

### Example for StockAnalysis

If this were applied to StockAnalysis:

**Blocks**:
1. **API Layer** - `api::analyze`, `api::batch_analyze`
2. **Decision Engine** - All PF*, VT*, S*, C* nodes
3. **Data Fetchers** - `yfinance_fetcher::*`, `sec_fetcher::*`
4. **Cache System** - `cache_manager::*`
5. **Metrics Calculator** - `stock_analysis_lib::calculate_*`
6. **Report Generator** - `html_template::*`, `visualizer::*`
7. **Tests** - All test_* functions
8. **Utilities** - `global_lib::*`, standalone helpers

**Connections**:
- API Layer → Decision Engine (evaluates)
- Decision Engine → Data Fetchers (retrieves)
- Decision Engine → Metrics Calculator (calculates)
- Data Fetchers → Cache System (caches)
- Decision Engine → Report Generator (generates)

### Benefits
- Quick architectural understanding for new developers
- Navigate large codebases by architectural area
- Identify cross-cutting concerns
- Visualize dependency patterns
- Educational: shows how code is organized

---

## 🟢 MEDIUM: Dark Mode Toggle

### Motivation
Developers often work in dark environments and prefer dark themes. Providing a dark mode improves usability and reduces eye strain during extended sessions.

### Implementation

#### 1. Toggle Switch UI

**Location**: Top-right corner of header, next to "Before/After" toggle

**HTML**:
```html
<div class="theme-toggle">
    <label class="switch">
        <input type="checkbox" id="dark-mode-toggle">
        <span class="slider round"></span>
    </label>
    <span class="theme-label">Dark Mode</span>
</div>
```

**CSS for Toggle Switch**:
```css
.switch {
    position: relative;
    display: inline-block;
    width: 50px;
    height: 24px;
}

.switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #ccc;
    transition: 0.4s;
    border-radius: 24px;
}

.slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: 0.4s;
    border-radius: 50%;
}

input:checked + .slider {
    background-color: #2196F3;
}

input:checked + .slider:before {
    transform: translateX(26px);
}
```

#### 2. Dark Mode Color Palette

**CSS Variables**:
```css
:root {
    /* Light mode (default) */
    --bg-primary: #ffffff;
    --bg-secondary: #f5f5f5;
    --bg-tree: #fafafa;
    --text-primary: #2c3e50;
    --text-secondary: #7f8c8d;
    --border-color: #e0e0e0;
    --highlight-bg: #fff9e6;
    --change-color: #f0ad4e;
    --deleted-bg: #2a1a1a;
    --deleted-color: #ff6b6b;
}

[data-theme="dark"] {
    /* Dark mode */
    --bg-primary: #1e1e1e;
    --bg-secondary: #2d2d2d;
    --bg-tree: #252525;
    --text-primary: #e0e0e0;
    --text-secondary: #b0b0b0;
    --border-color: #404040;
    --highlight-bg: #3a3a2a;
    --change-color: #ffa500;
    --deleted-bg: #3a1a1a;
    --deleted-color: #ff8080;
}

body {
    background-color: var(--bg-primary);
    color: var(--text-primary);
}

.tree-container {
    background-color: var(--bg-tree);
    border-color: var(--border-color);
}

.tree-node.has-changes {
    background-color: var(--highlight-bg);
    color: var(--change-color);
}

.deleted-function {
    background-color: var(--deleted-bg);
    color: var(--deleted-color);
}
```

#### 3. JavaScript Toggle Logic

```javascript
// On page load, check saved preference
document.addEventListener('DOMContentLoaded', () => {
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    const savedTheme = localStorage.getItem('theme') || 'light';

    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        darkModeToggle.checked = true;
    }

    darkModeToggle.addEventListener('change', (e) => {
        if (e.target.checked) {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    });
});
```

#### 4. Syntax Highlighting for Dark Mode

**diff2html Dark Theme**:
```javascript
// When rendering diffs in dark mode
if (document.documentElement.getAttribute('data-theme') === 'dark') {
    const diffHtml = Diff2Html.html(diffContent, {
        drawFileList: false,
        matching: 'lines',
        outputFormat: 'line-by-line',
        colorScheme: 'dark'  // Use dark color scheme
    });
}
```

### User Experience

**Features**:
- Persists preference in `localStorage`
- Smooth transition animations (0.3s)
- All UI elements adapt (buttons, panels, modals)
- Syntax highlighting adjusts for readability
- Icon changes: ☀️ (light) / 🌙 (dark)

**Accessibility**:
- Respects `prefers-color-scheme` media query
- Sufficient contrast ratios (WCAG AA)
- Keyboard accessible (Tab to toggle, Space to activate)

### Benefits
- Reduced eye strain in low-light environments
- Modern UI feature expected by developers
- Improved focus during extended analysis sessions
- Professional appearance

---

## 🟢 MEDIUM: Code Quality - Return Type Hints

### Motivation
Many functions in the codebase lack return type hints, which reduces IDE support, type checking effectiveness, and code documentation quality. Adding comprehensive type hints improves developer experience and catches potential type errors early.

### Current State
- Approximately 40+ functions missing return type hints
- Most commonly in:
  - `src/cli.py` - Command functions and helpers
  - `src/web/server.py` - API endpoint handlers
  - `src/analyzer/orchestrator.py` - Analysis methods
  - Various utility functions

### Implementation Plan

**Files to Update**:

1. **cli.py**:
```python
# Before
def count_functions(nodes):
    """Count total functions in a list of tree nodes recursively."""

# After
def count_functions(nodes: List[CallTreeNode]) -> int:
    """Count total functions in a list of tree nodes recursively."""
```

2. **server.py**:
```python
# Before
def _find_function_in_tree(qualified_name: str):
    """Find a function in the tree data by qualified name."""

# After
def _find_function_in_tree(qualified_name: str) -> Optional[Dict[str, Any]]:
    """Find a function in the tree data by qualified name."""
```

3. **orchestrator.py**:
```python
# Before
def _discover_files(self):
    """Discover all relevant source files in project."""

# After
def _discover_files(self) -> List[Path]:
    """Discover all relevant source files in project."""
```

**Benefits**:
- Better IDE autocomplete and inline documentation
- Catch type errors during development (with mypy)
- Self-documenting code
- Easier refactoring with type safety

**Effort**: Low (1-2 hours)
**Impact**: Medium (improved developer experience)

---

## Additional Future Enhancements

### 🔵 LOW Priority

#### 1. Export Capabilities
- Export call tree as PNG/SVG
- Export diff report as PDF
- Export architecture diagram

#### 2. Compare Multiple Refs
- Side-by-side comparison of 3+ branches
- Visualize evolution across commits

#### 3. Performance Optimizations
- Lazy-load large trees (virtualized rendering)
- Cache analysis results
- Incremental analysis (only changed files)

#### 4. Advanced Filters
- Filter by file patterns (glob)
- Filter by change type (added/modified/deleted)
- Filter by complexity metrics

#### 5. Integration Features
- VS Code extension
- GitHub PR integration (comment with diff link)
- CI/CD pipeline integration

---

## Implementation Priority

### Phase 1 (Critical)
1. Comprehensive test suite
2. Fix remaining code duplication
3. Complete constants/utilities migration

### Phase 2 (High Value)
1. Architecture block diagram
2. Improved diff header design
3. Dark mode toggle

### Phase 3 (Polish)
1. Export capabilities
2. Performance optimizations
3. VS Code extension

---

**Last Updated**: 2026-02-07
