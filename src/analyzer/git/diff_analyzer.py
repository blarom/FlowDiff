"""Main git diff analyzer."""
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import tempfile

from ..legacy import CallTreeNode
from ..call_tree_adapter import CallTreeAdapter
from .ref_resolver import GitRefResolver
from .file_change_detector import FileChangeDetector, FileChange, ChangeType
from .symbol_change_mapper import SymbolChangeMapper, SymbolChange
from utils.subprocess_runner import run_piped_commands, SubprocessError

@dataclass
class DiffResult:
    """Complete diff analysis."""
    before_ref: str
    after_ref: str
    before_description: str
    after_description: str
    file_changes: List[FileChange]
    symbol_changes: Dict[str, SymbolChange]
    before_tree: List[CallTreeNode]
    after_tree: List[CallTreeNode]
    functions_added: int
    functions_deleted: int
    functions_modified: int
    functions_unchanged: int

class GitDiffAnalyzer:
    """Analyze git diffs and build before/after call trees."""

    def __init__(self, project_root: Path, debug_log_path: Optional[Path] = None):
        self.project_root = project_root
        self.ref_resolver = GitRefResolver(project_root)
        self.file_detector = FileChangeDetector(project_root)
        self.symbol_mapper = SymbolChangeMapper(project_root)
        self.debug_log_path = debug_log_path

    def analyze_diff(
        self,
        before: str = "HEAD",
        after: str = "working"
    ) -> DiffResult:
        """Analyze diff between two refs."""
        before_sha = self.ref_resolver.resolve(before)
        after_sha = self.ref_resolver.resolve(after)

        file_changes = self.file_detector.get_changed_files(before_sha, after_sha)
        symbol_changes = self.symbol_mapper.map_changes(before_sha, after_sha, file_changes)

        before_tree = self._build_tree_at_ref(before_sha, symbol_changes, True)
        after_tree = self._build_tree_at_ref(after_sha, symbol_changes, False)

        stats = self._calculate_stats(symbol_changes)

        return DiffResult(
            before_ref=before,
            after_ref=after,
            before_description=self.ref_resolver.get_ref_description(before),
            after_description=self.ref_resolver.get_ref_description(after),
            file_changes=file_changes,
            symbol_changes=symbol_changes,
            before_tree=before_tree,
            after_tree=after_tree,
            **stats
        )

    def _build_tree_at_ref(
        self,
        ref: Optional[str],
        symbol_changes: Dict[str, SymbolChange],
        is_before: bool
    ) -> List[CallTreeNode]:
        """Build call tree at specific ref with has_changes populated.

        Args:
            ref: Git ref (SHA or "working" for working directory)
            symbol_changes: Detected changes to mark in tree
            is_before: Whether this is the before tree

        Returns:
            List of call trees built from the specified ref
        """
        # Determine if we need to checkout to temp directory
        # Use working directory if ref is None or "working"
        use_working_dir = ref is None or ref == "working"

        if use_working_dir:
            # Build from working directory
            adapter = CallTreeAdapter(self.project_root)
            context = "after ref (working directory)" if not is_before else "current state"
            adapter.symbol_tables = adapter.orchestrator.analyze(context=context)
            build_path = self.project_root
        else:
            # Checkout ref to temp directory
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir) / "checkout"
                tmp_path.mkdir()

                # Use git archive to extract ref
                try:
                    run_piped_commands(
                        [["git", "archive", ref], ["tar", "-x", "-C", str(tmp_path)]],
                        cwd=self.project_root,
                        description=f"Extracting git ref {ref}"
                    )
                except SubprocessError as e:
                    raise RuntimeError(f"Failed to extract ref {ref}: {e}") from e

                # Build tree from checkout
                adapter = CallTreeAdapter(tmp_path)
                context = f"before ref ({ref[:8]})" if is_before else f"ref ({ref[:8]})"
                adapter.symbol_tables = adapter.orchestrator.analyze(context=context)
                build_path = tmp_path

                # Continue with tree building inside the with block
                # so temp directory doesn't get deleted before we're done
                return self._build_tree_from_adapter(adapter, symbol_changes, ref, is_before)

        # For working directory, build tree outside temp directory context
        return self._build_tree_from_adapter(adapter, symbol_changes, ref, is_before)

    def _build_tree_from_adapter(
        self,
        adapter: CallTreeAdapter,
        symbol_changes: Dict[str, SymbolChange],
        ref: Optional[str],
        is_before: bool
    ) -> List[CallTreeNode]:
        """Build tree from an adapter with symbol tables already populated."""

        # Build unified symbol map
        for table in adapter.symbol_tables.values():
            for symbol in table.get_all_symbols():
                adapter.all_symbols[symbol.qualified_name] = symbol

        # Build called_by relationships
        adapter._build_called_by_relationships()

        # Get entry points FIRST
        entry_point_qnames = adapter.orchestrator.get_entry_points(adapter.symbol_tables)

        # PRE-MARK symbols with changes BEFORE building tree
        # This allows the tree builder to track max depth of changed nodes
        # IMPORTANT: Filter symbol_changes based on is_before flag:
        # - Before tree: mark MODIFIED and DELETED symbols (they exist in before ref)
        # - After tree: mark MODIFIED and ADDED symbols (they exist in after ref)
        marked_count = 0
        for qname, change in symbol_changes.items():
            # Filter based on which tree we're building
            if is_before:
                # Before tree: only mark symbols that existed before (MODIFIED or DELETED)
                if change.change_type == ChangeType.ADDED:
                    continue  # Skip added symbols (don't exist in before tree)
            else:
                # After tree: only mark symbols that exist after (MODIFIED or ADDED)
                if change.change_type == ChangeType.DELETED:
                    continue  # Skip deleted symbols (don't exist in after tree)

            if qname in adapter.all_symbols:
                adapter.all_symbols[qname].has_changes = True
                marked_count += 1

        # Build trees from entry points in all_symbols (which now have has_changes marked)
        # This ensures we use the marked symbols, not new instances
        adapter.max_changed_depth = 0
        trees = []
        for symbol in entry_point_qnames:
            if symbol.qualified_name in adapter.all_symbols:
                marked_symbol = adapter.all_symbols[symbol.qualified_name]
                tree = adapter._build_tree_recursive(marked_symbol, depth=0, visited=set())
                trees.append(tree)

        # Apply expansion state based on calculated depth
        expansion_depth = max(adapter.DEFAULT_EXPANSION_DEPTH, adapter.max_changed_depth)
        for tree in trees:
            adapter._apply_expansion_state(tree, expansion_depth)

        # Debug logging
        if self.debug_log_path:
            with open(self.debug_log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Building tree at ref: {ref} (is_before={is_before})\n")
                f.write(f"Symbol changes detected: {len(symbol_changes)}\n")
                f.write(f"Sample symbol changes (first 10):\n")
                for i, (qname, change) in enumerate(list(symbol_changes.items())[:10]):
                    f.write(f"  {i+1}. {qname} [{change.change_type.value}]\n")
                f.write(f"\nTree entry points: {len(trees)}\n")
                f.write(f"Max changed depth detected: {adapter.max_changed_depth}\n")
                f.write(f"Expansion depth: {expansion_depth}\n")

        return trees

    def _calculate_stats(self, symbol_changes: Dict[str, SymbolChange]) -> Dict[str, int]:
        """Calculate summary statistics."""
        added = sum(1 for sc in symbol_changes.values() if sc.change_type.value == "A")
        deleted = sum(1 for sc in symbol_changes.values() if sc.change_type.value == "D")
        modified = sum(1 for sc in symbol_changes.values() if sc.change_type.value == "M")

        return {
            "functions_added": added,
            "functions_deleted": deleted,
            "functions_modified": modified,
            "functions_unchanged": 0
        }
