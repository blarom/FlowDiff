# FlowDiff: Git Diff Visualization - Implementation Plan

## Overview

This plan transforms FlowDiff into a change-first diff visualization tool with:
- Professional split-pane UI (GitHub/VS Code quality)
- Any-vs-any git comparison (commits, branches, tags)
- Smart defaults (uncommitted vs HEAD)
- Clean architecture with no technical debt
- Export and LLM frameworks (implementation deferred to Phase 2)

---

## Step 0: Git Repository Initialization

### Initialize Git Repository

```bash
cd /Users/barlarom/PycharmProjects/Main/FlowDiff
git init
```

### Create .gitignore

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv
*.egg-info/
dist/
build/

# IDE
.vscode/
.idea/
*.swp
*.swo

# FlowDiff specific
.flowdiff/cache/
*.log

# OS
.DS_Store
Thumbs.db
```

### Initial Commit

```bash
git add .
git commit -m "Initial commit: FlowDiff multi-language call tree analyzer

- Symbol-based architecture with Python and Shell support
- Cross-language bridge system (HTTP → Python)
- Dynamic tree expansion based on changes
- Web UI with FastAPI backend
- Documentation extraction and display
"
```

### Connect to GitHub

**Option A: Via GitHub Web Interface**
1. Go to https://github.com/new
2. Repository name: `FlowDiff`
3. Description: "Multi-language call tree analyzer with git diff visualization"
4. Choose Public or Private
5. Don't initialize with README
6. Click "Create repository"

**Option B: Via GitHub CLI** (if installed)
```bash
gh repo create FlowDiff --public --source=. --remote=origin \
  --description="Multi-language call tree analyzer with git diff visualization"
```

### Setup GitHub Authentication & Push

GitHub no longer accepts passwords. Choose one authentication method:

**Method A: Personal Access Token (HTTPS) - Recommended for beginners**

1. Create token:
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token" → "Generate new token (classic)"
   - Name: "FlowDiff Development"
   - Expiration: 90 days (or your preference)
   - Scopes: Check `repo` (full control)
   - Click "Generate token"
   - **IMPORTANT: Copy the token immediately** (won't be shown again)

2. Push to GitHub:
```bash
git remote add origin https://github.com/YOUR_USERNAME/FlowDiff.git
git branch -M main
git push -u origin main
# When prompted:
# Username: YOUR_USERNAME
# Password: <paste your token here, not your GitHub password>
```

**Method B: SSH Keys - More secure, no expiration**

1. Check for existing SSH key:
```bash
ls -la ~/.ssh
# Look for id_ed25519.pub or id_rsa.pub
```

2. If no key exists, generate one:
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
# Press Enter to accept default location
# Enter passphrase (optional but recommended)
```

3. Add SSH key to ssh-agent:
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

4. Copy public key to clipboard:
```bash
pbcopy < ~/.ssh/id_ed25519.pub
```

5. Add to GitHub:
   - Go to: https://github.com/settings/keys
   - Click "New SSH key"
   - Title: "FlowDiff Development"
   - Paste the key
   - Click "Add SSH key"

6. Push to GitHub:
```bash
git remote add origin git@github.com:YOUR_USERNAME/FlowDiff.git
git branch -M main
git push -u origin main
```

---

## Section 1: Legacy Code Cleanup (971 lines removed)

### Task 1.1: Create Legacy Module

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/analyzer/legacy.py`:

```python
"""Legacy data structures for backward compatibility with UI."""
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class FunctionInfo:
    """Legacy FunctionInfo for backward compatibility with UI."""
    name: str
    qualified_name: str
    file_path: str
    file_name: str
    line_number: int
    parameters: List[str]
    return_type: str
    calls: List[str]
    called_by: List[str] = field(default_factory=list)
    local_variables: List[str] = field(default_factory=list)
    is_entry_point: bool = False
    language: str = "python"
    http_method: Optional[str] = None
    http_route: Optional[str] = None
    has_changes: bool = False
    documentation: Optional[str] = None

