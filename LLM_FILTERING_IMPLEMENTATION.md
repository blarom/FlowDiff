# LLM-Based Entry Point Filtering - Implementation Summary

## What Was Implemented

FlowDiff now uses **Claude** to intelligently filter entry points from a user's perspective, solving the limitations of hard-coded rules.

### Files Created/Modified

#### 1. **NEW**: `src/analyzer/llm_entry_point_filter.py`
**Purpose**: LLM-based entry point filtering using Claude API

**Key Components**:
- `EntryPointCandidate`: Dataclass with function metadata and context
- `LLMEntryPointFilter`: Main class that calls Claude API
  - `filter_entry_points()`: Sends candidates to Claude, gets filtered list
  - `_build_filtering_prompt()`: Constructs prompt with candidate context
  - `_parse_response()`: Parses JSON response from Claude

**Context Provided to Claude**:
- Function name, file name, qualified name
- Parameters
- Whether it uses CLI parsing (argparse, sys.argv, decorators)
- Whether it's called in `__main__` block
- Whether it's a test function
- Whether it's private/internal
- How many functions call it
- How many functions it calls
- Project name

**Claude's Task**:
> "Determine which functions should be shown as top-level entry points from a user's perspective"

**Output**: JSON with filtered list and reasoning

#### 2. **MODIFIED**: `src/analyzer/call_tree_builder.py`
**Changes**:
1. Added import for `LLMEntryPointFilter` and `EntryPointCandidate`
2. Added `use_llm_filtering` parameter to `__init__()` (default: `True`)
3. Added `_apply_llm_filtering()` method:
   - Builds candidate list from functions marked as entry points
   - Calls Claude API to filter
   - Updates `is_entry_point` flags based on Claude's decision
   - Handles errors gracefully (falls back to hard-coded rules)
4. Updated `_identify_entry_points()` to call LLM filtering if enabled

**Error Handling**:
- Missing API key: Falls back to hard-coded rules with warning
- LLM API errors: Falls back to hard-coded rules with warning
- Import errors: Falls back to hard-coded rules with warning

#### 3. **MODIFIED**: `src/cli.py`
**Changes**:
1. Added `--no-llm` flag to disable LLM filtering
2. Added API key check before enabling LLM filtering
3. Added user-friendly warnings when API key is missing
4. Passes `use_llm_filtering` parameter to `CallTreeBuilder`

**Example Usage**:
```bash
# LLM filtering enabled (default)
flowdiff snapshot /path/to/project

# LLM filtering disabled
flowdiff snapshot /path/to/project --no-llm
```

#### 4. **MODIFIED**: `requirements.txt`
**Changes**:
- Added `anthropic>=0.39.0` dependency

#### 5. **UPDATED**: `ENTRY_POINT_RULES.md`
**Changes**:
- Updated to explain two-phase detection system
- Added section on LLM filtering: how it works, usage, requirements, cost, privacy
- Explained why LLM filtering solves hard-coded rule limitations

---

## How It Works

### Two-Phase Detection

**Phase 1: Hard-Coded Rules (Conservative)**
- Identifies potential entry points using conservative rules
- Marks functions as candidates if they:
  - Use CLI parsing (argparse, sys.argv, decorators)
  - Are called in `__main__` block
  - Are test functions (`test_*`)
  - Are named exactly `main`, `run`, `execute`, etc.
  - Are not private/internal (`_name`)
  - Are not class methods

**Phase 2: LLM Filtering (User Perspective)**
- If enabled, sends all candidates to Claude
- Claude analyzes each candidate considering:
  - Function name and context
  - Whether it's truly standalone or a utility
  - Project-specific conventions
  - User intent
- Returns filtered list of functions that should be top-level
- Updates `is_entry_point` flags based on Claude's decision

---

## Expected Behavior

### Before (Hard-Coded Rules Only)

User reported seeing:
```
✓ enrich_gics_from_sp500::main
✓ update_ticker_database::main
✓ backend::debug_analyze_stock
✗ aapl_peg::check_aapl_peg          ← Should NOT be top-level (utility)
✓ example_aapl::main
✗ conglomerate_detection::detect_conglomerate  ← Should NOT be top-level (utility)
✗ analyze_stock.sh                  ← MISSING (shell script)
```

### After (With LLM Filtering)

Expected to see:
```
✓ analyze_stock.sh                  ← Shell script (LLM recognizes as top-level)
✓ enrich_gics_from_sp500::main
✓ update_ticker_database::main
✓ backend::debug_analyze_stock
✓ example_aapl::main
```

Excluded (correctly):
```
✗ aapl_peg::check_aapl_peg          ← LLM identifies as utility
✗ conglomerate_detection::detect_conglomerate  ← LLM identifies as utility
```

---

## Testing

### Prerequisites

