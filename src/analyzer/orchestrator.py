"""FlowDiff orchestrator for multi-language analysis."""

from pathlib import Path
from typing import Dict, List
from collections import defaultdict
import logging

from .core.symbol import SymbolTable, Symbol
from .core.cross_language_resolver import CrossLanguageResolver
from .registry import LanguageRegistry
from .python.python_analyzer import PythonAnalyzer
from .shell.shell_analyzer import ShellAnalyzer
from .bridges.http_to_python import HTTPToPythonBridge

# Setup logger
logger = logging.getLogger(__name__)


class FlowDiffOrchestrator:
    """Main orchestrator for multi-language static analysis.

    Coordinates the full analysis pipeline:
    1. Discover files
    2. Group by language
    3. Build per-language symbol tables
    4. Resolve intra-language calls
    5. Resolve cross-language calls
    6. Build unified call graph
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.registry = LanguageRegistry()
        self.resolver = CrossLanguageResolver()

        # Register analyzers
        self.registry.register(PythonAnalyzer(project_root))
        self.registry.register(ShellAnalyzer(project_root))

        # Register bridges
        self.resolver.register_bridge(HTTPToPythonBridge())

    def analyze(self) -> Dict[str, SymbolTable]:
        """Run full analysis pipeline.

        Returns:
            Map from language name to SymbolTable with resolved calls
        """
        logger.info("\n=== FlowDiff Multi-Language Analysis ===")
        logger.info(f"Project: {self.project_root}\n")

        # Step 1: Discover files
        logger.info("Step 1: Discovering files...")
        files = self._discover_files()
        logger.info(f"  Found {len(files)} files\n")

        # Step 2: Group by language
        logger.info("Step 2: Grouping by language...")
        files_by_lang = self._group_by_language(files)
        for lang, lang_files in files_by_lang.items():
            logger.info(f"  {lang}: {len(lang_files)} files")
        logger.info("")

        # Step 3: Build symbol tables
        logger.info("Step 3: Building symbol tables...")
        symbol_tables = {}
        for lang, lang_files in files_by_lang.items():
            analyzer = self.registry.get_analyzer(lang)
            if not analyzer:
                continue

            logger.info(f"  {lang}:")
            tables = []
            for file_path in lang_files:
                table = analyzer.build_symbol_table(file_path)
                tables.append(table)
                logger.info(f"    {file_path.name}: {len(table)} symbols")

            merged = analyzer.merge_symbol_tables(tables)
            symbol_tables[lang] = merged
            logger.info(f"  Total {lang} symbols: {len(merged)}\n")

        # Step 4: Resolve intra-language calls
        logger.info("Step 4: Resolving intra-language calls...")
        for lang, table in symbol_tables.items():
            analyzer = self.registry.get_analyzer(lang)
            if analyzer:
                logger.info(f"  Resolving {lang} calls...")
                analyzer.resolve_calls(table)
        logger.info("")

        # Step 4.5: Mark entry points
        logger.info("Step 4.5: Marking entry points...")
        for lang, table in symbol_tables.items():
            analyzer = self.registry.get_analyzer(lang)
            if analyzer and hasattr(analyzer, 'mark_entry_points'):
                analyzer.mark_entry_points(table)
                entry_count = sum(1 for s in table.get_all_symbols() if s.is_entry_point)
                logger.info(f"  {lang}: {entry_count} entry points marked")
        logger.info("")

        # Step 5: Resolve cross-language calls
        logger.info("Step 5: Resolving cross-language calls...")
        cross_refs = self.resolver.resolve_cross_language_calls(symbol_tables)
        logger.info(f"  Found {len(cross_refs)} cross-language references\n")

        # Apply cross-references to symbols
        self.resolver.apply_cross_refs(symbol_tables, cross_refs)

        logger.info("=== Analysis Complete ===\n")
        return symbol_tables

    def _discover_files(self) -> List[Path]:
        """Discover all relevant source files in project.

        Returns:
            List of file paths
        """
        files = []

        # Find Python files
        for path in self.project_root.rglob('*.py'):
            if self._should_include_file(path):
                files.append(path)

        # Find shell scripts
        for path in self.project_root.rglob('*.sh'):
            if self._should_include_file(path):
                files.append(path)

        return files

    def _should_include_file(self, path: Path) -> bool:
        """Check if file should be included in analysis.

        Excludes:
        - Hidden directories (.*,)
        - Virtual environments
        - Node modules
        - __pycache__

        Args:
            path: File path

        Returns:
            True if file should be included
        """
        exclude_patterns = [
            'venv', 'node_modules', '__pycache__', '.git',
            '.pytest_cache', '.mypy_cache', 'build', 'dist'
        ]

        for part in path.parts:
            if part.startswith('.') or part in exclude_patterns:
                return False

        return True

    def _group_by_language(self, files: List[Path]) -> Dict[str, List[Path]]:
        """Group files by language.

        Args:
            files: List of file paths

        Returns:
            Map from language name to list of file paths
        """
        groups = defaultdict(list)

        for file_path in files:
            analyzer = self.registry.get_analyzer_for_file(file_path)
            if analyzer:
                lang = analyzer.get_language_name()
                groups[lang].append(file_path)

        return dict(groups)

    def get_all_symbols(self, symbol_tables: Dict[str, SymbolTable]) -> List[Symbol]:
        """Get all symbols from all language tables.

        Args:
            symbol_tables: Map from language to SymbolTable

        Returns:
            List of all symbols
        """
        all_symbols = []
        for table in symbol_tables.values():
            all_symbols.extend(table.get_all_symbols())
        return all_symbols

    def get_entry_points(self, symbol_tables: Dict[str, SymbolTable]) -> List[Symbol]:
        """Get entry point symbols.

        Entry points are:
        - Shell scripts (always entry points)
        - Python functions marked as entry points

        Args:
            symbol_tables: Map from language to SymbolTable

        Returns:
            List of entry point symbols
        """
        entry_points = []

        for lang, table in symbol_tables.items():
            for symbol in table.get_all_symbols():
                if symbol.is_entry_point or lang == "shell":
                    entry_points.append(symbol)

        return entry_points
