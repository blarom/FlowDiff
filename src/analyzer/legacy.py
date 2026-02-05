"""Legacy data structures for backward compatibility with UI."""
from dataclasses import dataclass, field
from typing import List, Optional

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
    http_method: Optional[str] = None
    http_route: Optional[str] = None
    has_changes: bool = False
    documentation: Optional[str] = None

@dataclass
class CallTreeNode:
    """Legacy CallTreeNode for backward compatibility with UI."""
    function: FunctionInfo
    children: List['CallTreeNode'] = field(default_factory=list)
    depth: int = 0
    is_expanded: bool = False
