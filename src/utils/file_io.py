"""File I/O utilities with consistent error handling."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class FileIOError(Exception):
    """Raised when file I/O operations fail."""
    pass


def ensure_parent_dir(file_path: Path) -> None:
    """
    Ensure parent directory exists for a file path.

    Args:
        file_path: Path to file

    Raises:
        FileIOError: If directory creation fails
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured parent directory exists: {file_path.parent}")
    except OSError as e:
        raise FileIOError(f"Failed to create directory {file_path.parent}: {e}") from e


def safe_write_json(
    file_path: Path,
    data: Dict[str, Any],
    create_parents: bool = True,
    indent: Optional[int] = 2,
) -> None:
    """
    Safely write JSON data to file.

    Args:
        file_path: Path to output file
        data: Dictionary to write as JSON
        create_parents: Create parent directories if needed
        indent: JSON indentation (None for compact)

    Raises:
        FileIOError: If write fails
    """
    try:
        if create_parents:
            ensure_parent_dir(file_path)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

        logger.info(f"Wrote JSON to {file_path}")

    except (OSError, TypeError, ValueError) as e:
        raise FileIOError(f"Failed to write JSON to {file_path}: {e}") from e


def safe_read_json(file_path: Path) -> Dict[str, Any]:
    """
    Safely read JSON data from file.

    Args:
        file_path: Path to input file

    Returns:
        Parsed JSON data as dictionary

    Raises:
        FileIOError: If read fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.debug(f"Read JSON from {file_path}")
        return data

    except (OSError, json.JSONDecodeError) as e:
        raise FileIOError(f"Failed to read JSON from {file_path}: {e}") from e


def safe_write_text(
    file_path: Path,
    content: str,
    create_parents: bool = True,
    encoding: str = 'utf-8',
) -> None:
    """
    Safely write text to file.

    Args:
        file_path: Path to output file
        content: Text content to write
        create_parents: Create parent directories if needed
        encoding: Text encoding

    Raises:
        FileIOError: If write fails
    """
    try:
        if create_parents:
            ensure_parent_dir(file_path)

        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)

        logger.info(f"Wrote text to {file_path}")

    except OSError as e:
        raise FileIOError(f"Failed to write text to {file_path}: {e}") from e


def safe_read_text(file_path: Path, encoding: str = 'utf-8') -> str:
    """
    Safely read text from file.

    Args:
        file_path: Path to input file
        encoding: Text encoding

    Returns:
        File contents as string

    Raises:
        FileIOError: If read fails
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()

        logger.debug(f"Read text from {file_path}")
        return content

    except OSError as e:
        raise FileIOError(f"Failed to read text from {file_path}: {e}") from e
