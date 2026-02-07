"""Language registry for FlowDiff multi-language support."""

from pathlib import Path
from typing import Dict, List, Optional
import logging

from .core.language_analyzer import LanguageAnalyzer

logger = logging.getLogger(__name__)


class LanguageRegistry:
    """Registry of language analyzers.

    Manages available language analyzers and dispatches files
    to appropriate analyzer based on file extension.
    """

    def __init__(self):
        self.analyzers: List[LanguageAnalyzer] = []
        self._analyzer_by_lang: Dict[str, LanguageAnalyzer] = {}

    def register(self, analyzer: LanguageAnalyzer) -> None:
        """Register a language analyzer.

        Args:
            analyzer: LanguageAnalyzer implementation
        """
        self.analyzers.append(analyzer)
        lang = analyzer.get_language_name()
        self._analyzer_by_lang[lang] = analyzer
        logger.debug(f"Registered analyzer: {analyzer.get_language_name()}")

    def get_analyzer_for_file(self, file_path: Path) -> Optional[LanguageAnalyzer]:
        """Get appropriate analyzer for a file.

        Args:
            file_path: Path to file

        Returns:
            LanguageAnalyzer that can handle this file, or None
        """
        for analyzer in self.analyzers:
            if analyzer.can_analyze(file_path):
                return analyzer
        return None

    def get_analyzer(self, language: str) -> Optional[LanguageAnalyzer]:
        """Get analyzer by language name.

        Args:
            language: Language name (e.g., "python", "shell")

        Returns:
            LanguageAnalyzer for that language, or None
        """
        return self._analyzer_by_lang.get(language)

    def get_supported_languages(self) -> List[str]:
        """Get list of supported language names.

        Returns:
            List of language names
        """
        return list(self._analyzer_by_lang.keys())
