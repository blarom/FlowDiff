# FlowDiff: Diff Visualization Implementation Plan

## Overview
Add git-based diff visualization showing before/after function call trees with intuitive side-by-side comparison.

---

## Phase 1: Strengthen Entry Point Detection (HIGH PRIORITY)

### Problem
Current logic is too permissive - treats many functions as entry points that shouldn't be (e.g., `_safe_evaluate`).

### Solution: Conservative Entry Point Detection with CLI Script Recognition

**Rules (in order of priority):**

1. **Explicit Entry Points** (always include):
   - Functions with `if __name__ == "__main__":` guard that call them
   - Test functions: `test_*` (pytest/unittest)
   - Setup/teardown: `setUp`, `tearDown`, etc.

2. **CLI Scripts** (NEW - command-line scripts):
   - Functions that use `argparse.ArgumentParser`
   - Functions that access `sys.argv`
   - Functions decorated with `@click.command`, `@typer.command`, etc.
   - **Example**: `analyze_stock()` that uses argparse is an entry point

3. **Named Entry Points** (only specific names):
   - Exactly: `main`, `run`, `execute`, `start`, `init`, `initialize`
   - NOT variations like `run_*` or `initialize_*` - these are utilities

4. **Exclude from Entry Points** (never show as top-level):
   - Private/internal functions: starts with `_` (e.g., `_safe_evaluate`, `__init__`)
   - Dunder methods: `__str__`, `__repr__`, `__call__`, etc.
   - Class methods: anything inside a class (methods, not entry points)
   - Property getters/setters: decorated with `@property`, `@*.setter`

5. **Default behavior**:
   - If none of the above apply and function is not called by anyone → **NOT an entry point**
   - Be skeptical: better to miss an entry point than show noise

### Implementation

**File**: `src/analyzer/call_tree_builder.py`

Add:
- `_find_main_guard_calls()`: Parse `if __name__ == "__main__":` block and extract called functions ✅
- `_uses_cli_parsing()`: Detect argparse, sys.argv, click/typer decorators ✅
- `_is_private_or_internal()`: Check if function name suggests internal use ✅
- `_is_class_method()`: Check if function is inside a class definition ✅
- Updated `_is_real_entry_point()` to be conservative but recognize CLI scripts ✅
- Updated `_looks_like_entry_point()` to default to `False` ✅

**Status**: ✅ COMPLETED

---

## Phase 2: Backend - Git Diff Extraction

### Goal
Create backend API to extract git diffs and analyze function changes.

### New Files

**1. `src/analyzer/git_diff_analyzer.py`**
```python
class GitDiffAnalyzer:
    """Extract and analyze git diffs for function changes."""

    def get_file_contents_at_ref(ref: str, file_path: str) -> str:
        """Get file contents at a git ref (commit/branch)."""
        # Use: git show <ref>:<file_path>

    def get_changed_files(before_ref: str, after_ref: str) -> List[str]:
        """Get list of Python files that changed between refs."""
        # Use: git diff --name-only <before>..<after> -- '*.py'

    def analyze_diff(project_path: Path, before_ref: str, after_ref: str) -> DiffResult:
        """Compare function trees between two refs."""
        # 1. Get changed files
        # 2. For each file:
        #    a. Parse functions at before_ref
        #    b. Parse functions at after_ref
        #    c. Compare function signatures and bodies
        # 3. Return structured diff data

@dataclass
class FunctionDiff:
    """Represents a diff for a single function."""
    status: str  # 'added', 'deleted', 'modified', 'unchanged'
    function_name: str
    qualified_name: str
    file_path: str

    # For modified functions
    before_code: Optional[str]
    after_code: Optional[str]
    before_line: Optional[int]
    after_line: Optional[int]

    # Changes
    params_changed: bool
    return_type_changed: bool
    body_changed: bool
    calls_changed: bool  # Different functions called

    # Detailed line changes (for visualization)
    line_changes: List[LineDiff]  # added/removed/modified lines

@dataclass
class DiffResult:
    """Complete diff analysis between two refs."""
    before_ref: str
    after_ref: str
    changed_files: List[str]
    function_diffs: Dict[str, FunctionDiff]  # qualified_name -> diff

    # Trees for visualization
    before_tree: List[CallTreeNode]
    after_tree: List[CallTreeNode]

    # Summary stats
    functions_added: int
    functions_deleted: int
    functions_modified: int
    functions_unchanged: int
```

