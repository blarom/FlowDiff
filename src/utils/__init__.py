"""Utils package initialization."""

from utils.file_io import (
    FileIOError,
    ensure_parent_dir,
    safe_read_json,
    safe_read_text,
    safe_write_json,
    safe_write_text,
)
from utils.serialization import extract_deleted_functions, serialize_symbol
from utils.subprocess_runner import (
    CommandResult,
    SubprocessError,
    run_command,
    run_piped_commands,
)

__all__ = [
    # File I/O
    "FileIOError",
    "ensure_parent_dir",
    "safe_read_json",
    "safe_read_text",
    "safe_write_json",
    "safe_write_text",
    # Serialization
    "extract_deleted_functions",
    "serialize_symbol",
    # Subprocess
    "CommandResult",
    "SubprocessError",
    "run_command",
    "run_piped_commands",
]
