"""Git reference resolver for FlowDiff."""
from pathlib import Path
from typing import Optional
import subprocess

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
            result = subprocess.run(
                ["git", "rev-parse", "--verify", ref],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Invalid git ref '{ref}': {e.stderr.strip()}")

    def get_ref_description(self, ref: str) -> str:
        """Get human-readable description."""
        if ref == self.WORKING_TREE_MARKER:
            return "Working directory (uncommitted changes)"

        sha = self.resolve(ref)
        try:
            result = subprocess.run(
                ["git", "name-rev", "--name-only", sha],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            branch = result.stdout.strip()
            return f"{ref} ({branch}, {sha[:7]})"
        except:
            return f"{ref} ({sha[:7]})"