@dataclass
class CallTreeNode:
    """Legacy CallTreeNode for backward compatibility with UI."""
    function: FunctionInfo
    children: List['CallTreeNode'] = field(default_factory=list)
    depth: int = 0
    is_expanded: bool = False
```

### Task 1.2: Update CallTreeAdapter

Update `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/analyzer/call_tree_adapter.py`:
- Remove duplicate class definitions (lines 12-40)
- Import from legacy module: `from .legacy import FunctionInfo, CallTreeNode`

### Task 1.3: Delete Deprecated Code

```bash
# Backup first
git checkout -b backup/call-tree-builder
git add src/analyzer/call_tree_builder.py
git commit -m "Backup: call_tree_builder.py before deletion"
git checkout main

# Delete
rm src/analyzer/call_tree_builder.py
```

### Verification Checklist

- [ ] `analyzer/legacy.py` created
- [ ] `call_tree_adapter.py` imports from legacy module
- [ ] `call_tree_builder.py` deleted
- [ ] Tests pass: `python3 test_comprehensive.py`
- [ ] Commit: "refactor: Remove legacy call_tree_builder.py (971 lines)"

---

## Section 2: Git Diff Backend

### Architecture

```
GitDiffAnalyzer
├── GitRefResolver (parse refs: HEAD, branches, commits)
├── FileChangeDetector (git diff --name-status)
├── SymbolChangeMapper (map file changes → symbol changes)
└── DiffResultBuilder (build before/after trees)
```

### Task 2.1: Create GitRefResolver

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/analyzer/git/ref_resolver.py`:

```python
"""Git reference resolver for FlowDiff."""
from pathlib import Path
from typing import Optional
import subprocess

class GitRefResolver:
    """Resolve git reference strings to commit SHAs."""

    WORKING_TREE_MARKER = "working"

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._verify_git_repo()

    def _verify_git_repo(self) -> None:
        """Check if project_root is a git repository."""
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {self.project_root}")

    def resolve(self, ref: str) -> Optional[str]:
        """Resolve ref to commit SHA.

        Returns None for "working" (uncommitted changes).
        """
        if ref == self.WORKING_TREE_MARKER:
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--verify", ref],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Invalid git ref '{ref}': {e.stderr.strip()}")

    def get_ref_description(self, ref: str) -> str:
        """Get human-readable description."""
        if ref == self.WORKING_TREE_MARKER:
            return "Working directory (uncommitted changes)"

        sha = self.resolve(ref)
        try:
            result = subprocess.run(
                ["git", "name-rev", "--name-only", sha],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            return f"{ref} ({branch}, {sha[:7]})"
        except:
            return f"{ref} ({sha[:7]})"
```

### Task 2.2: Create FileChangeDetector

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/analyzer/git/file_change_detector.py`:

```python
"""Detect file changes between git refs."""
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum
import subprocess

class ChangeType(Enum):
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"

@dataclass
class FileChange:
    path: str
    change_type: ChangeType
    old_path: Optional[str] = None

class FileChangeDetector:
    """Detect file changes between git refs."""

    SUPPORTED_EXTENSIONS = {".py", ".sh"}

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def get_changed_files(
        self,
        before_ref: Optional[str],
        after_ref: Optional[str]
    ) -> List[FileChange]:
        """Get changed files between two refs."""
        cmd = ["git", "diff", "--name-status"]

        if before_ref is None and after_ref is None:
            raise ValueError("At least one ref must be specified")
        elif after_ref is None:
            cmd.append(before_ref)
        elif before_ref is None:
            cmd.extend([after_ref, "--"])
        else:
            cmd.extend([f"{before_ref}..{after_ref}"])

        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=True
        )

        changes = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            change = self._parse_change_line(line)
            if change and self._is_supported_file(change.path):
                changes.append(change)

        return changes

    def _parse_change_line(self, line: str) -> Optional[FileChange]:
        """Parse git diff --name-status line."""
        parts = line.split("\t")
        if len(parts) < 2:
            return None

        status = parts[0][0]
        try:
            change_type = ChangeType(status)
        except ValueError:
            return None

        if change_type == ChangeType.RENAMED:
            return FileChange(
                path=parts[2],
                change_type=change_type,
                old_path=parts[1]
            )
        else:
            return FileChange(
                path=parts[1],
                change_type=change_type
            )

    def _is_supported_file(self, path: str) -> bool:
        return Path(path).suffix in self.SUPPORTED_EXTENSIONS
