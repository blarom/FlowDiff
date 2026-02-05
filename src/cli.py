#!/usr/bin/env python3
"""
FlowDiff CLI - Function call tree visualizer for Python projects.

Usage:
    flowdiff snapshot <path>        # Visualize function call tree
    flowdiff snapshot <path> --port 9000  # Use custom port
"""

import sys
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from analyzer.call_tree_adapter import CallTreeAdapter, CallTreeNode
from web.server import start_server
from output.report_generator import (
    save_json_output,
    save_text_report,
    save_markdown_report,
    save_html_output
)

# Optional: config and LLM providers
try:
    from config.config_loader import load_config
    from analyzer.llm_providers import create_provider
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

app = typer.Typer(help="FlowDiff - Function call tree visualizer")
console = Console()


def serialize_tree_node(node: CallTreeNode) -> dict:
    """Convert CallTreeNode to JSON-serializable dict.

    Args:
        node: CallTreeNode to serialize

    Returns:
        Dictionary with function info and children
    """
    return {
        "function": {
            "name": node.function.name,
            "qualified_name": node.function.qualified_name,
            "file_path": node.function.file_path,
            "file_name": node.function.file_name,
            "line_number": node.function.line_number,
            "parameters": node.function.parameters,
            "return_type": node.function.return_type,
            "calls": node.function.calls,
            "called_by": node.function.called_by,
            "local_variables": node.function.local_variables,
            "is_entry_point": node.function.is_entry_point
        },
        "children": [serialize_tree_node(child) for child in node.children],
        "depth": node.depth
    }


def discover_python_files(root: Path) -> List[Path]:
    """Discover all Python files in a directory.

    Args:
        root: Root directory to search

    Returns:
        List of Python file paths
    """
    python_files = []

    # Patterns to exclude
    exclude_patterns = {
        '__pycache__',
        '.git',
        '.venv',
        'venv',
        '.tox',
        '.pytest_cache',
        '.mypy_cache',
        'build',
        'dist',
        '*.egg-info'
    }

    for path in root.rglob("*.py"):
        # Check if any parent directory matches exclude pattern
        if any(pattern in path.parts for pattern in exclude_patterns):
            continue
        python_files.append(path)

    return python_files


