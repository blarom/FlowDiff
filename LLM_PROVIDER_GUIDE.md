# FlowDiff LLM Provider System

## Overview

FlowDiff supports multiple LLM providers for intelligent entry point filtering, allowing you to use either API-based services or corporate CLI tools.

## Supported Providers

### 1. Claude Code CLI (Recommended for Corporate Users)

Uses the `claude` command from your corporate Claude Code session. **No API key required!**

**Advantages:**
- ✅ No API key needed
- ✅ Works with corporate/Apple sessions
- ✅ Uses your existing Claude Code access
- ✅ No additional cost

**Requirements:**
- Claude Code CLI installed and accessible
- Active corporate session

**Usage:**
```bash
# Auto-detect (tries CLI first)
python src/cli.py snapshot /path/to/project

# Explicitly use CLI
python src/cli.py snapshot /path/to/project --llm-provider claude-code-cli

# Specify model
python src/cli.py snapshot /path/to/project --llm-provider claude-code-cli --llm-model sonnet
```

**Available Models:**
- `sonnet` (default)
- `opus`
- `haiku`

### 2. Anthropic API

Uses the official Anthropic Python API. **Requires API key.**

**Advantages:**
- ✅ Works anywhere (not limited to corporate network)
- ✅ Programmatic access
- ✅ Full control over model selection

**Requirements:**
- `ANTHROPIC_API_KEY` environment variable set
- `anthropic` Python package installed

**Usage:**
```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Use Anthropic API
python src/cli.py snapshot /path/to/project --llm-provider anthropic-api

# Specify model
python src/cli.py snapshot /path/to/project --llm-provider anthropic-api --llm-model claude-opus-4-5-20251101
```

**Available Models:**
- `claude-3-5-sonnet-20241022` (default)
- `claude-opus-4-5-20251101`
- `claude-3-haiku-20240307`

### 3. Auto-Detection (Default)

Automatically detects available provider:
1. Tries Claude Code CLI first (if `claude` command available)
2. Falls back to Anthropic API (if `ANTHROPIC_API_KEY` set)
3. Disables LLM filtering if neither available

**Usage:**
```bash
# Auto-detect (recommended)
python src/cli.py snapshot /path/to/project
```

---

## Configuration

### Option 1: CLI Arguments (Quick)

Override configuration per run:

```bash
# Use Claude Code CLI
python src/cli.py snapshot . --llm-provider claude-code-cli

# Use Anthropic API with specific model
python src/cli.py snapshot . --llm-provider anthropic-api --llm-model claude-opus-4-5-20251101

# Disable LLM filtering
python src/cli.py snapshot . --no-llm
```

### Option 2: Config File (Persistent)

Create `.flowdiff.yaml` for persistent configuration.

**Initialize config:**
```bash
# In project directory
python src/cli.py init

# Global config (home directory)
python src/cli.py init --global
```

**Sample `.flowdiff.yaml`:**

```yaml
# LLM Configuration (for entry point filtering)
llm:
  # Provider type: 'auto', 'claude-code-cli', 'anthropic-api'
  provider: 'claude-code-cli'

  # Model name (optional, uses provider default if not set)
  model: 'sonnet'

  # CLI command for CLI providers
  cli_command: 'claude'

  # Enable/disable LLM filtering
  enabled: true
```

### Option 3: Environment Variables

Set environment variables for one-time configuration:

```bash
# Provider type
export FLOWDIFF_LLM_PROVIDER="claude-code-cli"

# Model
export FLOWDIFF_LLM_MODEL="sonnet"

# CLI command
export FLOWDIFF_LLM_CLI_COMMAND="claude"

# Enable/disable
export FLOWDIFF_LLM_ENABLED="true"

# Run FlowDiff
python src/cli.py snapshot /path/to/project
```

### Configuration Priority

Highest to lowest:
1. CLI arguments (`--llm-provider`, `--llm-model`, `--no-llm`)
2. Environment variables (`FLOWDIFF_LLM_*`)
3. Config file (`.flowdiff.yaml`)
4. Defaults (auto-detection)

---

## Examples

### Example 1: Corporate User (Apple)

**Scenario:** You're using Claude Code at Apple, no API key.

