# FlowDiff: Enhanced Diff Visualization with LLM-Powered Analysis

## Vision

Create an intelligent diff visualization system that:
1. Shows before/after function call trees with clear change highlighting
2. Uses LLM to structure unencapsulated legacy code into logical operations
3. Provides LLM-powered explanations of each diff in context
4. Handles both modern well-structured code and messy legacy scripts

---

## Phase 1: Core Diff Visualization (Foundation)

### 1.1 Git Diff Backend

**File**: `src/analyzer/git_diff_analyzer.py`

```python
class GitDiffAnalyzer:
    """Extract and analyze git diffs for function changes."""

    def get_file_contents_at_ref(ref: str, file_path: str) -> str:
        """Get file contents at a git ref."""
        # Use: git show <ref>:<file_path>

    def get_changed_files(before_ref: str, after_ref: str) -> List[str]:
        """Get list of changed Python files."""
        # Use: git diff --name-only <before>..<after> -- '*.py'

    def get_commit_messages(before_ref: str, after_ref: str) -> List[str]:
        """Get commit messages between refs for LLM context."""
        # Use: git log --oneline <before>..<after>

    def analyze_diff(project_path: Path, before_ref: str, after_ref: str) -> DiffResult:
        """Compare function trees between two refs."""
        # 1. Build before tree
        # 2. Build after tree
        # 3. Compare and categorize changes
        # 4. Return structured diff
```

**Data Models**:
```python
@dataclass
class FunctionDiff:
    status: str  # 'added', 'deleted', 'modified', 'unchanged'
    function_name: str
    qualified_name: str
    file_path: str

    # For modified functions
    before_code: Optional[str]
    after_code: Optional[str]
    before_line: Optional[int]
    after_line: Optional[int]

    # Change details
    params_changed: bool
    return_type_changed: bool
    body_changed: bool
    calls_changed: List[str]  # Functions added/removed from calls

    # Line-by-line diff
    unified_diff: str  # Standard unified diff format

@dataclass
class DiffResult:
    before_ref: str
    after_ref: str
    commit_messages: List[str]  # For LLM context

    changed_files: List[str]
    function_diffs: Dict[str, FunctionDiff]

    # Trees
    before_tree: List[CallTreeNode]
    after_tree: List[CallTreeNode]

    # Summary
    functions_added: int
    functions_deleted: int
    functions_modified: int
```

### 1.2 Diff UI - Split View

**Files**: `src/web/static/diff.html`, `diff.css`, `diff.js`

**Layout**:
```
┌─────────────────────────────────────────────────────────────┐
│ FlowDiff - Diff View         [Back] [Export] [Explain All] │
├──────────────┬──────────────────────────────────────────────┤
│ Changed      │  Before (HEAD~1)  │  After (Working)         │
│ Functions    │ ─────────────────  ┼  ─────────────────      │
│              │                                               │
│ 📁 file.py   │  1 def main():     │  1 def main():          │
│ 🔴 modified  │  2   old_code      │  2   new_code      [?]  │
│  └ main()    │  3   process()     │  3   process()          │
│ 🟢 added     │                    │  4   analyze()     [?]  │
│  └ analyze() │                                               │
│              │ [Previous] [Next]  │  [Copy] [Explain]       │
└──────────────┴──────────────────────────────────────────────┘
```

**Features**:
- Color-coded tree (🟢 added, 🔴 modified/deleted, 🔵 unchanged)
- Side-by-side diff with syntax highlighting
- Click function in tree → scroll to diff
- "Explain" button on each changed section (LLM integration)
- Export as HTML or unified diff

---

## Phase 2: LLM-Powered Legacy Code Structuring

### Problem Statement

Legacy scripts often have thousands of lines without proper function encapsulation:

```python
# 10000-line monolithic script
import sys
import pandas as pd

# Lines 1-500: Setup and config
config = load_config()
db = connect_database()

# Lines 501-2000: Data extraction (no function!)
cursor = db.execute("SELECT * FROM...")
data = cursor.fetchall()
df = pd.DataFrame(data)

# Lines 2001-5000: Complex transformations (no function!)
df['new_col'] = df['old_col'] * 2
df = df.merge(other_df, on='key')
# ... 3000 more lines ...

# Lines 5001-10000: Output and cleanup (no function!)
df.to_csv('output.csv')
db.close()
```

**Challenge**: How to represent this in a flow tree when there are no functions?