**2. Update `src/web/server.py`**

Add endpoint:
```python
@app.post("/api/diff")
async def get_diff(request: Request):
    """Get diff between two git refs."""
    body = await request.json()
    before_ref = body.get("before")
    after_ref = body.get("after")

    # Special handling for "working" (uncommitted changes)
    if after_ref == "working":
        # Compare against working directory
        pass

    analyzer = GitDiffAnalyzer(project_path)
    diff_result = analyzer.analyze_diff(project_path, before_ref, after_ref)

    return JSONResponse(serialize_diff_result(diff_result))
```

---

## Phase 3: Frontend - Diff Visualization UI

### Goal
Create intuitive split-view interface showing before/after with highlighted changes.

### Industry Best Practices (Inspiration)

**GitHub Diff View**:
- Split view (before | after)
- Line-by-line highlighting (red removed, green added)
- Collapsible unchanged sections
- File tree on left

**VS Code Diff**:
- Inline diff with side-by-side toggle
- Syntax highlighting preserved
- Scroll synchronization between panes

**IntelliJ IDEA**:
- 3-way merge view
- Smart change detection (method extracted, renamed, etc.)
- Navigation between changes

### Our Design

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│ FlowDiff - Diff View               [Back to Tree] [Export Diff] │
├─────────────────────────────────────────────────────────────────┤
│ ┌───────────────┐  ┌──────────────────────────────────────────┐│
│ │ Changed       │  │ Diff View                                ││
│ │ Functions     │  │ ┌──────────────┬──────────────────────┐ ││
│ │               │  │ │   Before     │      After           │ ││
│ │ 📁 file.py    │  │ │  (HEAD~1)    │   (Working Dir)      │ ││
│ │  🔴 modified  │  │ ├──────────────┼──────────────────────┤ ││
│ │   └ main()    │  │ │ 1 def main():│ 1 def main():        │ ││
│ │  🟢 added     │  │ │ 2   old_var  │ 2   new_var          │ ││
│ │   └ new_fn()  │  │ │ 3   process()│ 3   process()        │ ││
│ │  🔴 deleted   │  │ │              │ 4   # New logic      │ ││
│ │   └ old_fn()  │  │ │              │ 5   analyze()        │ ││
│ │               │  │ └──────────────┴──────────────────────┘ ││
│ │ 🔵 Unchanged  │  │                                          ││
│ │  (collapsed)  │  │ Legend:                                  ││
│ │  └ helper()   │  │ 🟢 Added  🔴 Removed  🟡 Modified        ││
│ └───────────────┘  └──────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### New Files

**1. `src/web/static/diff.html`**
- New page for diff view
- Split-pane layout
- Function tree on left, diff on right

**2. `src/web/static/diff.css`**
- Styling for diff view
- Color coding:
  - Red background: removed lines
  - Green background: added lines
  - Yellow highlight: modified lines
  - Grey: unchanged (collapsed)

**3. `src/web/static/diff.js`**
```javascript
class DiffView {
    constructor(diffData) {
        this.diffData = diffData;
        this.currentFunction = null;
    }

    renderFunctionTree() {
        // Render left pane: tree of changed functions
        // Group by file, then function
        // Color code by status
    }

    renderSideBySideDiff(functionDiff) {
        // Render right pane: before/after comparison
        // Syntax highlight code
        // Highlight changed lines
        // Sync scrolling between panes
    }

    renderUnifiedDiff(functionDiff) {
        // Alternative: unified diff view (like git diff)
        // +/- prefix for added/removed
    }

    collapseUnchanged() {
        // Collapse sections with no changes
        // Show "... X unchanged lines ..."
    }

    jumpToNextChange() {
        // Navigate between changes
    }
}
```

