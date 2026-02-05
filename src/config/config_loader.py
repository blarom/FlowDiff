"""
Configuration system for FlowDiff.

Supports configuration from:
1. Config file (.flowdiff.yaml in project root or home directory)
2. Environment variables
3. CLI arguments (override config file)
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM configuration."""
    # Provider type: 'anthropic-api', 'claude-code-cli', 'openai-api', 'auto'
    provider: str = 'auto'

    # Model name (provider-specific)
    model: Optional[str] = None

    # API key for API providers (or env var name)
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None

    # CLI command for CLI providers
    cli_command: str = 'claude'

    # Enable/disable LLM filtering
    enabled: bool = True


@dataclass
class FlowDiffConfig:
    """Complete FlowDiff configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Future: diff settings, visualization settings, etc.


def load_config_file(config_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file (if None, searches for .flowdiff.yaml)

    Returns:
        Config dict or None if not found
    """
    if config_path and config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}

    # Search for .flowdiff.yaml in current directory and parents
    current = Path.cwd()
    while current != current.parent:
        config_file = current / '.flowdiff.yaml'
        if config_file.exists():
            with open(config_file, 'r') as f:
                return yaml.safe_load(f) or {}
        current = current.parent

    # Check home directory
    home_config = Path.home() / '.flowdiff.yaml'
    if home_config.exists():
        with open(home_config, 'r') as f:
            return yaml.safe_load(f) or {}

    return None


def load_config(config_path: Optional[Path] = None) -> FlowDiffConfig:
    """
    Load FlowDiff configuration from file and environment.

    Priority (highest to lowest):
    1. Environment variables (FLOWDIFF_*)
    2. Config file (.flowdiff.yaml)
    3. Defaults

    Args:
        config_path: Optional path to config file

    Returns:
        FlowDiffConfig instance
    """
    # Start with defaults
    config = FlowDiffConfig()

    # Load from file
    file_config = load_config_file(config_path)
    if file_config:
        # LLM config
        if 'llm' in file_config:
            llm_config = file_config['llm']
            if 'provider' in llm_config:
                config.llm.provider = llm_config['provider']
            if 'model' in llm_config:
                config.llm.model = llm_config['model']
            if 'api_key' in llm_config:
                config.llm.api_key = llm_config['api_key']
            if 'api_key_env' in llm_config:
                config.llm.api_key_env = llm_config['api_key_env']
            if 'cli_command' in llm_config:
                config.llm.cli_command = llm_config['cli_command']
            if 'enabled' in llm_config:
                config.llm.enabled = llm_config['enabled']

    # Override with environment variables
    if os.environ.get('FLOWDIFF_LLM_PROVIDER'):
        config.llm.provider = os.environ['FLOWDIFF_LLM_PROVIDER']
    if os.environ.get('FLOWDIFF_LLM_MODEL'):
        config.llm.model = os.environ['FLOWDIFF_LLM_MODEL']
    if os.environ.get('FLOWDIFF_LLM_CLI_COMMAND'):
        config.llm.cli_command = os.environ['FLOWDIFF_LLM_CLI_COMMAND']
    if os.environ.get('FLOWDIFF_LLM_ENABLED'):
        config.llm.enabled = os.environ['FLOWDIFF_LLM_ENABLED'].lower() in ('true', '1', 'yes')

    # Resolve API key if api_key_env is set
    if config.llm.api_key_env and not config.llm.api_key:
        config.llm.api_key = os.environ.get(config.llm.api_key_env)

    return config


def generate_sample_config() -> str:
    """
    Generate sample .flowdiff.yaml configuration.

    Returns:
        YAML string with sample config and comments
    """
    return """# FlowDiff Configuration

# LLM Configuration (for entry point filtering)
llm:
  # Provider type:
  # - 'auto': Auto-detect (tries claude-code-cli, then anthropic-api)
  # - 'claude-code-cli': Use Claude Code CLI (corporate sessions)
  # - 'anthropic-api': Use Anthropic API (requires API key)
  # - 'openai-api': Use OpenAI API (requires API key, not yet implemented)
  provider: 'auto'

  # Model name (optional, uses provider default if not set)
  # Examples:
  # - Anthropic: 'claude-3-5-sonnet-20241022', 'claude-opus-4-5-20251101'
  # - Claude Code CLI: 'sonnet', 'opus', 'haiku'
  # - OpenAI: 'gpt-4', 'gpt-3.5-turbo'
  # model: 'claude-3-5-sonnet-20241022'

  # API key for API providers (not needed for CLI providers)
  # Option 1: Direct API key (not recommended, use env var instead)
  # api_key: 'sk-ant-...'

  # Option 2: Environment variable name (recommended)
  api_key_env: 'ANTHROPIC_API_KEY'

  # CLI command for CLI providers (default: 'claude')
  cli_command: 'claude'

  # Enable/disable LLM filtering (default: true)
  enabled: true

# Future: Add diff, visualization, and other settings here
"""