### Solution: LLM-Powered Logical Blocks

**Concept**: When a code section is large and unencapsulated, use LLM to identify logical operations and create virtual "function nodes" in the tree.

**Threshold Rule**:
```
IF a tree node contains > X sequential lines of code (default: 50)
AND less than Y% are function calls (default: 30%)
THEN use LLM to structure it into logical blocks
```

**Process**:

1. **Detect Unstructured Code Blocks**
   ```python
   def detect_unstructured_blocks(code: str, threshold: int = 50) -> List[CodeBlock]:
       """Find code sections that need LLM structuring."""
       # Identify sequential code without function calls
       # Return blocks that exceed threshold
   ```

2. **LLM Structuring Request**
   ```python
   def structure_code_block(code_block: str) -> List[LogicalOperation]:
       """Use LLM to identify logical operations in unstructured code."""

       prompt = f"""
       Analyze this Python code block and identify distinct logical operations.
       For each operation, provide:
       1. A short descriptive name (like a function name)
       2. Line range it covers
       3. Brief description of what it does

       Code:
       ```python
       {code_block}
       ```

       Return JSON:
       {{
         "operations": [
           {{
             "name": "load_configuration",
             "lines": "1-15",
             "description": "Load config from YAML and set up environment"
           }},
           {{
             "name": "extract_database_data",
             "lines": "16-45",
             "description": "Query database and convert to DataFrame"
           }}
         ]
       }}
       """

       response = call_claude_api(prompt)
       return parse_operations(response)
   ```

3. **Create Virtual Function Nodes**
   ```python
   @dataclass
   class VirtualFunctionNode:
       """Represents a logical operation identified by LLM."""
       name: str  # e.g., "extract_database_data"
       description: str
       line_start: int
       line_end: int
       is_virtual: bool = True  # Flag to show it's LLM-generated
       confidence: float  # LLM confidence in this structuring
   ```

4. **Render in Tree with Special Indicator**
   ```
   📄 legacy_script.py
     🤖 load_configuration (lines 1-15)     [LLM-identified]
     🤖 extract_database_data (lines 16-45) [LLM-identified]
     📦 process_data()                      [Actual function]
     🤖 output_results (lines 5001-5100)   [LLM-identified]
   ```

**Implementation**:

**File**: `src/analyzer/llm_code_structurer.py`

```python
class LLMCodeStructurer:
    """Use LLM to structure unencapsulated code blocks."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    def should_structure(self, code_block: str, threshold: int = 50) -> bool:
        """Check if code block needs LLM structuring."""
        lines = code_block.split('\n')
        if len(lines) < threshold:
            return False

        # Count function calls vs other code
        function_call_ratio = self._count_function_calls(code_block) / len(lines)
        return function_call_ratio < 0.3  # Less than 30% function calls

    def structure_block(self, code_block: str, file_context: str = "") -> List[VirtualFunctionNode]:
        """Use LLM to identify logical operations."""
        prompt = self._build_structuring_prompt(code_block, file_context)
        response = self._call_claude(prompt)
        return self._parse_operations(response)

    def _build_structuring_prompt(self, code: str, context: str) -> str:
        """Build prompt for LLM structuring."""
        return f"""
        You are analyzing a Python script to identify logical operations.

        Context: {context}

        Code to analyze:
        ```python
        {code}
        ```

        Identify distinct logical operations (5-10 operations max).
        For each operation:
        1. Name it like a function (snake_case)
        2. Specify exact line range
        3. Brief description

        Return valid JSON only:
        {{
          "operations": [
            {{"name": "...", "lines": "start-end", "description": "..."}}
          ]
        }}
        """
```

**Caching Strategy**:
- Cache LLM structuring results by file hash
- Only re-structure when file changes
- Store in `.flowdiff/llm_cache/`

---

## Phase 3: LLM-Powered Diff Explanations

### Vision

When viewing a diff, user can click "Explain" to get contextual explanation:

```
User clicks [?] next to changed code
↓
LLM analyzes:
1. The specific code change
2. Related changes in the same file
3. Related changes in other files (from full diff)
4. Commit message(s) that introduced this change
↓
Returns explanation:
"This change refactors the data loading logic to use pandas instead of
 raw SQL. It's part of a larger effort (see commit abc123) to improve
 performance by 50%. The change affects downstream functions
 process_data() and generate_report() which now receive DataFrames
 instead of lists."
```

