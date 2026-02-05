# Entry Point Detection Analysis - StockAnalysis

## Current State (18 entry points found)

### Breakdown by Category:
1. **Test Files (13)** - ❌ Should be excluded
   - `archive.tests.test_foundation_metrics.run_all_tests`
   - `archive.tests.test_json_serialization_fix.test_clean_for_json`
   - `archive.tests.test_json_serialization_fix.test_before_and_after`
   - `archive.tests.test_csv_save_integration.test_csv_save_with_enums`
   - `tests.test_sqlite_manual.main`
   - `tests.test_report_integration.test_integration`
   - `tests.test_report_direct.test`
   - `tests.test_dummy_mode.main`
   - `tests.test_dummy_mode_fixes.main`
   - `testing.test_dummy_cache_workflow.main`
   - `debug.test_report_generation.test_report_generation`
   - `debug.backend.debug_analyze_stock`
   - `src.data.sec_data_extractor.test_extractor`

2. **Management/Admin Tools (2)** - ⚠️ Arguable (probably exclude)
   - `management.tools.enrich_gics_from_sp500.main`
   - `management.tools.update_ticker_database.main`

3. **Debug Scripts (2)** - ❌ Should be excluded
   - Already counted above in tests

4. **Examples/Backtesting (2)** - ⚠️ Arguable (probably exclude)
   - `src.backtesting.run_comprehensive_tests.main`
   - `src.backtesting.example_aapl.main`

5. **Production Entry Points (0)** - ❌ **MISSING!**
   - `server.py` (main Flask server) - **NOT DETECTED**
   - `src.analyzer.analyze_stock()` (core analysis function) - **NOT DETECTED**

## Root Causes

### Problem 1: Hard-coded Entry Point Detection Too Broad
**Location**: `src/analyzer/call_tree_builder.py` → `_identify_entry_points()`

The hard-coded rules identify functions as entry points if:
- Called in `if __name__ == '__main__'` blocks
- Have no callers (not called by anyone)
- Use CLI argument parsing

**Issue**: This catches ALL test files with main guards, ALL debug scripts, etc.

### Problem 2: LLM Prompt Encourages Including Tests
**Location**: `src/analyzer/llm_entry_point_filter.py` → `_build_filtering_prompt()`

Prompt says:
```
"Test functions (test_*) are entry points but can be filtered separately"
```

**Issue**: This tells the LLM that tests ARE entry points. The LLM follows instructions and includes them.

### Problem 3: Missing Path-Based Filtering
**Missing feature**: No pre-filtering based on file paths

Tests, debug scripts, examples should be filtered BEFORE LLM sees them.

Paths to exclude:
- `*/tests/*`, `*/test_*`
- `*/debug/*`
- `*/archive/*`
- `*/testing/*` (test utilities)
- `*/examples/*`, `*example_*.py`
- `*/tools/*`, `*/management/*` (admin scripts)

### Problem 4: Server.py Not Detected
**Why**: `server.py` only imports and doesn't have functions at module level

```python
from yfinance_extract_data import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
```

The `if __name__` block doesn't call a local function - it calls uvicorn directly.
This file needs special handling as a "script entry point" not a "function entry point".

## Proposed Solution

### Phase 1: Pre-filtering by Path (EASY, HIGH IMPACT)
Add path-based exclusions BEFORE entry point detection:

```python
def should_exclude_file(file_path: Path) -> bool:
    """Exclude test/debug/example files from entry point detection."""
    path_str = str(file_path).lower()

    # Exclude patterns
    exclude_patterns = [
        '/tests/',
        '/test_',
        '/debug/',
        '/archive/',
        '/testing/',
        '/examples/',
        '/example_',
        '/tools/',
        '/management/',
        '/scripts/',
        'conftest.py',
    ]

    return any(pattern in path_str for pattern in exclude_patterns)
```

**Expected Result**: 18 → ~2-3 entry points

### Phase 2: Improve LLM Prompt (EASY, MEDIUM IMPACT)
Update prompt to explicitly exclude tests/debug/examples:

