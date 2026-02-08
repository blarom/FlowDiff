"""Detect file changes between git refs."""
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from utils.subprocess_runner import run_command, SubprocessError

class ChangeType(Enum):
    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"

@dataclass
class FileChange:
    path: str
    change_type: ChangeType
    old_path: Optional[str] = None

class FileChangeDetector:
    """Detect file changes between git refs."""

    SUPPORTED_EXTENSIONS = {".py", ".sh"}

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def get_changed_files(
        self,
        before_ref: Optional[str],
        after_ref: Optional[str]
    ) -> List[FileChange]:
        """Get changed files between two refs."""
        cmd = ["git", "diff", "--name-status"]

        if before_ref is None and after_ref is None:
            raise ValueError("At least one ref must be specified")
        elif after_ref is None:
            cmd.append(before_ref)
        elif before_ref is None:
            cmd.extend([after_ref, "--"])
        else:
            cmd.extend([f"{before_ref}..{after_ref}"])

        result = run_command(
            cmd,
            cwd=self.project_root,
            description="Get changed files"
        )

        changes = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            change = self._parse_change_line(line)
            if change and self._is_supported_file(change.path):
                changes.append(change)

        return changes

    def _parse_change_line(self, line: str) -> Optional[FileChange]:
        """Parse git diff --name-status line."""
        parts = line.split("\t")
        if len(parts) < 2:
            return None

        status = parts[0][0]
        try:
            change_type = ChangeType(status)
        except ValueError:
            return None

        if change_type == ChangeType.RENAMED:
            return FileChange(
                path=parts[2],
                change_type=change_type,
                old_path=parts[1]
            )
        else:
            return FileChange(
                path=parts[1],
                change_type=change_type
            )

    def _is_supported_file(self, path: str) -> bool:
        return Path(path).suffix in self.SUPPORTED_EXTENSIONS
