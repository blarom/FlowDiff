"""Git reference resolver for FlowDiff."""
from pathlib import Path
from typing import Optional

from utils.subprocess_runner import run_command, SubprocessError


class GitRefResolver:
    """Resolve git reference strings to commit SHAs."""

    WORKING_TREE_MARKER = "working"

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self._verify_git_repo()

    def _verify_git_repo(self) -> None:
        """Check if project_root is a git repository."""
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {self.project_root}")

    def resolve(self, ref: str) -> Optional[str]:
        """Resolve ref to commit SHA.

        Returns None for "working" (uncommitted changes).
        """
        if ref == self.WORKING_TREE_MARKER:
            return None

        try:
            result = run_command(
                ["git", "rev-parse", "--verify", ref],
                cwd=self.project_root,
                description=f"Resolve git ref '{ref}'"
            )
            return result.stdout.strip()
        except SubprocessError as e:
            raise ValueError(f"Invalid git ref '{ref}': {e}")

    def get_ref_description(self, ref: str) -> str:
        """Get human-readable description."""
        if ref == self.WORKING_TREE_MARKER:
            return "Working directory (uncommitted changes)"

        sha = self.resolve(ref)
        try:
            result = run_command(
                ["git", "name-rev", "--name-only", sha],
                cwd=self.project_root,
                description="Get ref name",
                check=False
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                return f"{ref} ({branch}, {sha[:7]})"
            return f"{ref} ({sha[:7]})"
        except SubprocessError:
            return f"{ref} ({sha[:7]})"
