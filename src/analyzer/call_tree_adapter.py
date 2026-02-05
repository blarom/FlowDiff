"""Adapter to convert new symbol-based architecture to CallTreeNode format."""

from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass, field

from .orchestrator import FlowDiffOrchestrator
from .core.symbol import Symbol


# Legacy FunctionInfo and CallTreeNode for backward compatibility
@dataclass
class FunctionInfo:
    """Legacy FunctionInfo for backward compatibility with UI."""
    name: str
    qualified_name: str
    file_path: str
    file_name: str
    line_number: int
    parameters: List[str]
    return_type: str
    calls: List[str]
    called_by: List[str] = field(default_factory=list)
    local_variables: List[str] = field(default_factory=list)
    is_entry_point: bool = False
    language: str = "python"
    http_method: str = None
    http_route: str = None
    has_changes: bool = False        # NEW: For diff tracking
    documentation: str = None        # NEW: Docstring/comments


@dataclass
class CallTreeNode:
    """Legacy CallTreeNode for backward compatibility with UI."""
    function: FunctionInfo
    children: List['CallTreeNode'] = field(default_factory=list)
    depth: int = 0
    is_expanded: bool = False


class CallTreeAdapter:
    """Adapts new symbol-based architecture to legacy CallTreeNode format."""

    DEFAULT_EXPANSION_DEPTH = 6  # Default tree expansion depth

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.orchestrator = FlowDiffOrchestrator(project_root)
        self.symbol_tables = None
        self.all_symbols: Dict[str, Symbol] = {}  # qualified_name -> Symbol
        self.max_changed_depth = 0  # Track deepest changed node

    def analyze_project(self) -> List[CallTreeNode]:
        """Run analysis and return legacy CallTreeNode format.

        Returns:
            List of CallTreeNode objects (entry points)
        """
        # Run new architecture analysis
        self.symbol_tables = self.orchestrator.analyze()

        # Build unified symbol map
        for table in self.symbol_tables.values():
            for symbol in table.get_all_symbols():
                self.all_symbols[symbol.qualified_name] = symbol

        # Build called_by relationships
        self._build_called_by_relationships()

        # Get entry points
        entry_point_symbols = self.orchestrator.get_entry_points(self.symbol_tables)

        # First pass: Build trees and track max depth of changed nodes
        self.max_changed_depth = 0
        trees = []
        for symbol in entry_point_symbols:
            tree = self._build_tree_recursive(symbol, depth=0, visited=set())
            trees.append(tree)

        # Second pass: Apply expansion state based on calculated depth
        expansion_depth = max(self.DEFAULT_EXPANSION_DEPTH, self.max_changed_depth)
        for tree in trees:
            self._apply_expansion_state(tree, expansion_depth)

        return trees

    def _build_called_by_relationships(self):
        """Build called_by relationships from resolved_calls."""
        for symbol in self.all_symbols.values():
            for called_name in symbol.resolved_calls:
                if called_name in self.all_symbols:
                    called_symbol = self.all_symbols[called_name]
                    # This will be added to FunctionInfo later
                    if not hasattr(called_symbol, '_called_by'):
                        called_symbol._called_by = []
                    called_symbol._called_by.append(symbol.qualified_name)

    def _build_tree_recursive(
        self,
        symbol: Symbol,
        depth: int,
        visited: Set[str]
    ) -> CallTreeNode:
        """Build CallTreeNode recursively from Symbol.

        Args:
            symbol: Symbol to convert
            depth: Current tree depth
            visited: Set of visited qualified names (prevent cycles)

        Returns:
            CallTreeNode with children
        """
        # Track max depth of changed nodes
        if symbol.has_changes and depth > self.max_changed_depth:
            self.max_changed_depth = depth

        # Convert Symbol to FunctionInfo
        func_info = self._symbol_to_function_info(symbol)

        # Create node (expansion state will be set in second pass)
        node = CallTreeNode(function=func_info, depth=depth, is_expanded=False)

        # Prevent infinite recursion
        if symbol.qualified_name in visited:
            return node

        visited.add(symbol.qualified_name)

        # Build children from resolved calls
        for called_name in symbol.resolved_calls:
            if called_name in self.all_symbols:
                child_symbol = self.all_symbols[called_name]
                child_node = self._build_tree_recursive(
                    child_symbol,
                    depth + 1,
                    visited.copy()
                )
                node.children.append(child_node)

        return node

    def _apply_expansion_state(self, node: CallTreeNode, expansion_depth: int) -> None:
        """Apply expansion state to tree nodes based on depth threshold.

        Nodes at depth < expansion_depth are marked as expanded.
        This implements dynamic expansion: if a changed node is at depth 8,
        and DEFAULT_EXPANSION_DEPTH is 6, we expand to depth 8.

        Args:
            node: CallTreeNode to update
            expansion_depth: Depth threshold for expansion
        """
        # Expand if depth is less than threshold
        if node.depth < expansion_depth:
            node.is_expanded = True

        # Recursively apply to children
        for child in node.children:
            self._apply_expansion_state(child, expansion_depth)

    def _symbol_to_function_info(self, symbol: Symbol) -> FunctionInfo:
        """Convert Symbol to legacy FunctionInfo.

        Args:
            symbol: Symbol to convert

        Returns:
            FunctionInfo object
        """
        # Extract metadata
        metadata = symbol.metadata
        parameters = metadata.get("parameters", [])
        return_type = metadata.get("return_type", None)

        # Get called_by list
        called_by = getattr(symbol, '_called_by', [])

        # Create FunctionInfo
        return FunctionInfo(
            name=symbol.name,
            qualified_name=symbol.qualified_name,
            file_path=symbol.file_path,
            file_name=Path(symbol.file_path).name,
            line_number=symbol.line_number,
            parameters=parameters,
            return_type=return_type or "",
            calls=symbol.resolved_calls,
            called_by=called_by,
            local_variables=[],  # Not needed for UI
            is_entry_point=symbol.is_entry_point,
            language=symbol.language,
            http_method=metadata.get("http_method"),
            http_route=metadata.get("http_route"),
            has_changes=symbol.has_changes,        # NEW
            documentation=symbol.documentation     # NEW
        )

    def get_functions_dict(self) -> Dict[str, FunctionInfo]:
        """Get all functions as FunctionInfo dict (for compatibility).

        Returns:
            Map from qualified_name to FunctionInfo
        """
        functions = {}
        for qualified_name, symbol in self.all_symbols.items():
            functions[qualified_name] = self._symbol_to_function_info(symbol)
        return functions