```python
prompt = f"""...

An "entry point" from a user's perspective is a **production** function that:
- A user would directly execute in normal usage (CLI, server, main workflows)
- Represents a core feature or operation
- Is part of the production codebase

EXPLICITLY EXCLUDE:
- Test functions (pytest, unittest, test_*)
- Debug scripts (debug/, debug_*)
- Example/demo code (examples/, example_*)
- Admin/maintenance scripts (tools/, management/, scripts/)
- Internal utilities or helpers

FOCUS ONLY ON:
- Server entry points (Flask/FastAPI apps, uvicorn runners)
- CLI commands for end users
- Core workflow functions (analyze_stock, process_data, generate_report)

...
"""
```

**Expected Result**: Better LLM decisions even if pre-filtering misses something

### Phase 3: Script Entry Point Detection (MEDIUM, MEDIUM IMPACT)
Handle files like `server.py` that are entry points but don't have function calls:

```python
def detect_script_entry_points(file_path: Path) -> Optional[str]:
    """Detect if a file is a script entry point (e.g., server.py)."""
    with open(file_path) as f:
        content = f.read()

    # Check for main guard
    if 'if __name__ == "__main__"' not in content:
        return None

    # Check for server patterns
    server_patterns = [
        'uvicorn.run',
        'app.run(',
        'flask.run(',
        'fastapi',
    ]

    if any(pattern in content for pattern in server_patterns):
        return f"{file_path.stem}"  # e.g., "server"

    return None
```

### Phase 4: Heuristic Scoring (HARD, HIGH IMPACT)
Implement a scoring system for entry point quality:

```python
def score_entry_point(func: FunctionInfo, file_path: Path) -> float:
    """Score 0-100, higher = more likely to be user-facing entry point."""
    score = 50  # baseline

    # Positive signals
    if func.uses_cli_parsing: score += 20
    if func.called_in_main_guard: score += 15
    if file_path.stem in ['server', 'main', 'cli', 'app']: score += 20
    if func.name in ['main', 'run', 'start', 'analyze']: score += 10
    if len(func.called_by) == 0: score += 5  # no callers

    # Negative signals (path-based)
    if '/src/' not in str(file_path): score -= 20  # outside main source
    if func.name.startswith('_'): score -= 30  # private
    if len(func.calls) == 0: score -= 10  # doesn't do much

    return min(100, max(0, score))
```

Only pass high-scoring functions (>60) to LLM for final filtering.

## Expected Ideal State

After all improvements, StockAnalysis should show **2-4 entry points**:

1. ✅ **server** (server.py)
   - Main FastAPI server entry point
   - Reasoning: This is how users run the application

2. ✅ **src.analyzer.analyze_stock()**
   - Core stock analysis function
   - Reasoning: Main workflow function called by server

3. ⚠️ **Management Tools** (optional, user-configurable)
   - `management.tools.update_ticker_database.main`
   - `management.tools.enrich_gics_from_sp500.main`
   - Reasoning: Admin tools, could be excluded by default but useful for maintainers

## Implementation Priority

1. **CRITICAL (Phase 1)**: Path-based pre-filtering
   - **Impact**: Reduces 18 → ~3-5 entry points
   - **Effort**: 30 minutes
   - **Files**: `call_tree_builder.py` - add `should_exclude_file()` before entry point detection

2. **HIGH (Phase 2)**: Fix LLM prompt
   - **Impact**: Better LLM decisions
   - **Effort**: 15 minutes
   - **Files**: `llm_entry_point_filter.py` - update prompt

3. **MEDIUM (Phase 3)**: Script entry point detection
   - **Impact**: Detects server.py correctly
   - **Effort**: 1 hour
   - **Files**: `call_tree_builder.py` - add script detection logic

4. **NICE-TO-HAVE (Phase 4)**: Heuristic scoring
   - **Impact**: Smarter filtering before LLM
   - **Effort**: 2-3 hours
   - **Files**: `call_tree_builder.py` - add scoring system

## Quick Win Test
After Phase 1 + Phase 2, run on StockAnalysis:
```bash
python src/cli.py snapshot /Users/barlarom/PycharmProjects/Main/StockAnalysis
```

**Expected**: 2-5 entry points (server, analyzer, maybe management tools)
**Current**: 18 entry points (mostly tests/debug)

## Success Criteria
✅ Zero test files in entry points
✅ Zero debug scripts in entry points
✅ Server.py detected as entry point
✅ Core analysis function detected
✅ Management tools either excluded or clearly labeled
✅ Total entry points: 2-5 (not 18)