```

### Task 2.3: Create SymbolChangeMapper

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/analyzer/git/symbol_change_mapper.py`:

```python
"""Map file changes to symbol changes."""
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import subprocess
import tempfile

from ..orchestrator import FlowDiffOrchestrator
from ..core.symbol import Symbol
from .file_change_detector import FileChange, ChangeType

@dataclass
class SymbolChange:
    qualified_name: str
    change_type: ChangeType
    before_symbol: Optional[Symbol] = None
    after_symbol: Optional[Symbol] = None

class SymbolChangeMapper:
    """Map file-level changes to symbol-level changes."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def map_changes(
        self,
        before_ref: Optional[str],
        after_ref: Optional[str],
        file_changes: List[FileChange]
    ) -> Dict[str, SymbolChange]:
        """Map file changes to symbol changes."""
        before_symbols = self._build_symbol_table_at_ref(before_ref) if before_ref else {}
        after_symbols = self._build_symbol_table_at_ref(after_ref) if after_ref else self._build_current_symbol_table()

        symbol_changes = {}

        # Modified and deleted
        for qname, before_sym in before_symbols.items():
            if qname in after_symbols:
                after_sym = after_symbols[qname]
                if self._symbols_differ(before_sym, after_sym):
                    symbol_changes[qname] = SymbolChange(
                        qualified_name=qname,
                        change_type=ChangeType.MODIFIED,
                        before_symbol=before_sym,
                        after_symbol=after_sym
                    )
            else:
                symbol_changes[qname] = SymbolChange(
                    qualified_name=qname,
                    change_type=ChangeType.DELETED,
                    before_symbol=before_sym
                )

        # Added
        for qname, after_sym in after_symbols.items():
            if qname not in before_symbols:
                symbol_changes[qname] = SymbolChange(
                    qualified_name=qname,
                    change_type=ChangeType.ADDED,
                    after_symbol=after_sym
                )

        return symbol_changes

    def _build_symbol_table_at_ref(self, ref: str) -> Dict[str, Symbol]:
        """Build symbol table at specific git ref."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "checkout"
            tmp_path.mkdir()

            subprocess.run(
                ["git", "archive", ref, "|", "tar", "-x", "-C", str(tmp_path)],
                cwd=self.project_root,
                shell=True,
                check=True
            )

            orchestrator = FlowDiffOrchestrator(tmp_path)
            symbol_tables = orchestrator.analyze()

            all_symbols = {}
            for table in symbol_tables.values():
                for symbol in table.get_all_symbols():
                    all_symbols[symbol.qualified_name] = symbol

            return all_symbols

    def _build_current_symbol_table(self) -> Dict[str, Symbol]:
        """Build symbol table for working tree."""
        orchestrator = FlowDiffOrchestrator(self.project_root)
        symbol_tables = orchestrator.analyze()

        all_symbols = {}
        for table in symbol_tables.values():
            for symbol in table.get_all_symbols():
                all_symbols[symbol.qualified_name] = symbol

        return all_symbols

    def _symbols_differ(self, before: Symbol, after: Symbol) -> bool:
        """Check if symbols differ."""
        if before.line_number != after.line_number:
            return True
        if before.metadata != after.metadata:
            return True
        if set(before.resolved_calls) != set(after.resolved_calls):
            return True
        if before.documentation != after.documentation:
            return True
        return False
```

### Task 2.4: Create GitDiffAnalyzer

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/analyzer/git/diff_analyzer.py`:

```python
"""Main git diff analyzer."""
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from ..legacy import CallTreeNode
from ..call_tree_adapter import CallTreeAdapter
from .ref_resolver import GitRefResolver
from .file_change_detector import FileChangeDetector, FileChange
from .symbol_change_mapper import SymbolChangeMapper, SymbolChange

