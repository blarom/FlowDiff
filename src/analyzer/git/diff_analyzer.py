"""Main git diff analyzer."""
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from ..legacy import CallTreeNode
from ..call_tree_adapter import CallTreeAdapter
from .ref_resolver import GitRefResolver
from .file_change_detector import FileChangeDetector, FileChange
from .symbol_change_mapper import SymbolChangeMapper, SymbolChange

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

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.ref_resolver = GitRefResolver(project_root)
        self.file_detector = FileChangeDetector(project_root)
        self.symbol_mapper = SymbolChangeMapper(project_root)

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
        """Build call tree with has_changes populated."""
        adapter = CallTreeAdapter(self.project_root)
        trees = adapter.analyze_project()
        self._mark_changed_nodes(trees, symbol_changes)
        return trees

    def _mark_changed_nodes(
        self,
        trees: List[CallTreeNode],
        symbol_changes: Dict[str, SymbolChange]
    ) -> None:
        """Mark nodes with changes."""
        def mark_recursive(node: CallTreeNode):
            if node.function.qualified_name in symbol_changes:
                node.function.has_changes = True
            for child in node.children:
                mark_recursive(child)

        for tree in trees:
            mark_recursive(tree)

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
