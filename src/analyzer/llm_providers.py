"""
LLM provider abstractions for FlowDiff.

Supports multiple LLM backends:
- Anthropic API (requires ANTHROPIC_API_KEY)
- Claude Code CLI (uses 'claude' command from corporate session)
- OpenAI API (requires OPENAI_API_KEY) - future
"""

import os
import json
import subprocess
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 4000) -> str:
        """
        Send a prompt to the LLM and get a response.

        Args:
            prompt: The prompt text
            max_tokens: Maximum tokens in response

        Returns:
            Response text from LLM

        Raises:
            Exception: If LLM call fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available (API key set, CLI installed, etc.)."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get human-readable name of this provider."""
        pass


class AnthropicAPIProvider(LLMProvider):
    """Anthropic API provider using anthropic Python package."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        """
        Initialize Anthropic API provider.

        Args:
            model: Model name (default: claude-3-5-sonnet-20241022)
            api_key: API key (if None, reads from ANTHROPIC_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set and no api_key provided")

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def complete(self, prompt: str, max_tokens: int = 4000) -> str:
        """Send prompt to Anthropic API."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        return response.content[0].text

    def is_available(self) -> bool:
        """Check if API key is set and anthropic package is installed."""
        try:
            import anthropic
            return bool(self.api_key)
        except ImportError:
            return False

    def get_name(self) -> str:
        return f"Anthropic API ({self.model})"


class ClaudeCodeCLIProvider(LLMProvider):
    """
    Claude Code CLI provider using subprocess.

    Uses the 'claude' command from Apple's internal Claude Code CLI.
    Works with corporate sessions without requiring an API key.
    """

    def __init__(self, cli_command: str = "claude", model: Optional[str] = None):
        """
        Initialize Claude Code CLI provider.

        Args:
            cli_command: Command to invoke (default: 'claude')
            model: Model name (optional, CLI uses session default)
        """
        self.cli_command = cli_command
        self.model = model

    def complete(self, prompt: str, max_tokens: int = 4000) -> str:
        """
        Send prompt to Claude Code CLI.

        Uses subprocess with stdin: echo "prompt" | claude
        """
        # Build command
        cmd = [self.cli_command]

        # Add model if specified
        if self.model:
            cmd.extend(['--model', self.model])

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )

            if result.returncode != 0:
                # Check if it's a port issue (common with Claude CLI)
                if "No available ports" in result.stderr:
                    raise Exception(
                        "Claude CLI failed to start proxy server (no available ports). "
                        "Try using --llm-provider anthropic-api or --no-llm instead."
                    )
                raise Exception(f"Claude CLI failed: {result.stderr}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise Exception("Claude CLI timed out after 60 seconds")
        except FileNotFoundError:
            raise Exception(f"Claude CLI command not found: {self.cli_command}")

    def is_available(self) -> bool:
        """Check if claude CLI is installed and accessible."""
        try:
            result = subprocess.run(
                [self.cli_command, '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_name(self) -> str:
        model_str = f" - {self.model}" if self.model else ""
        return f"Claude Code CLI ({self.cli_command}{model_str})"


class OpenAIAPIProvider(LLMProvider):
    """OpenAI API provider (future implementation)."""

    def __init__(self, model: str = "gpt-4", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        raise NotImplementedError("OpenAI provider not yet implemented")

    def complete(self, prompt: str, max_tokens: int = 4000) -> str:
        raise NotImplementedError("OpenAI provider not yet implemented")

    def is_available(self) -> bool:
        return False

    def get_name(self) -> str:
        return f"OpenAI API ({self.model})"


def create_provider(
    provider_type: str,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    cli_command: Optional[str] = None
) -> LLMProvider:
    """
    Factory function to create LLM provider.

    Args:
        provider_type: One of: 'anthropic-api', 'claude-code-cli', 'openai-api'
        model: Model name (provider-specific)
        api_key: API key for API providers
        cli_command: CLI command for CLI providers

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider_type is unknown
    """
    provider_type = provider_type.lower()

    if provider_type == 'anthropic-api':
        model = model or "claude-3-5-sonnet-20241022"
        return AnthropicAPIProvider(model=model, api_key=api_key)

    elif provider_type == 'claude-code-cli':
        cli_command = cli_command or "claude"
        return ClaudeCodeCLIProvider(cli_command=cli_command, model=model)

    elif provider_type == 'openai-api':
        model = model or "gpt-4"
        return OpenAIAPIProvider(model=model, api_key=api_key)

    else:
        raise ValueError(
            f"Unknown provider type: {provider_type}. "
            f"Valid options: 'anthropic-api', 'claude-code-cli', 'openai-api'"
        )


def auto_detect_provider() -> LLMProvider:
    """
    Auto-detect available LLM provider.

    Priority:
    1. Claude Code CLI (if 'claude' command available)
    2. Anthropic API (if ANTHROPIC_API_KEY set)
    3. OpenAI API (if OPENAI_API_KEY set)

    Returns:
        First available provider

    Raises:
        Exception: If no provider is available
    """
    # Try Claude Code CLI first (corporate environment)
    try:
        provider = ClaudeCodeCLIProvider()
        if provider.is_available():
            return provider
    except Exception:
        pass

    # Try Anthropic API
    try:
        provider = AnthropicAPIProvider()
        if provider.is_available():
            return provider
    except Exception:
        pass

    # No provider available
    raise Exception(
        "No LLM provider available. Options:\n"
        "1. Install Claude Code CLI (for corporate sessions)\n"
        "2. Set ANTHROPIC_API_KEY environment variable\n"
        "3. Set OPENAI_API_KEY environment variable"
    )
