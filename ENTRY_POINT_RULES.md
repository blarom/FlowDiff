# FlowDiff: Entry Point Detection - Final Rules

## Summary

Entry point detection uses a **hybrid approach**: conservative hard-coded rules first, then **LLM-based filtering** to determine which functions are truly top-level from a user's perspective.

---

## Two-Phase Detection System

### Phase 1: Hard-Coded Rules (Conservative)

The system first applies conservative hard-coded rules to identify potential entry points. These rules cast a wider net to avoid missing important functions.

### Phase 2: LLM Filtering (User Perspective)

If LLM filtering is enabled (default), **Claude analyzes all candidates** and determines which functions a user would actually want to see as top-level, considering:
- Intent and purpose of the function
- Naming conventions
- Whether it's truly standalone or a utility
- Project context and patterns

This solves the fundamental limitation of hard-coded rules: **understanding user intent and project-specific context**.

---

## Phase 1: Hard-Coded Rules

A function is marked as a **candidate entry point** if it meets one of these criteria:

### 1. Explicitly Called in `__main__` Block ✅
```python
if __name__ == "__main__":
    analyze_stock()  # ← analyze_stock is an entry point
```

### 2. CLI Script (Uses Argument Parsing) ✅
```python
def analyze_stock():
    parser = argparse.ArgumentParser()  # ← Entry point
    # OR
    symbol = sys.argv[1]  # ← Entry point
```

### 3. CLI Framework Decorator ✅
```python
@click.command()  # ← Entry point
def analyze_stock():
    pass

@typer.command()  # ← Entry point
def process_data():
    pass
```

### 4. Test Function ✅
```python
def test_analyze_stock():  # ← Entry point
    assert analyze_stock('AAPL') is not None
```

### 5. Exact Name Match (Limited Set) ✅
```python
def main():  # ← Entry point (exact name)
    pass

def run():  # ← Entry point (exact name)
    pass

# Only these EXACT names qualify:
# main, run, execute, start, init, initialize
```

---

## What is NEVER an Entry Point?

### 1. Private/Internal Functions ❌
```python
def _safe_evaluate():  # ❌ Starts with _
    pass

def __init__():  # ❌ Dunder method
    pass
```

### 2. Class Methods ❌
```python
class DataProcessor:
    def process(self):  # ❌ Method inside class
        pass
```

### 3. Uncalled Utility Functions ❌
```python
def check_aapl_peg():  # ❌ Not called by anyone, not CLI script
    pass

def detect_conglomerate():  # ❌ Not called by anyone, not CLI script
    pass

def calculate_metrics():  # ❌ Orphaned utility
    pass
```

**Why they're excluded:**
- If they're real entry points, they should either:
  - Use argparse/sys.argv (CLI scripts), OR
  - Be called in `__main__` block, OR
  - Be named exactly `main`/`run`/etc.
- If they don't meet these criteria, they're utility functions that should be called by something else
- Better to exclude them than clutter the tree with noise

---

## Examples

### ✅ WILL Show as Entry Point

```python
# Example 1: Called in __main__
def analyze_stock(symbol):
    # ... logic ...

if __name__ == "__main__":
    analyze_stock('AAPL')  # ← Makes analyze_stock an entry point

# Example 2: Uses argparse
def analyze_stock():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol')
    args = parser.parse_args()
    # ... logic ...

# Example 3: CLI decorator
@click.command()
@click.option('--symbol')
def analyze_stock(symbol):
    # ... logic ...

# Example 4: Test function
def test_analyze_stock():
    assert analyze_stock('AAPL') is not None

# Example 5: Exact name
def main():
    analyze_stock('AAPL')
```

### ❌ Will NOT Show as Entry Point

```python
# Example 1: Uncalled utility
def check_aapl_peg():  # ❌ Orphaned, no argparse, not in __main__
    # Should be called by analyze_stock() or similar
    pass

# Example 2: Private function
def _safe_evaluate(expr):  # ❌ Starts with _
    pass

# Example 3: Class method
class StockAnalyzer:
    def analyze(self):  # ❌ Method, not entry point
        pass

# Example 4: Uncalled calculation
def calculate_metrics(data):  # ❌ Utility, should be called by something
    pass
```

---

## Decision Tree

```
Is function private (_name or __name__)?
  YES → ❌ NOT entry point
  NO  → Continue

Is function a class method?
  YES → ❌ NOT entry point
  NO  → Continue

Is function called in __main__ block?
  YES → ✅ ENTRY POINT
  NO  → Continue

Does function use argparse/sys.argv/CLI decorators?
  YES → ✅ ENTRY POINT
  NO  → Continue

Is function name test_*?
  YES → ✅ ENTRY POINT
  NO  → Continue

Is function name exactly main/run/execute/start/init/initialize?
  YES → ✅ ENTRY POINT
  NO  → Continue

Is function called by any other function?
  YES → ❌ NOT entry point (it's called by something, so not top-level)
  NO  → Continue

Function is orphaned (not called by anyone).
  Is it test_*? YES → ✅ ENTRY POINT
  Is it main/run/etc? YES → ✅ ENTRY POINT
  Otherwise → ❌ NOT entry point (orphaned utility, should be called by something)
```