### Implementation Options

#### Option A: On-Demand Explanation (Recommended for MVP)

**Pros**:
- No upfront cost
- Only explain what user actually views
- Can use most recent LLM models
- Faster initial diff load

**Cons**:
- Small delay when clicking "Explain"
- Might hit API rate limits if user clicks many

**Flow**:
```
User clicks "Explain" on diff
↓
Frontend sends: {function_name, before_code, after_code, diff_context}
↓
Backend calls LLM with full context
↓
Returns explanation in ~2-5 seconds
↓
Display in expandable panel
```

#### Option B: Pre-computed Explanation

**Pros**:
- Instant display when user clicks
- Can batch API calls (cheaper)
- Can show "AI insights" proactively

**Cons**:
- Slower initial diff load
- Might explain changes user never views
- Higher upfront API cost

**Flow**:
```
User loads diff
↓
Backend generates all explanations in background
↓
Cache in DiffResult
↓
User clicks "Explain" → instant display
```

### Recommended Approach: Hybrid

1. **Initial load**: Pre-compute explanations for top-level changes only (entry point functions)
2. **On-demand**: Explain nested changes when user clicks
3. **Cache**: Store explanations in session storage

### LLM Explanation Service

**File**: `src/analyzer/llm_explainer.py`

```python
class DiffExplainer:
    """Use LLM to explain code changes in context."""

    def explain_function_change(
        self,
        function_name: str,
        before_code: str,
        after_code: str,
        commit_messages: List[str],
        related_changes: List[FunctionDiff]
    ) -> DiffExplanation:
        """Generate explanation for a function change."""

        prompt = self._build_explanation_prompt(
            function_name,
            before_code,
            after_code,
            commit_messages,
            related_changes
        )

        response = self._call_claude(prompt)

        return DiffExplanation(
            summary=response['summary'],
            details=response['details'],
            impact=response['impact'],
            related_changes=response['related_changes']
        )

    def _build_explanation_prompt(
        self,
        function_name: str,
        before: str,
        after: str,
        commits: List[str],
        related: List[FunctionDiff]
    ) -> str:
        """Build comprehensive prompt for diff explanation."""

        # Build context from related changes
        context = self._build_change_context(related)

        return f"""
        You are a code review expert explaining a code change.

        Function: {function_name}

        Commit messages:
        {chr(10).join(commits)}

        Before:
        ```python
        {before}
        ```

        After:
        ```python
        {after}
        ```

        Related changes in this diff:
        {context}

        Provide:
        1. Summary: One sentence explaining what changed
        2. Details: 2-3 sentences on why/how
        3. Impact: Which other functions are affected
        4. Related changes: Link to other relevant changes

        Return JSON:
        {{
          "summary": "...",
          "details": "...",
          "impact": ["function1", "function2"],
          "related_changes": ["change1", "change2"]
        }}

        Be concise and technical. Focus on intent and impact.
        """

@dataclass
class DiffExplanation:
    """LLM-generated explanation of a code change."""
    summary: str  # One-liner
    details: str  # 2-3 sentences
    impact: List[str]  # Affected functions
    related_changes: List[str]  # Links to related changes
    confidence: float  # LLM confidence
    generated_at: datetime
```

### UI Integration

**Explanation Panel**:
```html
<div class="diff-explanation">
  <div class="explanation-header">
    <span class="ai-badge">🤖 AI Explanation</span>
    <button class="regenerate">↻ Regenerate</button>
  </div>

  <div class="explanation-summary">
    {{summary}}
  </div>

  <details class="explanation-details">
    <summary>Show details</summary>
    <p>{{details}}</p>
  </details>

  <div class="explanation-impact" *ngIf="impact.length > 0">
    <strong>Impact:</strong>
    <ul>
      <li *ngFor="let func of impact">
        <a href="#{{func}}">{{func}}</a>
      </li>
    </ul>
  </div>

  <div class="explanation-related" *ngIf="related.length > 0">
    <strong>Related changes:</strong>
    <ul>
      <li *ngFor="let change of related">
        <a href="#{{change}}">{{change}}</a>
      </li>
    </ul>
  </div>
</div>
```

**Button Placement**:
```
Before                 │  After
──────────────────────  ┼  ──────────────────────
1 def analyze():       │  1 def analyze():
2   old_code           │  2   new_code        [?] ← Explain button
3   return result      │  3   return enhanced
```

