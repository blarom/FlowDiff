# FlowDiff Agents

## Overview

This directory contains specialized agents for maintaining FlowDiff project health and quality.

**Current Agents:**
1. **FlowDiff Architect** (`flowdiff_architect.md`) - Project health guardian

## Purpose

Agents are designed to:
- Catch architectural issues before they become technical debt
- Enforce coding conventions and best practices
- Maintain clean, maintainable codebase
- Provide automated health checks

## Available Agents

### 1. FlowDiff Architect (Project Health Guardian)

**File:** `flowdiff_architect.md`

**Role:** Maintain clean project structure, enforce conventions, prevent technical debt

**When to Use:**
- Weekly/monthly project health checks
- Before starting major features (ensure clean baseline)
- After bulk changes or refactoring
- When investigating suspected technical debt

**What It Checks:**
- Project structure compliance
- Code quality (type hints, docstrings, magic numbers)
- Architectural integrity (layer violations, coupling)
- Security (hardcoded credentials, permissions)
- Configuration management
- Error handling patterns

**Output:** Comprehensive health report with prioritized actions

**Usage:**
```
/flowdiff_architect              # Full scan
/flowdiff_architect quality      # Quality scan only
/flowdiff_architect security     # Security scan only
/flowdiff_architect architecture # Architecture check only
/flowdiff_architect fix          # Auto-fix mode
```

## Integration with Development Workflow

### Typical Usage Pattern

```
Weekly Cycle:
1. Run FlowDiff Architect → Identify issues
2. Prioritize (Critical → Warning → Info)
3. Fix issues systematically
4. Verify with re-scan

Before New Features:
1. Run architect to ensure clean baseline
2. Fix critical issues
3. Proceed with feature development

After Changes:
1. Run architect to check for regressions
2. Verify no new technical debt
3. Clean up before committing
```

### Success Metrics

| Metric | Target |
|--------|--------|
| Structure Compliance | 100% |
| Security Score | 100% (0 secrets) |
| Type Hint Coverage | 90%+ |
| Code Duplication | <5% |
| Magic Numbers | 0 (in constants.py) |
| Error Handling | 95%+ |

## Agent Design Philosophy

Agents are **inspectors, not implementers**:
- ✅ Identify issues and provide fix instructions
- ✅ Auto-fix simple, safe changes (with confirmation)
- ❌ Don't make complex changes automatically
- ❌ Don't write feature code

## Future Agents (Planned)

As FlowDiff grows, consider adding:
- **Refactoring Agent** - Suggest architectural improvements
- **Performance Agent** - Identify bottlenecks and optimization opportunities
- **Documentation Agent** - Ensure code and API docs are complete

## Maintenance

- Review agent definitions quarterly
- Update as project conventions evolve
- Add new checks as patterns emerge

---

**The FlowDiff Architect ensures sustained project health and prevents technical debt accumulation.**
