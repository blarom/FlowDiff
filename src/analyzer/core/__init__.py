"""Core abstractions for multi-language static analysis."""

from .symbol import Symbol, SymbolTable
from .language_analyzer import LanguageAnalyzer
from .language_bridge import LanguageBridge
from .cross_language_resolver import CrossLanguageResolver

__all__ = [
    'Symbol',
    'SymbolTable',
    'LanguageAnalyzer',
    'LanguageBridge',
    'CrossLanguageResolver',
]
