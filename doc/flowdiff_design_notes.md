# LLM‑Aware Architecture Visualization

> **Purpose:** Capture the reasoning, constraints, and design principles behind a tool that helps a senior engineer maintain architectural control when using LLMs (e.g. Claude) to evolve a non‑trivial codebase.

---

## 1. Core Motivation

- LLMs are strong at **local code changes** and weak at **global architectural reasoning**.
- When an LLM touches many files, the result becomes **opaque**, even to experienced engineers.
- Text diffs scale poorly for:
  - Multi‑file changes
  - Flow changes
  - New dependencies
- This opacity leads to iteration loops:
  - accept → break → patch → repeat

**Goal:** Restore human architectural control by externalizing the mental model the engineer normally builds internally.

---

## 2. Non‑Goals (Explicit)

This tool is **not** meant to:
- Replace reading code
- Replace git diffs
- Judge correctness automatically
- Make LLMs “smarter”
- Visualize runtime behavior perfectly

It is a **control surface**, not an automation engine.

---

## 3. Key Insight

> Visualization must not compete with code reading.
> It must win only in moments where text breaks down.

Experienced engineers:
- Read code faster than GUIs
- Build mental models quickly

Therefore, visualization must deliver **high‑value signal** that would take **minutes** to infer from text.

---

## 4. When Visualization *Is* Worth It

Visualization adds value primarily in these cases:

### 4.1 Large, Multi‑File LLM Changes
- Many files touched
- New helpers/modules introduced
- Flow reconstructed mentally across files

### 4.2 Unintended Architectural Changes
Humans miss these in text diffs:
- New dependencies
- Layer violations
- Responsibility creep

A new arrow in a graph is immediately visible.

### 4.3 Iteration Reduction
- Catch architectural mistakes **before running the app**
- Reduce LLM feedback loops
- Reduce token waste

---

## 5. When Visualization Is *Not* Worth It

The tool should step aside when:
- Changes are local
- Few files touched
- No new dependencies
- No flow changes detected

**Rule:** If nothing interesting is detected, the tool should recommend skipping visualization.

---

## 6. Correct Framing of “What the Diagram Shows”

Not:
> “What the app did / does”

But:
> **Structural control and data flow as implied by the code**, before and after

This avoids:
- Overclaiming runtime semantics
- False confidence

---

## 7. Diagram Semantics (What Is Visualized)

### 7.1 Nodes
- Modules / folders
- (Later) classes or major functions

### 7.2 Edges
- Imports
- Direct function calls (best‑effort)
- Data‑layer access paths

### 7.3 Visual Encoding
- Direction = control/data flow
- Color = added / removed / modified
- Thickness = coupling intensity or call frequency

---

## 8. Change‑First Visualization Principle

Default view should emphasize:
- Only **changed nodes and edges**
- Context faded

The full graph exists, but is not the default.

**One glance should reveal something non‑obvious.**

---

## 9. Granularity Rules

- Start coarse (≈10–30 blocks max)
- Drill down only on demand
- Function‑level detail only via click

If the graph does not fit on one screen, it is too dense.

---

## 10. Bootstrap Strategy: From Code to Intent

### 10.1 Automation Can Do
- Discover existence
- Discover connections
- Discover frequency

### 10.2 Automation Cannot Do Reliably
- Discover intent
- Discover importance
- Discover architectural boundaries

### 10.3 Correct Pipeline

```
Code
  → Noisy structural graph (AST / imports / calls)
  → Automatic collapsing (folders, leaves, stdlib)
  → Human pruning & grouping
  → Intent graph (stable, meaningful)
```

---

## 11. Intent Layer (Critical Design Choice)

Intent must be:
- Explicit
- Editable
- Version‑controlled
- Separate from code

Example:
```yaml
blocks:
  backend:
    includes:
      - api/*
      - services/*
    label: Backend Core
    pinned: true
```

The intent layer overrides visualization, not code.

---

## 12. Interaction Model

### 12.1 Review Flow
1. LLM completes change
2. Visualizer shows:
   - File structure diff
   - Structural graph diff
3. Engineer spots suspicious change (or not)
4. Either:
   - Reject / constrain change
   - Skip visualization and read code

### 12.2 Drill‑Down
- Click block → functions
- Click edge → call sites
- Click function → classic diff

---

## 13. LLM Feedback Integration

Avoid free‑form feedback.

Instead, generate **structured architectural feedback**:
```json
{
  "rejected_changes": [
    {
      "type": "new_dependency",
      "from": "ui",
      "to": "db",
      "reason": "violates layering"
    }
  ]
}
```

LLM explanations are **supplementary**, not authoritative.

---

## 14. Trust and Stability Principles

- Visualization must be stable across refactors
- Small code changes should not reshuffle the diagram
- Fewer blocks > more accuracy

Early trust is more important than completeness.

---

## 15. Roadmap (Personal, Practical)

### Phase 1 – Structural Snapshot
- Python AST parsing
- Module/import graph
- Static, read‑only diagram

**Success:** Diagram matches the engineer’s mental model.

---

### Phase 2 – Change Overlay
- Before/after graph diff
- Highlight added/removed edges

**Success:** Architectural changes are immediately visible.

---

### Phase 3 – Review Loop
- Click‑through diffs
- Structured feedback export

**Success:** Catch issues before execution.

---

### Phase 4 – Optional Signals
- Coupling increase
- Responsibility growth

Signals only, no judgments.

---

## 16. Hard Constraints to Enforce

- Visualization must pay for itself in <60 seconds
- If nothing interesting is detected, say so
- Never attempt to replace code reading

---

## 17. Positioning (Mental Model)

This tool is:
- A **pre‑review filter**
- A **change‑aware architectural lens**
- A way to externalize and protect senior‑level judgment

It is not a diagram generator for documentation.

---

## 18. Guiding Metric

> *Does this visualization reveal something important that would take ≥5–10 minutes to infer from code?*

If not, it should not exist.

