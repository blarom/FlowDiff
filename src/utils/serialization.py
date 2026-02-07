"""Serialization utilities for common data transformations."""

from typing import Any, Dict, List

from analyzer.models import Symbol, SymbolChange


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
