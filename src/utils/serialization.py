"""Serialization utilities for common data transformations."""

from typing import Any, Dict, List, TYPE_CHECKING

from analyzer.core.symbol import Symbol
from analyzer.git.symbol_change_mapper import SymbolChange

if TYPE_CHECKING:
    from analyzer.legacy import CallTreeNode


def serialize_symbol(symbol: Symbol) -> Dict[str, Any]:
    """
    Serialize a Symbol object to a dictionary.

    Args:
        symbol: Symbol to serialize

    Returns:
        Dictionary representation of symbol
    """
    return {
        "name": symbol.name,
        "qualified_name": symbol.qualified_name,
        "file_path": symbol.file_path,
        "file_name": symbol.file_path.split('/')[-1] if symbol.file_path else "",
        "line_number": symbol.line_number,
        "has_changes": getattr(symbol, 'has_changes', False),
    }


def extract_deleted_functions(symbol_changes: Dict[str, SymbolChange]) -> List[Dict[str, Any]]:
    """
    Extract deleted functions from symbol changes.

    Args:
        symbol_changes: Dictionary of symbol changes keyed by qualified name

    Returns:
        List of deleted function dictionaries
    """
    deleted = []
    for qname, symbol_change in symbol_changes.items():
        if symbol_change.change_type.value == "D" and symbol_change.before_symbol:
            deleted.append(serialize_symbol(symbol_change.before_symbol))
    return deleted


def serialize_tree_node(node: "CallTreeNode", minimal: bool = False) -> Dict[str, Any]:
    """
    Convert CallTreeNode to JSON-serializable dictionary.

    Args:
        node: CallTreeNode to serialize
        minimal: If True, include only essential fields (for diff view).
                 If False, include all metadata (for full tree view).

    Returns:
        Dictionary representation of tree node
    """
    if minimal:
        # Minimal serialization for diff view
        return {
            "function": {
                "name": node.function.name,
                "qualified_name": node.function.qualified_name,
                "file_path": node.function.file_path,
                "line_number": node.function.line_number,
                "has_changes": node.function.has_changes
            },
            "children": [serialize_tree_node(c, minimal=True) for c in node.children],
            "is_expanded": node.is_expanded,
            "depth": node.depth
        }
    else:
        # Full serialization for complete tree view
        return {
            "function": {
                "name": node.function.name,
                "qualified_name": node.function.qualified_name,
                "file_path": node.function.file_path,
                "file_name": node.function.file_name,
                "line_number": node.function.line_number,
                "parameters": node.function.parameters,
                "return_type": node.function.return_type,
                "calls": node.function.calls,
                "called_by": node.function.called_by,
                "local_variables": node.function.local_variables,
                "is_entry_point": node.function.is_entry_point,
                "has_changes": node.function.has_changes,
                "documentation": node.function.documentation or ""
            },
            "children": [serialize_tree_node(child, minimal=False) for child in node.children],
            "depth": node.depth
        }
