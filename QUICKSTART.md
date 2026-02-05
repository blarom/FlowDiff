# FlowDiff - Quick Start Guide

## Running FlowDiff (Current Setup)

FlowDiff is not yet installed as a package, so you run it directly with Python.

### Prerequisites

```bash
cd /Users/barlarom/PycharmProjects/Main/FlowDiff
pip install -r requirements.txt
```

### Basic Usage

```bash
# Analyze a project (auto-detects LLM provider)
python src/cli.py snapshot /path/to/project

# Analyze current directory
python src/cli.py snapshot .

# Analyze StockAnalysis project
cd /Users/barlarom/PycharmProjects/Main
python FlowDiff/src/cli.py snapshot StockAnalysis/
```

### LLM Provider Options

#### Option 1: Claude Code CLI (Recommended for Apple Users)

**No API key needed!** Uses your corporate Claude Code session.

```bash
# Auto-detect (will use Claude CLI if available)
python src/cli.py snapshot /path/to/project

# Explicitly use Claude CLI
python src/cli.py snapshot /path/to/project --llm-provider claude-code-cli
```

**Check if Claude CLI is available:**
```bash
claude --version
```

#### Option 2: Anthropic API

Requires API key:

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Run with API
python src/cli.py snapshot /path/to/project --llm-provider anthropic-api
```

#### Option 3: No LLM (Fastest)

Uses only hard-coded rules:

```bash
python src/cli.py snapshot /path/to/project --no-llm
```

### Common Commands

```bash
# Help
python src/cli.py --help
python src/cli.py snapshot --help

# Custom port
python src/cli.py snapshot . --port 9000

# Don't open browser
python src/cli.py snapshot . --no-browser

# Generate config file
python src/cli.py init

# Version
python src/cli.py version
```

### Configuration

Create `.flowdiff.yaml` for persistent settings:

```bash
python src/cli.py init
```

Example config:
```yaml
llm:
  provider: 'claude-code-cli'  # or 'anthropic-api' or 'auto'
  model: 'sonnet'              # optional
  cli_command: 'claude'        # CLI command
  enabled: true                # enable/disable LLM filtering
```

### Expected Output

```
FlowDiff - Function Call Tree Analyzer
Project: StockAnalysis

🔍 Discovering Python files...
   Found 70 Python files
📝 Analyzing functions and building call trees...
   Auto-detected: Claude Code CLI (claude)
🤖 Using Claude Code CLI (claude) to filter 15 entry point candidates...
✓ LLM selected 8 entry points

   Found 250 functions, 8 entry points
🌐 Preparing visualization...

✓ Ready to visualize!

Server running at http://localhost:8080
Press Ctrl+C to stop server.
```

Browser will open showing interactive function call tree.

### Testing on StockAnalysis

```bash
cd /Users/barlarom/PycharmProjects/Main

# With Claude Code CLI (auto-detected)
python FlowDiff/src/cli.py snapshot StockAnalysis/

# With Anthropic API
export ANTHROPIC_API_KEY="your-key"
python FlowDiff/src/cli.py snapshot StockAnalysis/ --llm-provider anthropic-api

# Without LLM (fast)
python FlowDiff/src/cli.py snapshot StockAnalysis/ --no-llm
```

### Troubleshooting

**"No LLM provider available"**
- Check if `claude` command works: `claude --version`
- Or set API key: `export ANTHROPIC_API_KEY="your-key"`
- Or disable LLM: `--no-llm`

**"claude: command not found"**
- Claude CLI not installed or not in PATH
- Use API instead: `--llm-provider anthropic-api`
- Or disable LLM: `--no-llm`

**Import errors**
- Install dependencies: `pip install -r requirements.txt`
- Make sure you're in FlowDiff directory when running

### Next Steps

See full documentation:
- `LLM_PROVIDER_GUIDE.md` - Detailed LLM configuration guide
- `ENTRY_POINT_RULES.md` - How entry point detection works
- `LLM_FILTERING_IMPLEMENTATION.md` - Implementation details