1. **Install dependencies**:
   ```bash
   cd /Users/barlarom/PycharmProjects/Main/FlowDiff
   pip install -r requirements.txt
   ```

2. **Set API key**:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

### Test 1: Verify LLM Filtering Works

```bash
cd /Users/barlarom/PycharmProjects/Main
flowdiff snapshot StockAnalysis/
```

**Expected Output**:
```
FlowDiff - Function Call Tree Analyzer
Project: StockAnalysis

🔍 Discovering Python files...
   Found 70 Python files
📝 Analyzing functions and building call trees...
🤖 Using Claude to filter 15 entry point candidates...
✓ LLM selected 8 entry points

   Found 250 functions, 8 entry points
🌐 Preparing visualization...

✓ Ready to visualize!

Server running at http://localhost:8080
```

**Then verify in browser**:
- `check_aapl_peg` should NOT appear
- `detect_conglomerate` should NOT appear
- `analyze_stock.sh` should appear (if detectable)

### Test 2: Without API Key

```bash
unset ANTHROPIC_API_KEY
flowdiff snapshot StockAnalysis/
```

**Expected Output**:
```
⚠ ANTHROPIC_API_KEY not set - using hard-coded rules only
   Set ANTHROPIC_API_KEY to enable LLM-based entry point filtering
```

Should fall back to hard-coded rules (may show `check_aapl_peg`, etc.)

### Test 3: Disable LLM Filtering

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
flowdiff snapshot StockAnalysis/ --no-llm
```

Should use only hard-coded rules (no LLM call)

---

## Cost

**Per Analysis**:
- Input: ~2-5K tokens (candidate list + context)
- Output: ~500-1K tokens (filtered list + reasoning)
- Model: Claude 3.5 Sonnet
- **Cost: ~$0.01-0.02 per analysis**

**Caching**:
- Results are cached per session (not across runs)
- Future: Could add persistent caching by project hash

---

## Known Limitations

### 1. Shell Scripts Not Detected

**Issue**: `analyze_stock.sh` won't be detected by Phase 1 (Python-only parser)

**Workaround**: LLM can't filter what it doesn't see

**Future Fix**: Add shell script detection to Phase 1
- Parse shell scripts for shebang
- Include shell scripts in candidate list
- LLM can then determine if they're entry points

### 2. False Positives if API Key Missing

**Issue**: If API key is missing, falls back to hard-coded rules which may show utilities

**Solution**: User will see warning to set API key

### 3. LLM May Disagree with User

**Issue**: Claude might make different decisions than user expects

**Solution**:
- User can disable LLM filtering with `--no-llm`
- User can refactor code to be more explicit (add `__main__` guards)
- Future: Allow user feedback to improve prompts

---

## Next Steps

### Immediate
1. **Test on StockAnalysis** to verify:
   - `check_aapl_peg` is filtered out
   - `detect_conglomerate` is filtered out
   - Other entry points remain

2. **If shell scripts missing**: Add shell script detection to Phase 1

### Future Enhancements
1. **Persistent Caching**: Cache LLM results by project hash
2. **User Feedback**: Allow user to mark functions as entry/not entry, improve prompts
3. **Confidence Scores**: Show LLM confidence for each decision
4. **Multi-Language Support**: Extend to JavaScript, Java, etc.
5. **Reasoning Display**: Show LLM's reasoning in UI (tooltip or panel)

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
**Fix**: Export your API key before running FlowDiff:
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

### "Warning: LLM filtering failed"
**Cause**: API error (rate limit, network issue, invalid key)
**Fix**: Check API key, try again, or use `--no-llm`

### "LLM filtering requested but llm_entry_point_filter not available"
**Cause**: Import error (missing `anthropic` package)
**Fix**: `pip install -r requirements.txt`

### Still seeing unwanted functions
**Options**:
1. Check if LLM filtering is actually running (should see "🤖 Using Claude..." message)
2. Try running again (LLM decisions may vary slightly)
3. Use `--no-llm` to see hard-coded rules only for comparison
4. Check `ANTHROPIC_API_KEY` is set correctly

---

## Summary

FlowDiff now uses Claude to intelligently filter entry points, solving the key limitation of hard-coded rules: **understanding user intent and project context**.

**Key Benefits**:
- ✅ Excludes utility functions like `check_aapl_peg`
- ✅ Includes true entry points even if unconventional
- ✅ Adapts to project-specific patterns
- ✅ Graceful fallback if API unavailable
- ✅ Low cost (~$0.01 per analysis)
- ✅ Privacy-friendly (no code sent, only metadata)

**User Experience**:
- Default: LLM filtering enabled (best results)
- Fallback: Hard-coded rules if API key missing
- Option: `--no-llm` to disable LLM filtering
- Clear warnings and helpful error messages