### Features to Implement

1. **Function Tree (Left Pane)**
   - Expandable file list
   - Status icons: 🟢 added, 🔴 modified/deleted, 🔵 unchanged
   - Click function → show diff on right
   - Filter: show only changed/show all

2. **Diff View (Right Pane)**
   - Toggle: Side-by-Side | Unified
   - Syntax highlighting (use Prism.js or highlight.js)
   - Line numbers
   - Sync scrolling (when in split view)
   - Collapse unchanged sections
   - Copy code buttons

3. **Navigation**
   - "Previous/Next Change" buttons
   - Jump to function from tree
   - Keyboard shortcuts (n/p for next/previous)

4. **Export**
   - Export as HTML
   - Export as unified diff (git format)
   - Copy to clipboard

---

## Phase 4: Advanced Features (Future)

### Call Graph Changes
- Show how function calls changed
- Visualize: "Function X now calls Y instead of Z"
- Highlight: new dependencies, removed dependencies

### Semantic Diff
- Detect refactoring (function renamed but logic same)
- Detect extracted methods
- Detect moved code

### Multi-commit Comparison
- Compare across multiple commits
- Show evolution of a function
- Timeline slider

---

## Implementation Order

1. **Phase 1: Strengthen Entry Point Detection** ⭐ HIGH PRIORITY
   - Filter out `_private` functions
   - Make default behavior skeptical
   - Only show truly meaningful entry points

2. **Phase 2: Backend Git Integration**
   - Implement `GitDiffAnalyzer`
   - Add `/api/diff` endpoint
   - Test with simple diffs

3. **Phase 3: Basic Diff UI**
   - Create diff.html with split layout
   - Implement function tree view
   - Implement basic side-by-side diff

4. **Phase 3.1: Polish Diff UI**
   - Add syntax highlighting
   - Add collapse/expand
   - Add navigation

5. **Phase 4: Advanced Features** (optional)
   - Export functionality
   - Semantic diff detection
   - Call graph visualization

---

## Testing Strategy

1. **Entry Point Detection**: Test with various Python projects
   - Should NOT show: `_helper()`, `__init__()`, `get_data()`
   - Should show: `main()`, `test_something()`, functions called in `__main__`

2. **Diff Analysis**: Test with known git repos
   - Simple add/delete
   - Function modification
   - File rename
   - Merge conflicts

3. **UI Testing**: Manual testing
   - Navigate between changes
   - Collapse/expand
   - Side-by-side vs unified
   - Mobile/responsive

---

## Estimated Complexity

- **Phase 1 (Entry Points)**: 1-2 hours (CRITICAL)
- **Phase 2 (Backend)**: 3-4 hours
- **Phase 3 (UI)**: 4-6 hours
- **Total**: 8-12 hours for complete feature

---

## Dependencies

- **Git**: Required on system (check with `git --version`)
- **Syntax Highlighter**: Prism.js or highlight.js (CDN)
- **Difflib**: Python's built-in `difflib` for line-by-line diff

---

## Risk Mitigation

1. **Git not installed**: Detect and show error message
2. **Invalid ref**: Handle gracefully, suggest valid refs
3. **Large diffs**: Paginate or limit to N functions
4. **Binary files**: Skip non-.py files
5. **Merge conflicts**: Show warning, may not parse correctly

---

## Success Criteria

✅ Entry point detection is very conservative (no noise)
✅ Can load diff between any two git refs
✅ Diff view clearly shows what changed
✅ Easy to navigate between changes
✅ Professional, GitHub-quality UI
✅ Export/share functionality works

---

## Next Steps

**Immediate**: Implement Phase 1 (strengthen entry point detection)
- Fix `_safe_evaluate` showing as top-level
- Filter out all private/internal functions
- Make logic very skeptical

**After approval**: Proceed with Phase 2 (git backend)