---

## Why This Approach?

### Philosophy: **Better to Miss Than to Noise**

1. **Clean Tree** > **Complete Tree**
   - Missing an edge-case entry point is better than showing 50 utility functions
   - User can always search for specific functions

2. **Intent Matters**
   - CLI scripts (argparse) show clear intent to be run from command line
   - Functions in `__main__` show clear intent to be entry points
   - Orphaned `check_aapl_peg()` doesn't show any such intent

3. **Practical Reality**
   - In well-structured code, utilities are called by something
   - If `check_aapl_peg()` isn't called, it's either:
     - Dead code (should be removed)
     - Incomplete integration (should be called by analyze_stock)
     - Testing code (should be in test_*)

---

## Troubleshooting

### "My entry point isn't showing!"

**Check:**
1. Does it use argparse, sys.argv, or CLI decorators?
2. Is it called in `if __name__ == "__main__":`?
3. Is it named exactly `main`, `run`, `execute`, `start`, `init`, or `initialize`?
4. Does it start with `test_`?

If none of these, it won't show as entry point. **Solutions:**
- Add argparse to make it a CLI script
- Call it in `__main__` block
- Rename it to `main()` or `run()`
- If it's a test, name it `test_*`

### "Why is check_aapl_peg not an entry point?"

Because:
- It doesn't use argparse/sys.argv (not a CLI script)
- It's not called in `__main__` block
- It's not named `main`/`run`/etc.
- It doesn't start with `test_`

**If it's really an entry point**, add one of these:
```python
# Option 1: Make it a CLI script
def check_aapl_peg():
    parser = argparse.ArgumentParser()
    # ...

# Option 2: Call it in __main__
if __name__ == "__main__":
    check_aapl_peg()

# Option 3: Rename it
def main():  # was check_aapl_peg
    # ...
```

---

## Configuration

Entry point detection is **not configurable** - this is intentional.

The rules are designed to match real-world conventions:
- CLI scripts use argparse
- Entry points are called in `__main__`
- Main entry points are named `main()`

If your code doesn't follow these conventions, the solution is to update the code, not the tool.

---

## LLM Filtering (Phase 2)

### How It Works

After Phase 1 identifies candidate entry points, Claude analyzes each candidate considering:

**Context Provided to LLM:**
- Function name and file location
- Whether it uses CLI parsing (argparse, sys.argv)
- Whether it's called in `__main__` block
- Whether it's a test function
- How many functions call it
- How many functions it calls
- Project name for context

**LLM Decision Criteria:**
- Is this a function a user would directly execute?
- Does it represent a distinct workflow or operation?
- Does it make sense as a standalone action?
- Or is it an internal utility that should be called by something else?

### Usage

**Enable LLM filtering (default):**
```bash
flowdiff snapshot /path/to/project
```

**Disable LLM filtering (hard-coded rules only):**
```bash
flowdiff snapshot /path/to/project --no-llm
```

### Requirements

LLM filtering requires the `ANTHROPIC_API_KEY` environment variable:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
flowdiff snapshot /path/to/project
```

If the API key is not set, FlowDiff automatically falls back to hard-coded rules with a warning.

### Why LLM Filtering?

Hard-coded rules have fundamental limitations:

1. **Can't understand project context**
   - Is `check_aapl_peg` a standalone script or utility?
   - Hard-coded rules can't tell - LLM can infer from name and context

2. **Can't handle shell scripts**
   - `analyze_stock.sh` isn't Python - hard-coded rules miss it
   - LLM can understand it's a top-level entry point from project structure

3. **Can't infer user intent**
   - `detect_conglomerate` might be top-level in one project, utility in another
   - LLM considers naming conventions and usage patterns

4. **Project-specific conventions**
   - Different projects have different entry point patterns
   - LLM adapts to each project's conventions

### Cost

LLM filtering makes a single API call per analysis with:
- ~2-5K tokens input (candidate list)
- ~500-1K tokens output (filtered list + reasoning)
- Cost: **~$0.01-0.02 per analysis** (Sonnet 3.5)

This is a one-time cost per run, cached for the session.

### Privacy

**Data sent to Claude:**
- Function names and file names
- Function signatures (parameters)
- Context flags (uses CLI parsing, etc.)
- Project name

**Data NOT sent:**
- Function bodies (no code)
- File contents
- Comments or docstrings

---

## Examples of LLM Filtering
