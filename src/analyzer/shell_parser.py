"""
Shell script parser for FlowDiff.

Parses .sh files to extract:
- curl commands (HTTP API calls)
- Python invocations (python script.py, python -m module)
- Script-to-script calls (./other_script.sh)
"""

import re
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ShellCommand:
    """Represents a command extracted from a shell script."""
    type: str  # "http_call", "python_invoke", "script_invoke"
    target: str  # URL path, Python module, or script path
    method: Optional[str] = None  # HTTP method (GET, POST, etc.) for http_call
    line_number: int = 0


def parse_shell_script(file_path: Path) -> List[ShellCommand]:
    """Parse shell script and extract commands.

    Args:
        file_path: Path to .sh file

    Returns:
        List of ShellCommands found in the script
    """
    if not file_path.exists():
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, OSError):
        return []

    commands = []

    # Extract curl commands
    commands.extend(_extract_curl_commands(content))

    # Extract Python invocations
    commands.extend(_extract_python_invocations(content, file_path))

    # Extract script-to-script calls
    commands.extend(_extract_script_calls(content, file_path))

    return commands


def _extract_curl_commands(content: str) -> List[ShellCommand]:
    """Extract curl HTTP calls from shell script.

    Patterns to match:
        curl http://localhost:8000/analyze
        curl -X POST "$SERVER_URL/analyze"
        curl -s -X POST http://localhost:8000/api/analyze
    """
    commands = []

    # Split into lines for line number tracking
    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        # Skip comments
        if line.strip().startswith('#'):
            continue

        # Check if line contains curl
        if 'curl' not in line:
            continue

        # Extract HTTP method
        method = 'GET'  # Default
        if '-X POST' in line or '--request POST' in line:
            method = 'POST'
        elif '-X PUT' in line:
            method = 'PUT'
        elif '-X DELETE' in line:
            method = 'DELETE'
        elif '-X PATCH' in line:
            method = 'PATCH'

        # Extract URL/path
        # Pattern: http://HOST:PORT/path or $VAR/path
        url_patterns = [
            r'https?://[^\s"\']+(/[^\s"\']*)',  # http://localhost:8000/analyze
            r'\$[A-Z_]+(/[^\s"\']*)',  # $SERVER_URL/analyze
            r'"\$[A-Z_]+(/[^\s"\']*)"',  # "$SERVER_URL/analyze"
        ]

        path = None
        for pattern in url_patterns:
            match = re.search(pattern, line)
            if match:
                # Extract just the path part (group 1)
                path = match.group(1)
                break

        if not path:
            # Try to extract any /path after curl
            match = re.search(r'(/[a-zA-Z0-9_/-]+)', line)
            if match:
                path = match.group(1)

        if path:
            commands.append(ShellCommand(
                type="http_call",
                target=path,
                method=method,
                line_number=line_num
            ))

    return commands


def _extract_python_invocations(content: str, script_path: Path) -> List[ShellCommand]:
    """Extract Python invocations from shell script.

    Patterns to match:
        python script.py
        python -m module.name
        python3 src/analyzer.py
    """
    commands = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        # Skip comments
        if line.strip().startswith('#'):
            continue

        # Check for python invocations
        if 'python' not in line:
            continue

        # Pattern: python -m module.name
        match = re.search(r'python[0-9.]* -m ([a-zA-Z0-9_.]+)', line)
        if match:
            module = match.group(1)
            commands.append(ShellCommand(
                type="python_invoke",
                target=module,
                line_number=line_num
            ))
            continue

        # Pattern: python script.py or python src/analyzer.py
        match = re.search(r'python[0-9.]* ([a-zA-Z0-9_/.]+\.py)', line)
        if match:
            script = match.group(1)
            commands.append(ShellCommand(
                type="python_invoke",
                target=script,
                line_number=line_num
            ))

    return commands


def _extract_script_calls(content: str, script_path: Path) -> List[ShellCommand]:
    """Extract script-to-script calls.

    Patterns to match:
        ./other_script.sh
        bash scripts/setup.sh
        sh start_server.sh
    """
    commands = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        # Skip comments
        if line.strip().startswith('#'):
            continue

        # Pattern: ./script.sh or bash script.sh
        patterns = [
            r'\.(/[a-zA-Z0-9_/.]+\.sh)',  # ./script.sh
            r'bash ([a-zA-Z0-9_/.]+\.sh)',  # bash script.sh
            r'sh ([a-zA-Z0-9_/.]+\.sh)',  # sh script.sh
        ]

        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                script = match.group(1)
                commands.append(ShellCommand(
                    type="script_invoke",
                    target=script,
                    line_number=line_num
                ))
                break

    return commands