@dataclass
class DiffResult:
    """Complete diff analysis."""
    before_ref: str
    after_ref: str
    before_description: str
    after_description: str
    file_changes: List[FileChange]
    symbol_changes: Dict[str, SymbolChange]
    before_tree: List[CallTreeNode]
    after_tree: List[CallTreeNode]
    functions_added: int
    functions_deleted: int
    functions_modified: int
    functions_unchanged: int

class GitDiffAnalyzer:
    """Analyze git diffs and build before/after call trees."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.ref_resolver = GitRefResolver(project_root)
        self.file_detector = FileChangeDetector(project_root)
        self.symbol_mapper = SymbolChangeMapper(project_root)

    def analyze_diff(
        self,
        before: str = "HEAD",
        after: str = "working"
    ) -> DiffResult:
        """Analyze diff between two refs."""
        before_sha = self.ref_resolver.resolve(before)
        after_sha = self.ref_resolver.resolve(after)

        file_changes = self.file_detector.get_changed_files(before_sha, after_sha)
        symbol_changes = self.symbol_mapper.map_changes(before_sha, after_sha, file_changes)

        before_tree = self._build_tree_at_ref(before_sha, symbol_changes, True)
        after_tree = self._build_tree_at_ref(after_sha, symbol_changes, False)

        stats = self._calculate_stats(symbol_changes)

        return DiffResult(
            before_ref=before,
            after_ref=after,
            before_description=self.ref_resolver.get_ref_description(before),
            after_description=self.ref_resolver.get_ref_description(after),
            file_changes=file_changes,
            symbol_changes=symbol_changes,
            before_tree=before_tree,
            after_tree=after_tree,
            **stats
        )

    def _build_tree_at_ref(
        self,
        ref: Optional[str],
        symbol_changes: Dict[str, SymbolChange],
        is_before: bool
    ) -> List[CallTreeNode]:
        """Build call tree with has_changes populated."""
        adapter = CallTreeAdapter(self.project_root)
        trees = adapter.analyze_project()
        self._mark_changed_nodes(trees, symbol_changes)
        return trees

    def _mark_changed_nodes(
        self,
        trees: List[CallTreeNode],
        symbol_changes: Dict[str, SymbolChange]
    ) -> None:
        """Mark nodes with changes."""
        def mark_recursive(node: CallTreeNode):
            if node.function.qualified_name in symbol_changes:
                node.function.has_changes = True
            for child in node.children:
                mark_recursive(child)

        for tree in trees:
            mark_recursive(tree)

    def _calculate_stats(self, symbol_changes: Dict[str, SymbolChange]) -> Dict[str, int]:
        """Calculate summary statistics."""
        added = sum(1 for sc in symbol_changes.values() if sc.change_type.value == "A")
        deleted = sum(1 for sc in symbol_changes.values() if sc.change_type.value == "D")
        modified = sum(1 for sc in symbol_changes.values() if sc.change_type.value == "M")

        return {
            "functions_added": added,
            "functions_deleted": deleted,
            "functions_modified": modified,
            "functions_unchanged": 0
        }
```

### Task 2.5: Add API Endpoint

Update `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/web/server.py`:

```python
from analyzer.git.diff_analyzer import GitDiffAnalyzer, DiffResult

@app.post("/api/diff")
async def get_diff(request: Request):
    """Get diff between two git refs."""
    try:
        body = await request.json()
        before_ref = body.get("before", "HEAD")
        after_ref = body.get("after", "working")

        analyzer = GitDiffAnalyzer(project_path)
        diff_result = analyzer.analyze_diff(before_ref, after_ref)

        return JSONResponse(content=_serialize_diff_result(diff_result))
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

def _serialize_diff_result(diff: DiffResult) -> dict:
    """Convert DiffResult to JSON."""
    return {
        "before_ref": diff.before_ref,
        "after_ref": diff.after_ref,
        "before_description": diff.before_description,
        "after_description": diff.after_description,
        "summary": {
            "added": diff.functions_added,
            "deleted": diff.functions_deleted,
            "modified": diff.functions_modified
        },
        "before_tree": [_serialize_tree_node(n) for n in diff.before_tree],
        "after_tree": [_serialize_tree_node(n) for n in diff.after_tree]
    }
```

### Verification Checklist

- [ ] All git modules created
- [ ] API endpoint returns proper JSON
- [ ] Test with real git repo
- [ ] Commit: "feat: Add git diff backend infrastructure"

---

## Section 3: Diff Visualization UI

### Task 3.1: Create diff.html

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/web/static/diff.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>FlowDiff - Diff View</title>
    <link rel="stylesheet" href="diff.css">
</head>
<body>
    <div class="diff-container">
        <div class="diff-header">
            <h1>FlowDiff - Diff View</h1>
            <div class="diff-actions">
                <button id="close-diff" class="btn">← Back</button>
                <button id="export-diff" class="btn" disabled>Export</button>
            </div>
        </div>

        <div class="ref-selector">
            <div class="ref-input">
                <label>Before:</label>
                <select id="before-ref">
                    <option value="HEAD~1">HEAD~1</option>
                    <option value="HEAD" selected>HEAD</option>
                    <option value="custom">Custom...</option>
                </select>
                <input type="text" id="before-custom" placeholder="Branch/commit" style="display:none;">
            </div>
            <div class="ref-input">
                <label>After:</label>
                <select id="after-ref">
                    <option value="HEAD">HEAD</option>
                    <option value="working" selected>Working directory</option>
                    <option value="custom">Custom...</option>
                </select>
                <input type="text" id="after-custom" placeholder="Branch/commit" style="display:none;">
            </div>
            <button id="load-diff" class="btn btn-primary">Load Diff</button>
        </div>

        <div id="diff-summary" class="diff-summary hidden">
            <span class="stat">🟢 <span id="stat-added">0</span> Added</span>
            <span class="stat">🔴 <span id="stat-deleted">0</span> Deleted</span>
            <span class="stat">🟡 <span id="stat-modified">0</span> Modified</span>
        </div>

        <div id="diff-split-view" class="diff-split-view hidden">
            <div class="split-pane">
                <div class="pane-header">
                    <h3 id="before-title">Before</h3>
                </div>
                <div id="before-tree" class="tree-container"></div>
            </div>

            <div class="split-pane">
                <div class="pane-header">
                    <h3 id="after-title">After</h3>
                </div>
                <div id="after-tree" class="tree-container"></div>
            </div>
        </div>

        <div id="loading" class="loading hidden">
            <div class="spinner"></div>
            <p>Analyzing diff...</p>
        </div>
    </div>

    <script src="diff.js"></script>
</body>
</html>
```

### Task 3.2: Create diff.css

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/web/static/diff.css`:

```css
:root {
    --color-added: #d4edda;
    --color-deleted: #f8d7da;
    --color-modified: #fff3cd;
}

.diff-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

.diff-header {
    display: flex;
    justify-content: space-between;
    padding: 1rem 2rem;
    background: #2c3e50;
    color: white;
}

.ref-selector {
    display: flex;
    gap: 1rem;
    padding: 1rem 2rem;
    background: #ecf0f1;
}

.diff-summary {
    padding: 1rem 2rem;
    background: white;
    border-bottom: 1px solid #ddd;
}

.stat {
    margin-right: 2rem;
    font-weight: 600;
}

.diff-split-view {
    display: grid;
    grid-template-columns: 1fr 1fr;
    flex: 1;
    overflow: hidden;
}

.split-pane {
    border-right: 2px solid #ddd;
    overflow-y: auto;
}

.pane-header {
    padding: 0.75rem;
    background: #34495e;
    color: white;
}

.tree-node.added {
    background: var(--color-added);
}

.tree-node.deleted {
    background: var(--color-deleted);
}

.tree-node.modified {
    background: var(--color-modified);
}

.hidden {
    display: none;
}

.btn {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.btn-primary {
    background: #3498db;
    color: white;
}
```

### Task 3.3: Create diff.js

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/web/static/diff.js`:

```javascript
(function() {
    'use strict';

    let currentDiff = null;

    document.addEventListener('DOMContentLoaded', init);

    function init() {
        setupEventListeners();
        loadDefaultDiff();
    }

    function setupEventListeners() {
        document.getElementById('load-diff').addEventListener('click', loadDiff);
        document.getElementById('close-diff').addEventListener('click', () => {
            window.location.href = '/';
        });
    }

    async function loadDefaultDiff() {
        await loadDiff('HEAD', 'working');
    }

    async function loadDiff(before, after) {
        if (!before) {
            const beforeSelect = document.getElementById('before-ref');
            before = beforeSelect.value === 'custom'
                ? document.getElementById('before-custom').value
                : beforeSelect.value;
        }

        if (!after) {
            const afterSelect = document.getElementById('after-ref');
            after = afterSelect.value === 'custom'
                ? document.getElementById('after-custom').value
                : afterSelect.value;
        }

        showLoading(true);

        try {
            const response = await fetch('/api/diff', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ before, after })
            });

            if (!response.ok) {
                throw new Error('Failed to load diff');
            }

            currentDiff = await response.json();
            renderDiff();
        } catch (error) {
            alert('Error: ' + error.message);
        } finally {
            showLoading(false);
        }
    }

    function renderDiff() {
        document.getElementById('before-title').textContent = currentDiff.before_description;
        document.getElementById('after-title').textContent = currentDiff.after_description;

        document.getElementById('stat-added').textContent = currentDiff.summary.added;
        document.getElementById('stat-deleted').textContent = currentDiff.summary.deleted;
        document.getElementById('stat-modified').textContent = currentDiff.summary.modified;

        renderTree('before-tree', currentDiff.before_tree);
        renderTree('after-tree', currentDiff.after_tree);

        document.getElementById('diff-summary').classList.remove('hidden');
        document.getElementById('diff-split-view').classList.remove('hidden');
    }

    function renderTree(containerId, trees) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        trees.forEach(tree => {
            const elem = renderTreeNode(tree);
            container.appendChild(elem);
        });
    }

    function renderTreeNode(node, depth = 0) {
        const div = document.createElement('div');
        div.className = 'tree-node';
        div.style.marginLeft = `${depth * 1.5}rem`;

        if (node.function.has_changes) {
            div.classList.add('modified');
        }

        const label = document.createElement('div');
        label.textContent = `${node.children.length > 0 ? '📁' : '📄'} ${node.function.name}`;
        div.appendChild(label);

        if (node.is_expanded) {
            node.children.forEach(child => {
                div.appendChild(renderTreeNode(child, depth + 1));
            });
        }

        return div;
    }

    function showLoading(show) {
        document.getElementById('loading').classList.toggle('hidden', !show);
    }
})();
```

### Task 3.4: Add Route

Update `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/web/server.py`:

```python
@app.get("/diff.html")
async def diff_page():
    html_path = static_dir / "diff.html"
    return FileResponse(html_path)
```

### Verification Checklist

- [ ] Diff view renders correctly
- [ ] Split-pane layout works
- [ ] Changed nodes highlighted
- [ ] Ref selection works
- [ ] Commit: "feat: Add split-pane diff visualization UI"

---

## Section 4: Integration & Testing

### Task 4.1: Add Export Framework (Not Implemented)

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/web/export.py`:

```python
"""Export framework (Phase 2)."""
from pathlib import Path
from analyzer.git.diff_analyzer import DiffResult

class HTMLExporter:
    def export(self, diff_result: DiffResult, output_path: Path) -> None:
        raise NotImplementedError("HTML export coming in Phase 2")

class PDFExporter:
    def export(self, diff_result: DiffResult, output_path: Path) -> None:
        raise NotImplementedError("PDF export coming in Phase 2")
```

### Task 4.2: Add LLM Framework (Not Implemented)

Create `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/analyzer/llm/interfaces.py`:

```python
"""LLM integration interfaces (Phase 2)."""
from abc import ABC, abstractmethod

class DiffExplainer(ABC):
    @abstractmethod
    def explain_change(self, before_code: str, after_code: str) -> str:
        raise NotImplementedError("LLM explanations coming in Phase 2")
```

### Task 4.3: Add CLI Command

Update `/Users/barlarom/PycharmProjects/Main/FlowDiff/src/cli.py`:

```python
@app.command()
def diff(
    project_path: str = typer.Argument(".", help="Project directory"),
    before: str = typer.Option("HEAD", help="Before ref"),
    after: str = typer.Option("working", help="After ref"),
    port: int = typer.Option(8000, help="Port")
):
    """Show diff between git refs."""
    from .analyzer.git.diff_analyzer import GitDiffAnalyzer

    analyzer = GitDiffAnalyzer(Path(project_path))
    diff_result = analyzer.analyze_diff(before, after)

    typer.echo(f"Added: {diff_result.functions_added}")
    typer.echo(f"Modified: {diff_result.functions_modified}")
    typer.echo(f"Deleted: {diff_result.functions_deleted}")

    # Start server
    import webbrowser
    webbrowser.open(f"http://localhost:{port}/diff.html")
    start_server(port=port)
```

### Task 4.4: Update Documentation

Update `/Users/barlarom/PycharmProjects/Main/FlowDiff/README.md`:

```markdown
# FlowDiff

Multi-language call tree analyzer with git diff visualization.

## Features

- 📊 Interactive call tree visualization
- 🔀 Git diff analysis with before/after comparison
- 🌐 Multi-language support (Python, Shell)
- 🎨 Professional split-pane UI

## Usage

```bash
# View call tree
flowdiff snapshot .

# View git diff
flowdiff diff                          # Uncommitted vs HEAD
flowdiff diff --before HEAD~1          # Working vs previous
flowdiff diff --before main --after dev # Compare branches
```

## Diff Visualization

- 🟢 Green: Added functions
- 🔴 Red: Deleted functions
- 🟡 Yellow: Modified functions
```

### Verification Checklist

- [ ] Export framework exists (not implemented)
- [ ] LLM framework exists (not implemented)
- [ ] `flowdiff diff` CLI works
- [ ] Documentation updated
- [ ] All tests pass
- [ ] Commit: "feat: Add diff integration and framework hooks"

---

## Final Deliverable Checklist

### Code Quality
- [ ] No legacy code remaining
- [ ] No code duplication
- [ ] Proper error handling
- [ ] Type hints
- [ ] Docstrings

### Architecture
- [ ] Clean separation of concerns
- [ ] Git diff backend independent of UI
- [ ] Export framework extensible
- [ ] LLM integration optional

### UX
- [ ] Professional split-pane UI
- [ ] Any-vs-any comparison
- [ ] Smart defaults (working vs HEAD)
- [ ] Clear visual indicators

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing on real repos

### Documentation
- [ ] README updated
- [ ] Code comments clear
- [ ] GitHub repo initialized

---

## Verification Commands

```bash
# Verify git initialization
git remote -v
git log --oneline

# Verify legacy code removed
ls src/analyzer/call_tree_builder.py  # Should not exist

# Verify tests pass
python3 test_comprehensive.py

# Verify CLI works
flowdiff diff --help
flowdiff diff

# Verify UI loads
# Browser should open automatically
```

---

## Success Metrics

✅ Technical Debt: 971 lines removed
✅ Architecture: Clean, extensible
✅ UX: GitHub/VS Code quality
✅ Functionality: Any-vs-any comparison
✅ Performance: <5 seconds
✅ Extensibility: Framework ready
✅ Testing: Comprehensive coverage
✅ Documentation: Clear README

---

## Phase 2 Roadmap (Future)

1. **LLM Integration**
   - Diff explanations
   - Code structuring
   - Insight generation

2. **Export Features**
   - HTML snapshots
   - PDF reports
   - Unified diff format

3. **Advanced Diff**
   - Semantic diff
   - Multi-commit comparison
   - Blame integration
