"""
LLM-based entry point filtering.

Uses configurable LLM providers (API or CLI) to determine which candidate
entry points should actually be shown as top-level from a user's perspective.
"""

import json
from typing import List, Set, Dict, Optional
from dataclasses import dataclass

from .llm_providers import LLMProvider, auto_detect_provider


@dataclass
class EntryPointCandidate:
    """A function that might be an entry point."""
    name: str
    qualified_name: str
    file_name: str
    file_path: str
    parameters: List[str]

    # Context for LLM decision
    uses_cli_parsing: bool
    called_in_main_guard: bool
    is_test: bool
    is_private: bool
    called_by: List[str]  # Functions that call this
    calls: List[str]  # Functions this calls


class LLMEntryPointFilter:
    """Use LLM to filter entry points from user's perspective."""

    def __init__(self, provider: Optional[LLMProvider] = None):
        """
        Initialize LLM entry point filter.

        Args:
            provider: LLM provider (if None, auto-detects available provider)
        """
        if provider is None:
            provider = auto_detect_provider()

        self.provider = provider

    def filter_entry_points(
        self,
        candidates: List[EntryPointCandidate],
        project_name: str
    ) -> Set[str]:
        """
        Use LLM to determine which candidates should be top-level entry points.

        Args:
            candidates: List of potential entry points
            project_name: Name of the project for context

        Returns:
            Set of qualified names that should be shown as top-level
        """
        if not candidates:
            return set()

        prompt = self._build_filtering_prompt(candidates, project_name)

        try:
            response_text = self.provider.complete(prompt, max_tokens=4000)
            result = self._parse_response(response_text)
            return set(result.get('entry_points', []))
        except Exception as e:
            print(f"Warning: LLM filtering failed: {e}")
            print(f"Provider: {self.provider.get_name()}")
            # Return all candidates if LLM fails (fallback to hard-coded rules)
            return {c.qualified_name for c in candidates}

    def _build_filtering_prompt(
        self,
        candidates: List[EntryPointCandidate],
        project_name: str
    ) -> str:
        """Build prompt for LLM to filter entry points."""

        # Build candidate descriptions
        candidate_descriptions = []
        for c in candidates:
            desc = {
                'qualified_name': c.qualified_name,
                'name': c.name,
                'file': c.file_name,
                'parameters': c.parameters,
                'uses_cli_parsing': c.uses_cli_parsing,
                'called_in_main_guard': c.called_in_main_guard,
                'is_test': c.is_test,
                'is_private': c.is_private,
                'called_by_count': len(c.called_by),
                'calls_count': len(c.calls)
            }
            candidate_descriptions.append(desc)

        return f"""You are analyzing a Python project called "{project_name}" to determine which functions should be shown as top-level entry points to a user.

An "entry point" from a user's perspective is a function that:
- A user would directly execute (web servers, CLI commands, tests, main workflows)
- Represents a distinct workflow or operation
- Makes sense as a standalone action

**HIGH PRIORITY (always include these):**
- Web server entry points (FastAPI apps, Flask apps, uvicorn.run calls)
- Core workflow functions (analyze_stock, process_data, generate_report)
- Functions called from __main__ in production scripts

**MEDIUM PRIORITY (include unless clearly utilities):**
- Test functions (test_*, pytest patterns) - these are entry points for testing
- CLI tools and utilities
- Example/demo code (examples/, example_*)

**LOW PRIORITY (exclude these):**
- Debug scripts that are clearly temporary (debug/, debug_*)
- Archive or old code (archive/, archived/)
- Admin/maintenance one-off scripts (update_database, migrate_*)
- Internal utilities/helpers that users never call directly

NOTE: Tests ARE valid entry points - users run them. Don't exclude all tests.
NOTE: The UI has a "Hide Tests" button, so including tests is fine.

Here are the candidate functions:

{json.dumps(candidate_descriptions, indent=2)}

**INSTRUCTIONS:**
1. Include production entry points, tests, and examples
2. Only exclude clear utilities, debug scripts, and internal helpers
3. When in doubt about a test or example, INCLUDE it
4. Aim for 5-15 entry points (not just 2-3)

Analyze each candidate and determine which should be shown as top-level entry points.

Return ONLY valid JSON with this structure:
{{
  "entry_points": ["qualified.name.here", "another.qualified.name"],
  "reasoning": {{
    "qualified.name.here": "Brief reason why included/excluded",
    "another.qualified.name": "Brief reason"
  }}
}}"""

    def _parse_response(self, response_text: str) -> dict:
        """Parse LLM response."""
        try:
            # Extract JSON from response (may have markdown code blocks)
            if '```json' in response_text:
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()
            elif '```' in response_text:
                start = response_text.find('```') + 3
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()

            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse LLM response: {e}")
            print(f"Response: {response_text}")
            return {'entry_points': [], 'reasoning': {}}