### Prompt Engineering Strategy

**Key Principles**:

1. **Provide full context**: Include commit messages, related changes, call tree position
2. **Request structured output**: Always JSON for easy parsing
3. **Limit scope**: Explain one change at a time, not entire diff
4. **Focus on intent**: Why changed, not just what changed
5. **Link related changes**: Help user see the big picture

**Example Prompts**:

```python
# For simple changes
SIMPLE_CHANGE_PROMPT = """
Explain this code change in one sentence:
- Before: {before}
- After: {after}
- Commit: {commit_msg}

Focus on the intent (why), not mechanics (what).
"""

# For complex refactoring
REFACTOR_PROMPT = """
This appears to be a refactoring. Analyze:

Before:
{before_code}

After:
{after_code}

Related changes:
{related_changes}

Explain:
1. What pattern/technique was used
2. Why this improves the code
3. What functions are affected

Be specific and technical.
"""

# For bug fixes
BUGFIX_PROMPT = """
This appears to be a bug fix.

Commit message: {commit_msg}

Code change:
- Before: {before}
- After: {after}

Explain:
1. What bug was fixed
2. How the fix works
3. Edge cases now handled

Be concise.
"""
```

---

## Phase 4: Advanced Features

### 4.1 Batch Explanation

Generate explanations for all changes in one API call:

```python
def explain_all_changes(diff_result: DiffResult) -> Dict[str, DiffExplanation]:
    """Generate explanations for all changes in batch."""

    # Build mega-prompt with all changes
    prompt = build_batch_explanation_prompt(diff_result)

    # Single API call (cheaper, faster)
    response = call_claude_extended_context(prompt)

    # Parse into individual explanations
    return parse_batch_explanations(response)
```

### 4.2 Smart Grouping

Group related changes for better explanation:

```
Instead of:
  🔴 utils.py::parse_data - modified
  🔴 utils.py::validate_data - modified
  🔴 utils.py::clean_data - modified

Show:
  📦 Data Processing Refactor (3 functions)
    └ Migrated to pandas DataFrame
    └ Affects: main.py::analyze_stock
    [Explain Refactor]
```

### 4.3 Diff Insights Panel

Proactive AI insights:

```
┌─────────────────────────────────────┐
│ 🤖 AI Insights                      │
├─────────────────────────────────────┤
│ • Performance improvement detected  │
│   3 functions now use caching       │
│                                     │
│ • Breaking change warning           │
│   analyze_stock() signature changed │
│                                     │
│ • Code quality improvement          │
│   2 functions extracted for reuse   │
└─────────────────────────────────────┘
```

---

## Configuration & Settings

### LLM Settings

**File**: `.flowdiff/config.yaml`

```yaml
llm:
  provider: "anthropic"  # or "openai"
  model: "claude-3-5-sonnet-20241022"
  api_key_env: "ANTHROPIC_API_KEY"

  # Code structuring
  structuring:
    enabled: true
    threshold_lines: 50
    min_function_call_ratio: 0.3
    cache_results: true

  # Diff explanations
  explanations:
    mode: "hybrid"  # "on-demand", "pre-computed", "hybrid"
    pre_compute_top_level: true
    batch_mode: true
    max_context_tokens: 100000

  # Rate limiting
  rate_limit:
    requests_per_minute: 50
    concurrent_requests: 5
```

### Cost Estimation

**Code Structuring** (one-time per file):
- Average legacy file: 2000 lines
- LLM tokens: ~10K input + 2K output
- Cost per file: ~$0.05 (Sonnet 3.5)
- Cache hit rate: 90% (only re-run on changes)

**Diff Explanations**:
- Average change: 50 lines before + 50 lines after + 500 tokens context
- Cost per explanation: ~$0.01
- Typical PR with 20 changes: ~$0.20

**Batch optimization**:
- Single API call for all changes: 60% cheaper
- Recommended for PRs > 10 changes

---

## Implementation Phases

### Phase 1: Core Diff (Week 1)
- ✅ Git backend
- ✅ Diff analysis
- ✅ Split-view UI
- ✅ Basic navigation

### Phase 2: LLM Structuring (Week 2)
- ⏳ Unstructured code detection
- ⏳ LLM API integration
- ⏳ Virtual function nodes
- ⏳ Caching system

