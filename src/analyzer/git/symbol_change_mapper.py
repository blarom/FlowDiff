"""Map file changes to symbol changes."""
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import subprocess
import tempfile

from ..orchestrator import FlowDiffOrchestrator
from ..core.symbol import Symbol
from .file_change_detector import FileChange, ChangeType

@dataclass
class SymbolChange:
    qualified_name: str
    change_type: ChangeType
    before_symbol: Optional[Symbol] = None
    after_symbol: Optional[Symbol] = None

class SymbolChangeMapper:
    """Map file-level changes to symbol-level changes."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def map_changes(
        self,
        before_ref: Optional[str],
        after_ref: Optional[str],
        file_changes: List[FileChange]
    ) -> Dict[str, SymbolChange]:
        """Map file changes to symbol changes."""
        before_symbols = self._build_symbol_table_at_ref(before_ref) if before_ref else {}
        after_symbols = self._build_symbol_table_at_ref(after_ref) if after_ref else self._build_current_symbol_table()

        symbol_changes = {}

        # Modified and deleted
        for qname, before_sym in before_symbols.items():
            if qname in after_symbols:
                after_sym = after_symbols[qname]
                if self._symbols_differ(before_sym, after_sym):
                    symbol_changes[qname] = SymbolChange(
                        qualified_name=qname,
                        change_type=ChangeType.MODIFIED,
                        before_symbol=before_sym,
                        after_symbol=after_sym
                    )
            else:
                symbol_changes[qname] = SymbolChange(
                    qualified_name=qname,
                    change_type=ChangeType.DELETED,
                    before_symbol=before_sym
                )

        # Added
        for qname, after_sym in after_symbols.items():
            if qname not in before_symbols:
                symbol_changes[qname] = SymbolChange(
                    qualified_name=qname,
                    change_type=ChangeType.ADDED,
                    after_symbol=after_sym
                )

        return symbol_changes

    def _build_symbol_table_at_ref(self, ref: str) -> Dict[str, Symbol]:
        """Build symbol table at specific git ref."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "checkout"
            tmp_path.mkdir()

            # Use Popen to pipe git archive to tar
            archive_process = subprocess.Popen(
                ["git", "archive", ref],
                cwd=self.project_root,
                stdout=subprocess.PIPE
            )

            extract_process = subprocess.run(
                ["tar", "-x", "-C", str(tmp_path)],
                stdin=archive_process.stdout,
                check=True
            )

            archive_process.wait()
            if archive_process.returncode != 0:
                raise subprocess.CalledProcessError(archive_process.returncode, ["git", "archive", ref])

            orchestrator = FlowDiffOrchestrator(tmp_path)
            symbol_tables = orchestrator.analyze()

            all_symbols = {}
            for table in symbol_tables.values():
                for symbol in table.get_all_symbols():
                    all_symbols[symbol.qualified_name] = symbol

            return all_symbols

    def _build_current_symbol_table(self) -> Dict[str, Symbol]:
        """Build symbol table for working tree."""
        orchestrator = FlowDiffOrchestrator(self.project_root)
        symbol_tables = orchestrator.analyze()

        all_symbols = {}
        for table in symbol_tables.values():
            for symbol in table.get_all_symbols():
                all_symbols[symbol.qualified_name] = symbol

        return all_symbols

    def _symbols_differ(self, before: Symbol, after: Symbol) -> bool:
        """Check if symbols differ in meaningful ways.

        NOTE: We intentionally DO NOT compare line numbers, because functions
        often move to different lines when code is added/removed above them.
        This was causing false positives where unchanged functions were marked
        as modified just because they shifted.

        We only compare:
        - Metadata (parameters, return type, etc.)
        - Resolved calls (what the function calls)
        - Documentation (docstrings)

        Args:
            before: Symbol from before ref
            after: Symbol from after ref

        Returns:
            True if symbols differ in meaningful ways
        """
        differs = False
        reason = None

        # Compare metadata (parameters, return type, etc.)
        if before.metadata != after.metadata:
            differs = True
            reason = "metadata"

        # Compare what functions are called
        if set(before.resolved_calls) != set(after.resolved_calls):
            differs = True
            reason = "resolved_calls"

        # Compare documentation
        if before.documentation != after.documentation:
            differs = True
            reason = "documentation"

        return differs
