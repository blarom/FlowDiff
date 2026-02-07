"""
FlowDiff Constants - Centralized Configuration

All magic numbers, strings, and configuration values should be defined here.
This prevents scattered configuration and makes values easy to update.
"""

from pathlib import Path

# ==============================================================================
# Application Metadata
# ==============================================================================

APP_NAME = "FlowDiff"
APP_VERSION = "0.3.0"  # Single source of truth for version
APP_DESCRIPTION = "Python call flow analyzer with git diff integration"

# ==============================================================================
# Server Configuration
# ==============================================================================

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

# ==============================================================================
# Git Configuration
# ==============================================================================

# Default git references for comparison
DEFAULT_BEFORE_REF = "HEAD"
DEFAULT_AFTER_REF = "working"

# Special ref name for working directory (unstaged changes)
WORKING_DIR_REF = "working"

# ==============================================================================
# Analysis Configuration
# ==============================================================================

# Call tree expansion depth
DEFAULT_EXPANSION_DEPTH = 6
MAX_EXPANSION_DEPTH = 20
MIN_EXPANSION_DEPTH = 1

# ==============================================================================
# Timeouts (in seconds)
# ==============================================================================

# External diff viewer timeouts
VSCODE_TIMEOUT = 2
DIFFTASTIC_TIMEOUT = 2
GIT_DIFFTOOL_TIMEOUT = 5

# Git operation timeouts
GIT_ARCHIVE_TIMEOUT = 30
GIT_DIFF_TIMEOUT = 10

# Default subprocess timeout
SUBPROCESS_DEFAULT_TIMEOUT = 60

# ==============================================================================
# File Patterns & Extensions
# ==============================================================================

# Supported file extensions
PYTHON_EXTENSION = ".py"
SHELL_EXTENSION = ".sh"

# File patterns to exclude from analysis
EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".git",
    ".venv",
    "venv",
    "env",
    ".pytest_cache",
    ".mypy_cache",
    "*.egg-info",
    ".DS_Store",
]

# Patterns for script entry points
SCRIPT_ENTRY_PREFIX = "<script:"
SCRIPT_ENTRY_SUFFIX = ">"

# ==============================================================================
# Report Formatting
# ==============================================================================

# Separator characters and widths
SEPARATOR_WIDTH = 80
SEPARATOR_CHAR = "="
SUB_SEPARATOR_CHAR = "-"

# Tree rendering characters
TREE_INDENT = "    "  # 4 spaces
TREE_PIPE = "│"
TREE_TEE = "├──"
TREE_LAST = "└──"
TREE_EXPAND_COLLAPSED = "▶"
TREE_EXPAND_EXPANDED = "▼"

# ==============================================================================
# Environment Variables
# ==============================================================================

# LLM provider configuration
ENV_LLM_PROVIDER = "FLOWDIFF_LLM_PROVIDER"
ENV_LLM_API_KEY = "FLOWDIFF_LLM_API_KEY"
ENV_LLM_API_KEY_ENV = "FLOWDIFF_LLM_API_KEY_ENV"
ENV_LLM_MODEL = "FLOWDIFF_LLM_MODEL"
ENV_LLM_MAX_TOKENS = "FLOWDIFF_LLM_MAX_TOKENS"

# ==============================================================================
# LLM Defaults
# ==============================================================================

DEFAULT_LLM_PROVIDER = "anthropic"
DEFAULT_LLM_MODEL_ANTHROPIC = "claude-3-5-sonnet-20241022"
DEFAULT_LLM_MAX_TOKENS = 4000

# ==============================================================================
# Output Directories
# ==============================================================================

# Default output directory (relative to project root)
DEFAULT_OUTPUT_DIR = "output"

# Output subdirectories
LOG_DIR_NAME = "logs"
REPORT_DIR_NAME = "reports"

# ==============================================================================
# Log Configuration
# ==============================================================================

LOG_FILE_PREFIX = "flowdiff"
DEBUG_LOG_SUFFIX = "_debug"
LOG_FILE_EXTENSION = ".log"

# ==============================================================================
# File Names
# ==============================================================================

# Config file names
CONFIG_FILE_NAME = "flowdiff.toml"
CONFIG_SAMPLE_NAME = "flowdiff.toml.sample"

# ==============================================================================
# Diff Display
# ==============================================================================

# External diff viewers (in order of preference)
DIFF_VIEWER_VSCODE = "code"
DIFF_VIEWER_DIFFTASTIC = "difft"
DIFF_VIEWER_GIT = "git"

# Diff viewer commands
VSCODE_DIFF_ARGS = ["--diff", "--wait"]
GIT_DIFFTOOL_COMMAND = ["git", "difftool", "--no-prompt"]

# ==============================================================================
# Symbol Change Types
# ==============================================================================

CHANGE_TYPE_ADDED = "A"
CHANGE_TYPE_DELETED = "D"
CHANGE_TYPE_MODIFIED = "M"

# ==============================================================================
# Cache & Temporary Files
# ==============================================================================

# Maximum age for stale cache files (days)
MAX_CACHE_AGE_DAYS = 30

# Maximum age for old reports (days)
MAX_REPORT_AGE_DAYS = 90

# ==============================================================================
# Utility Functions
# ==============================================================================

def get_separator(char: str = SEPARATOR_CHAR, width: int = SEPARATOR_WIDTH) -> str:
    """Get a separator line with specified character and width."""
    return char * width


def get_output_dir(base_dir: Path) -> Path:
    """Get the default output directory path."""
    return base_dir / DEFAULT_OUTPUT_DIR


def get_log_dir(base_dir: Path) -> Path:
    """Get the log directory path."""
    return get_output_dir(base_dir) / LOG_DIR_NAME


def get_report_dir(base_dir: Path) -> Path:
    """Get the report directory path."""
    return get_output_dir(base_dir) / REPORT_DIR_NAME


def format_script_entry(name: str) -> str:
    """Format a script entry point name."""
    return f"{SCRIPT_ENTRY_PREFIX}{name}{SCRIPT_ENTRY_SUFFIX}"


def is_script_entry(name: str) -> bool:
    """Check if a name is a script entry point."""
    return name.startswith(SCRIPT_ENTRY_PREFIX) and name.endswith(SCRIPT_ENTRY_SUFFIX)


def extract_script_name(entry: str) -> str:
    """Extract script name from entry point format."""
    if is_script_entry(entry):
        return entry[len(SCRIPT_ENTRY_PREFIX):-len(SCRIPT_ENTRY_SUFFIX)]
    return entry