```bash
# Auto-detect (will find Claude Code CLI)
python src/cli.py snapshot /Users/barlarom/PycharmProjects/Main/StockAnalysis

# Output:
# 📝 Analyzing functions and building call trees...
#    Auto-detected: Claude Code CLI (claude)
# 🤖 Using Claude Code CLI (claude) to filter 15 entry point candidates...
# ✓ LLM selected 8 entry points
```

### Example 2: External User (With API Key)

**Scenario:** You're outside corporate network, have Anthropic API key.

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Auto-detect (will find API key)
python src/cli.py snapshot /path/to/project

# Or explicitly use API
python src/cli.py snapshot /path/to/project --llm-provider anthropic-api
```

### Example 3: Mixed Configuration

**Scenario:** Default to CLI, but override for specific runs.

**Create config:**
```yaml
# .flowdiff.yaml
llm:
  provider: 'claude-code-cli'
  model: 'sonnet'
```

**Override when needed:**
```bash
# Normal run (uses CLI from config)
python src/cli.py snapshot .

# Override to use API for this run
python src/cli.py snapshot . --llm-provider anthropic-api

# Disable LLM for this run (fast, no filtering)
python src/cli.py snapshot . --no-llm
```

### Example 4: CI/CD Pipeline

**Scenario:** Running FlowDiff in automated environment.

```bash
# Disable LLM filtering (fast, deterministic)
python src/cli.py snapshot . --no-llm --no-browser

# Or use API if available
export ANTHROPIC_API_KEY="${CI_ANTHROPIC_KEY}"
python src/cli.py snapshot . --llm-provider anthropic-api --no-browser
```

---

## Troubleshooting

### "No LLM provider available"

**Cause:** Neither CLI nor API key detected.

**Fix:**
```bash
# Option 1: Use Claude Code CLI
claude --version  # Check if installed

# Option 2: Set API key
export ANTHROPIC_API_KEY="your-key"

# Option 3: Disable LLM filtering
python src/cli.py snapshot . --no-llm
```

### "Claude CLI command not found"

**Cause:** `claude` command not in PATH.

**Fix:**
```bash
# Check where claude is installed
which claude

# If in custom location, configure:
python src/cli.py snapshot . --llm-provider claude-code-cli # Custom command not yet supported via CLI
```

Or create config:
```yaml
llm:
  provider: 'claude-code-cli'
  cli_command: '/path/to/claude'
```

### "Warning: Failed to create LLM provider"

**Cause:** Configuration error or provider unavailable.

**Fix:** Check error message and verify:
- API key is correct (for anthropic-api)
- CLI is installed (for claude-code-cli)
- Model name is valid for chosen provider

**Fallback:** FlowDiff automatically falls back to hard-coded rules if provider fails.

---

## Cost Comparison

### Claude Code CLI
- **Cost:** Free (uses corporate session)
- **Performance:** Fast (local CLI)
- **Availability:** Corporate network only

### Anthropic API
- **Cost:** ~$0.01-0.02 per analysis (Sonnet 3.5)
- **Performance:** Fast (API call)
- **Availability:** Anywhere with internet

### No LLM (--no-llm)
- **Cost:** Free
- **Performance:** Fastest (no API call)
- **Availability:** Anywhere
- **Accuracy:** Lower (hard-coded rules only)

---

## Advanced: Custom CLI Command

If your Claude CLI has a different name or custom wrapper:

**Config file:**
```yaml
llm:
  provider: 'claude-code-cli'
  cli_command: 'my-custom-claude'  # Or full path
```

**Environment variable:**
```bash
export FLOWDIFF_LLM_CLI_COMMAND="my-custom-claude"
```

---

## Summary

**For Apple/Corporate Users:**
- ✅ Use Claude Code CLI (auto-detected, no setup needed)
- ✅ No API key required
- ✅ Just run: `python src/cli.py snapshot /path/to/project`

**For External Users:**
- ✅ Get Anthropic API key from https://console.anthropic.com/
- ✅ Set `ANTHROPIC_API_KEY` environment variable
- ✅ Run: `python src/cli.py snapshot /path/to/project`

**For Everyone:**
- ✅ Use `--no-llm` to disable LLM filtering (fast, deterministic)
- ✅ Use `--llm-provider` and `--llm-model` to override configuration
- ✅ Create `.flowdiff.yaml` for persistent settings