@app.command()
def snapshot(
    path: Path = typer.Argument(..., help="Path to Python project"),
    port: int = typer.Option(8080, "--port", "-p", help="Server port"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser automatically"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM-based entry point filtering"),
    llm_provider: Optional[str] = typer.Option(None, "--llm-provider", help="LLM provider: 'anthropic-api', 'claude-code-cli', 'auto'"),
    llm_model: Optional[str] = typer.Option(None, "--llm-model", help="LLM model name (provider-specific)"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Save reports to directory (default: ./output)")
):
    """
    Generate and visualize function call tree for a Python project.

    Examples:
        flowdiff snapshot /path/to/project
        flowdiff snapshot . --port 9000
        flowdiff snapshot ~/code/myproject --no-browser
        flowdiff snapshot . --no-llm  # Use only hard-coded rules
        flowdiff snapshot . --llm-provider claude-code-cli  # Use Claude CLI
        flowdiff snapshot . --llm-provider anthropic-api --llm-model claude-opus-4-5-20251101
        flowdiff snapshot . --output reports/  # Save to custom directory
    """
    # Resolve path
    project_path = path.resolve()

    if not project_path.exists():
        console.print(f"[red]Error: Path does not exist: {project_path}[/red]")
        raise typer.Exit(1)

    if not project_path.is_dir():
        console.print(f"[red]Error: Path is not a directory: {project_path}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]FlowDiff[/bold] - Function Call Tree Analyzer")
    console.print(f"[dim]Project: {project_path.name}[/dim]")
    console.print()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            # Step 1: Discover Python files
            task1 = progress.add_task("🔍 Discovering Python files...", total=None)
            python_files = discover_python_files(project_path)
            progress.update(task1, completed=True)
            console.print(f"   Found {len(python_files)} Python files")

            if len(python_files) == 0:
                console.print("[yellow]Warning: No Python files found[/yellow]")
                raise typer.Exit(0)

            # Step 2: Analyze functions and build call trees
            task2 = progress.add_task("📝 Analyzing functions and building call trees...", total=None)

            # Build call tree using new architecture
            adapter = CallTreeAdapter(project_path)
            trees = adapter.analyze_project()
            functions = adapter.get_functions_dict()

            progress.update(task2, completed=True)

            function_count = len(functions)
            entry_point_count = len(trees)
            console.print(f"   Found {function_count} functions, {entry_point_count} entry points")

            if function_count == 0:
                console.print("[yellow]Warning: No functions found[/yellow]")
                raise typer.Exit(0)

            # Step 3: Serialize tree data
            task3 = progress.add_task("🌐 Preparing visualization...", total=None)

            tree_data = {
                "trees": [serialize_tree_node(tree) for tree in trees],
                "metadata": {
                    "project": project_path.name,
                    "function_count": function_count,
                    "entry_point_count": entry_point_count
                }
            }

            progress.update(task3, completed=True)

            # Step 4: Save outputs
            # Default output directory: ./output in FlowDiff project
            if output_dir is None:
                flowdiff_root = Path(__file__).parent.parent
                output_dir = flowdiff_root / "output"

            output_dir = output_dir.resolve()
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate timestamp-based filenames
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            project_name = project_path.name

            # Save outputs
            json_path = output_dir / f"{project_name}_{timestamp}.json"
            text_path = output_dir / f"{project_name}_{timestamp}.txt"
            md_path = output_dir / f"{project_name}_{timestamp}.md"
            html_path = output_dir / f"{project_name}_{timestamp}.html"

            # Static files directory (for HTML generation)
            static_dir = Path(__file__).parent / "web" / "static"

            save_json_output(tree_data, json_path)
            save_text_report(tree_data, text_path)
            save_markdown_report(tree_data, md_path)
            save_html_output(tree_data, html_path, static_dir)

            console.print(f"\n[dim]📄 Reports saved to:[/dim]")
            console.print(f"[dim]   JSON:     {json_path}[/dim]")
            console.print(f"[dim]   Text:     {text_path}[/dim]")
            console.print(f"[dim]   Markdown: {md_path}[/dim]")
            console.print(f"[dim]   HTML:     {html_path}[/dim]")

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)

    # Start server
    console.print()
    console.print("[green]✓ Ready to visualize![/green]")
    console.print()

    try:
        start_server(tree_data, port=port, open_browser=not no_browser, html_path=str(html_path))
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Server error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def diff(
    path: Path = typer.Argument(".", help="Path to git repository"),
    before: str = typer.Option("HEAD", "--before", "-b", help="Before ref (commit, branch, tag)"),
    after: str = typer.Option("working", "--after", "-a", help="After ref (commit, branch, tag, or 'working')"),
    port: int = typer.Option(8080, "--port", "-p", help="Server port"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser automatically")
):
    """
    Show git diff visualization with before/after call trees.

    Compare any two git references (commits, branches, tags) or uncommitted changes.

    Examples:
        flowdiff diff                          # Uncommitted vs HEAD
        flowdiff diff --before HEAD~1          # Working directory vs previous commit
        flowdiff diff --before main --after dev # Compare branches
        flowdiff diff --before v1.0 --after v2.0 # Compare tags
        flowdiff diff /path/to/repo --port 9000
    """
    from analyzer.git.diff_analyzer import GitDiffAnalyzer

    # Resolve path
    project_path = path.resolve()

    if not project_path.exists():
        console.print(f"[red]Error: Path does not exist: {project_path}[/red]")
        raise typer.Exit(1)

    if not project_path.is_dir():
        console.print(f"[red]Error: Path is not a directory: {project_path}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]FlowDiff[/bold] - Git Diff Visualization")
    console.print(f"[dim]Project: {project_path.name}[/dim]")
    console.print()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            # Analyze diff
            task = progress.add_task("🔍 Analyzing diff...", total=None)

            analyzer = GitDiffAnalyzer(project_path)
            diff_result = analyzer.analyze_diff(before, after)

            progress.update(task, completed=True)

            # Display summary
            console.print(f"\n[bold]Diff Summary:[/bold]")
            console.print(f"[dim]Before: {diff_result.before_description}[/dim]")
            console.print(f"[dim]After:  {diff_result.after_description}[/dim]")
            console.print()
            console.print(f"[green]🟢 {diff_result.functions_added} functions added[/green]")
            console.print(f"[yellow]🟡 {diff_result.functions_modified} functions modified[/yellow]")
            console.print(f"[red]🔴 {diff_result.functions_deleted} functions deleted[/red]")

    except ValueError as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)

    # Start server
    console.print()
    console.print("[green]✓ Opening diff view...[/green]")
    console.print()

    # Create empty tree_data (not used for diff view)
    tree_data = {"trees": [], "metadata": {}}

    try:
        import webbrowser
        if not no_browser:
            url = f"http://localhost:{port}/diff.html"
            console.print(f"🌐 Opening browser at {url}")
            webbrowser.open(url)

        start_server(tree_data, port=port, open_browser=False, project_path=project_path)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Server error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def init(
    global_config: bool = typer.Option(False, "--global", "-g", help="Create config in home directory instead of current directory")
):
    """
    Initialize FlowDiff configuration.

    Creates a .flowdiff.yaml configuration file with default settings and helpful comments.

    Examples:
        flowdiff init           # Create .flowdiff.yaml in current directory
        flowdiff init --global  # Create .flowdiff.yaml in home directory
    """
    if not CONFIG_AVAILABLE:
        console.print("[red]Error: Configuration system not available[/red]")
        console.print("[dim]Install dependencies: pip install pyyaml[/dim]")
        raise typer.Exit(1)

    from config.config_loader import generate_sample_config

    # Determine config path
    if global_config:
        config_path = Path.home() / '.flowdiff.yaml'
    else:
        config_path = Path.cwd() / '.flowdiff.yaml'

    # Check if config already exists
    if config_path.exists():
        overwrite = typer.confirm(f"Config file already exists at {config_path}. Overwrite?")
        if not overwrite:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

    # Generate and write config
    config_content = generate_sample_config()
    with open(config_path, 'w') as f:
        f.write(config_content)

    console.print(f"[green]✓ Created configuration file: {config_path}[/green]")
    console.print()
    console.print("[dim]Edit the file to customize your settings.[/dim]")
    console.print("[dim]See documentation for all available options.[/dim]")


@app.command()
def version():
    """Show FlowDiff version."""
    console.print("FlowDiff v0.2.0 - Function Call Tree Visualizer")



def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
