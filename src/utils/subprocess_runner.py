"""Subprocess execution wrapper with consistent error handling and logging."""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

from constants import SUBPROCESS_DEFAULT_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of a subprocess command execution."""
    stdout: str
    stderr: str
    returncode: int
    command: List[str]


class SubprocessError(Exception):
    """Raised when a subprocess command fails."""
    def __init__(self, message: str, result: Optional[CommandResult] = None):
        super().__init__(message)
        self.result = result


def run_command(
    command: List[str],
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[int] = None,
    description: Optional[str] = None,
    check: bool = True,
    capture_output: bool = True,
) -> CommandResult:
    """
    Run a subprocess command with consistent error handling.

    Args:
        command: Command and arguments as list
        cwd: Working directory for command
        timeout: Timeout in seconds (default: SUBPROCESS_DEFAULT_TIMEOUT)
        description: Human-readable description for logging/errors
        check: Raise exception if return code is non-zero
        capture_output: Capture stdout/stderr (default: True)

    Returns:
        CommandResult with stdout, stderr, and return code

    Raises:
        SubprocessError: If command fails and check=True
    """
    if timeout is None:
        timeout = SUBPROCESS_DEFAULT_TIMEOUT

    desc = description or " ".join(command)
    logger.debug(f"Running command: {desc}")
    logger.debug(f"  Command: {' '.join(command)}")
    logger.debug(f"  CWD: {cwd}")
    logger.debug(f"  Timeout: {timeout}s")

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
            check=False,  # We'll handle checking ourselves
        )

        cmd_result = CommandResult(
            stdout=result.stdout if capture_output else "",
            stderr=result.stderr if capture_output else "",
            returncode=result.returncode,
            command=command,
        )

        if check and result.returncode != 0:
            error_msg = (
                f"Command failed: {desc}\n"
                f"  Command: {' '.join(command)}\n"
                f"  CWD: {cwd}\n"
                f"  Return code: {result.returncode}\n"
                f"  Stderr: {result.stderr if capture_output else '(not captured)'}"
            )
            logger.error(error_msg)
            raise SubprocessError(error_msg, cmd_result)

        logger.debug(f"Command succeeded: {desc} (return code: {result.returncode})")
        return cmd_result

    except subprocess.TimeoutExpired as e:
        error_msg = (
            f"Command timed out after {timeout}s: {desc}\n"
            f"  Command: {' '.join(command)}\n"
            f"  CWD: {cwd}"
        )
        logger.error(error_msg)
        raise SubprocessError(error_msg) from e

    except FileNotFoundError as e:
        error_msg = (
            f"Command not found: {command[0]}\n"
            f"  Full command: {' '.join(command)}\n"
            f"  Description: {desc}"
        )
        logger.error(error_msg)
        raise SubprocessError(error_msg) from e


def run_piped_commands(
    commands: List[List[str]],
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[int] = None,
    description: Optional[str] = None,
) -> CommandResult:
    """
    Run multiple commands piped together.

    Example:
        run_piped_commands([
            ["git", "archive", "HEAD"],
            ["tar", "-x", "-C", "/tmp"]
        ])

    Args:
        commands: List of command lists to pipe together
        cwd: Working directory
        timeout: Total timeout for all commands
        description: Human-readable description

    Returns:
        CommandResult from the final command

    Raises:
        SubprocessError: If any command fails
    """
    if not commands:
        raise ValueError("No commands provided")

    if timeout is None:
        timeout = SUBPROCESS_DEFAULT_TIMEOUT

    desc = description or f"Piped: {' | '.join(' '.join(cmd) for cmd in commands)}"
    logger.debug(f"Running piped commands: {desc}")

    try:
        # Start first process
        processes = []
        prev_stdout = None

        for i, cmd in enumerate(commands):
            stdin = prev_stdout if i > 0 else None

            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdin=stdin,
                stdout=subprocess.PIPE if i < len(commands) - 1 else subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            processes.append(proc)
            prev_stdout = proc.stdout

        # Wait for all processes
        final_proc = processes[-1]
        stdout, stderr = final_proc.communicate(timeout=timeout)

        # Check all return codes
        for i, proc in enumerate(processes):
            proc.wait()
            if proc.returncode != 0:
                error_msg = (
                    f"Piped command failed at stage {i + 1}: {desc}\n"
                    f"  Failed command: {' '.join(commands[i])}\n"
                    f"  Return code: {proc.returncode}"
                )
                logger.error(error_msg)
                raise SubprocessError(error_msg)

        logger.debug(f"Piped commands succeeded: {desc}")
        return CommandResult(
            stdout=stdout,
            stderr=stderr,
            returncode=0,
            command=commands[-1],
        )

    except subprocess.TimeoutExpired as e:
        # Kill all processes
        for proc in processes:
            proc.kill()
        error_msg = f"Piped commands timed out after {timeout}s: {desc}"
        logger.error(error_msg)
        raise SubprocessError(error_msg) from e
