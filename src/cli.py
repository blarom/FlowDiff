#!/usr/bin/env python3
"""
FlowDiff CLI - Multi-language call tree analyzer with git diff visualization.

Usage:
    flowdiff <path>                    # Analyze with default options
    flowdiff <path> --before HEAD~1    # Compare against previous commit
    flowdiff <path> --llm-provider claude-code-cli  # Use LLM filtering
"""

import sys
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import webbrowser

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from analyzer.git.diff_analyzer import GitDiffAnalyzer
from analyzer.call_tree_adapter import CallTreeAdapter
from web.server import start_server
from output.report_generator import (
    save_json_output,
    save_text_report,
    save_markdown_report,
    save_html_output
)

app = typer.Typer(help="FlowDiff - Multi-language call tree analyzer with diff visualization")
console = Console()


@app.command()
def analyze(
    path: Path = typer.Argument(".", help="Path to git repository"),
    before: str = typer.Option("HEAD", "--before", "-b", help="Before ref (commit, branch, tag)"),
    after: str = typer.Option("working", "--after", "-a", help="After ref (commit, branch, tag, or 'working')"),
    port: int = typer.Option(8080, "--port", "-p", help="Server port"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser automatically"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Disable LLM-based entry point filtering"),
    llm_provider: Optional[str] = typer.Option(None, "--llm-provider", help="LLM provider: 'anthropic-api', 'claude-code-cli', 'auto'"),
    llm_model: Optional[str] = typer.Option(None, "--llm-model", help="LLM model name (provider-specific)"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Save reports to directory (default: ./output)")
):
    """
    Analyze codebase and visualize call tree with git diff highlighting.

    Shows unified view with:
    - Full call tree (left pane)
    - Change highlighting (functions that changed between refs)
    - Interactive exploration

    Examples:
        flowdiff analyze .                         # Current working directory
        flowdiff analyze ../MyProject              # Specific project
        flowdiff analyze . --before HEAD~1         # Compare vs previous commit
        flowdiff analyze . --before main --after dev  # Compare branches
        flowdiff analyze . --llm-provider claude-code-cli  # Use LLM filtering
        flowdiff analyze . --output reports/       # Save to custom directory
    """
    # Resolve path
    project_path = path.resolve()

    if not project_path.exists():
        console.print(f"[red]Error: Path does not exist: {project_path}[/red]")
        raise typer.Exit(1)

    if not project_path.is_dir():
        console.print(f"[red]Error: Path is not a directory: {project_path}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]FlowDiff[/bold] - Call Tree Analyzer with Diff Visualization")
    console.print(f"[dim]Project: {project_path.name}[/dim]")
    console.print()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            # Step 1: Analyze diff
            task1 = progress.add_task("🔍 Analyzing git diff...", total=None)

            analyzer = GitDiffAnalyzer(project_path)
            diff_result = analyzer.analyze_diff(before, after)

            progress.update(task1, completed=True)

            # Display summary
            console.print(f"\n[bold]Analysis Complete:[/bold]")
            console.print(f"[dim]Before: {diff_result.before_description}[/dim]")
            console.print(f"[dim]After:  {diff_result.after_description}[/dim]")
            console.print()
            console.print(f"[green]🟢 {diff_result.functions_added} functions added[/green]")
            console.print(f"[yellow]🟡 {diff_result.functions_modified} functions modified[/yellow]")
            console.print(f"[red]🔴 {diff_result.functions_deleted} functions deleted[/red]")

            # Step 2: Save outputs (optional)
            if output_dir:
                task2 = progress.add_task("💾 Saving reports...", total=None)

                output_dir = output_dir.resolve()
                output_dir.mkdir(parents=True, exist_ok=True)

                # Generate timestamp-based filenames
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                project_name = project_path.name

                # Build tree data for reports
                adapter = CallTreeAdapter(project_path)
                trees = adapter.analyze_project()

                tree_data = {
                    "trees": [_serialize_tree_node(tree) for tree in trees],
                    "metadata": {
                        "project": project_path.name,
                        "before_ref": diff_result.before_ref,
                        "after_ref": diff_result.after_ref,
                        "functions_added": diff_result.functions_added,
                        "functions_modified": diff_result.functions_modified,
                        "functions_deleted": diff_result.functions_deleted
                    }
                }

                # Save outputs
                json_path = output_dir / f"{project_name}_{timestamp}.json"
                text_path = output_dir / f"{project_name}_{timestamp}.txt"
                md_path = output_dir / f"{project_name}_{timestamp}.md"
                html_path = output_dir / f"{project_name}_{timestamp}.html"

                static_dir = Path(__file__).parent / "web" / "static"

                save_json_output(tree_data, json_path)
                save_text_report(tree_data, text_path)
                save_markdown_report(tree_data, md_path)
                save_html_output(tree_data, html_path, static_dir)

                progress.update(task2, completed=True)

                console.print(f"\n[dim]📄 Reports saved to:[/dim]")
                console.print(f"[dim]   JSON:     {json_path}[/dim]")
                console.print(f"[dim]   Text:     {text_path}[/dim]")
                console.print(f"[dim]   Markdown: {md_path}[/dim]")
                console.print(f"[dim]   HTML:     {html_path}[/dim]")

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
    console.print("[green]✓ Opening visualization...[/green]")
    console.print()

    # Create minimal tree_data (server needs it for legacy compatibility)
    tree_data = {"trees": [], "metadata": {}}

    try:
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


def _serialize_tree_node(node) -> dict:
    """Convert CallTreeNode to JSON-serializable dict."""
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
            "is_entry_point": node.function.is_entry_point,
            "has_changes": node.function.has_changes
        },
        "children": [_serialize_tree_node(child) for child in node.children],
        "depth": node.depth
    }


@app.command()
def version():
    """Show FlowDiff version."""
    console.print("FlowDiff v0.3.0 - Multi-language Call Tree Analyzer with Diff Visualization")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
