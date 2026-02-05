"""LLM integration interfaces (Phase 2)."""
from abc import ABC, abstractmethod

class DiffExplainer(ABC):
    """Interface for explaining code changes using LLM."""

    @abstractmethod
    def explain_change(self, before_code: str, after_code: str) -> str:
        """Generate natural language explanation of code changes.

        Args:
            before_code: Code before the change
            after_code: Code after the change

        Returns:
            Natural language explanation of the changes

        Raises:
            NotImplementedError: This feature is planned for Phase 2
        """
        raise NotImplementedError("LLM explanations coming in Phase 2")

    @abstractmethod
    def summarize_diff(self, diff_context: dict) -> str:
        """Generate high-level summary of all changes.

        Args:
            diff_context: Dictionary containing diff metadata and changes

        Returns:
            High-level summary of the changes

        Raises:
            NotImplementedError: This feature is planned for Phase 2
        """
        raise NotImplementedError("LLM summarization coming in Phase 2")