### Phase 3: LLM Explanations (Week 3)
- ⏳ On-demand explanation
- ⏳ Hybrid pre-compute
- ⏳ Batch mode
- ⏳ UI integration

### Phase 4: Polish (Week 4)
- ⏳ Smart grouping
- ⏳ Insights panel
- ⏳ Export features
- ⏳ Performance optimization

---

## Testing Strategy

### Unit Tests
- Git operations (mocked)
- LLM API calls (mocked with fixtures)
- Code structuring logic
- Diff analysis

### Integration Tests
- Real git repo diffs
- LLM structuring on legacy code samples
- End-to-end diff workflow

### LLM Quality Tests
- Compare LLM structuring vs manual annotation (sample legacy files)
- Evaluate explanation quality (5-point scale)
- Monitor hallucination rate

---

## Success Metrics

### Functional
- ✅ Can display any git diff
- ✅ Explains 95%+ of changes accurately
- ✅ Structures legacy code with 80%+ accuracy

### Performance
- ⏱️ Initial diff load: < 3 seconds
- ⏱️ Explanation generation: < 5 seconds
- ⏱️ LLM structuring: < 10 seconds per file

### Quality
- 📊 User satisfaction: 4+ / 5
- 📊 Explanation accuracy: 90%+
- 📊 False positive rate (wrong structuring): < 10%

---

## Risks & Mitigations

### Risk 1: LLM API Costs
**Mitigation**:
- Aggressive caching
- Batch mode default
- User confirmation before expensive operations
- Local model option (Ollama) for high-volume users

### Risk 2: LLM Hallucination
**Mitigation**:
- Clear "AI-generated" badges
- "Regenerate" button for bad explanations
- Confidence scores
- User feedback mechanism

### Risk 3: Legacy Code Too Complex
**Mitigation**:
- Fallback to simple "Unstructured code block (lines X-Y)"
- Manual annotation option
- Community-contributed structure templates

### Risk 4: Performance with Large Diffs
**Mitigation**:
- Paginate large diffs
- Lazy-load explanations
- Background processing
- Progress indicators

---

## Future Enhancements

### Multi-Language Support
- Extend to JavaScript, Java, Go, Rust
- Language-specific structuring prompts

### Semantic Diff
- Detect refactoring (renamed functions, extracted methods)
- Show "equivalent" changes as unchanged

### Diff Recommendations
- LLM suggests improvements to the diff
- "This change could benefit from..."

### Team Features
- Share diff explanations
- Collaborative annotation
- Review comments integration

---

## Appendix: Example LLM Outputs

### Code Structuring Example

**Input** (legacy script):
```python
# 300 lines of unstructured code
import pandas as pd
conn = sqlite3.connect('db.sqlite')
cursor = conn.cursor()
cursor.execute("SELECT * FROM stocks WHERE symbol='AAPL'")
rows = cursor.fetchall()
df = pd.DataFrame(rows, columns=['date', 'price'])
df['returns'] = df['price'].pct_change()
df['ma_20'] = df['price'].rolling(20).mean()
# ... 280 more lines ...
```

**LLM Output**:
```json
{
  "operations": [
    {
      "name": "connect_database",
      "lines": "1-3",
      "description": "Establish SQLite connection"
    },
    {
      "name": "fetch_stock_data",
      "lines": "4-7",
      "description": "Query AAPL stock prices and convert to DataFrame"
    },
    {
      "name": "calculate_technical_indicators",
      "lines": "8-10",
      "description": "Compute returns and 20-day moving average"
    }
  ]
}
```

### Diff Explanation Example

**Input**:
```python
# Before
def analyze_stock(symbol):
    data = fetch_data(symbol)
    return calculate_metrics(data)

# After
def analyze_stock(symbol, use_cache=True):
    data = fetch_data(symbol, cache=use_cache)
    metrics = calculate_metrics(data)
    return {
        'symbol': symbol,
        'metrics': metrics,
        'timestamp': datetime.now()
    }
```

**LLM Output**:
```json
{
  "summary": "Added caching support and enhanced return value with metadata",
  "details": "This change adds an optional `use_cache` parameter (default True) to improve performance by caching API calls. The return value now includes the symbol and timestamp for better tracking. This is part of the performance optimization effort mentioned in commit abc123.",
  "impact": ["main", "generate_report"],
  "related_changes": ["fetch_data (modified)", "calculate_metrics (unchanged)"]
}
```
