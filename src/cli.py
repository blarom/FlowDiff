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
import os
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

# Global console for logging
console = Console()
log_file = None


def count_functions(nodes):
    """Count total functions in a list of tree nodes recursively."""
    count = 0
    for node in nodes:
        count += 1
        count += count_functions(node.children)
    return count


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
    output_dir: Path = typer.Option("./output", "--output", "-o", help="Save reports to directory (default: ./output)")
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
    global log_file

    # Resolve paths
    project_path = path.resolve()
    output_dir = output_dir.resolve()

    if not project_path.exists():
        console.print(f"[red]Error: Path does not exist: {project_path}[/red]")
        raise typer.Exit(1)

    if not project_path.is_dir():
        console.print(f"[red]Error: Path is not a directory: {project_path}[/red]")
        raise typer.Exit(1)

    # Setup output directory and logging
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "run.log"
    log_file = open(log_path, 'w', encoding='utf-8')

    def log_print(msg: str, style: str = ""):
        """Print to both console and log file."""
        if style:
            console.print(msg)
        else:
            console.print(msg)
        # Strip ANSI codes for log file
        import re
        clean_msg = re.sub(r'\[.*?\]', '', msg)  # Remove rich markup
        clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', clean_msg)  # Remove ANSI codes
        log_file.write(clean_msg + '\n')
        log_file.flush()

    log_print(f"\n[bold]FlowDiff[/bold] - Call Tree Analyzer with Diff Visualization")
    log_print(f"[dim]Project: {project_path.name}[/dim]")
    log_print(f"[dim]Output: {output_dir}[/dim]")
    log_print("")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            # Step 1: Analyze diff
            task1 = progress.add_task("🔍 Analyzing git diff...", total=None)

            debug_log_path = output_dir / "debug.log"
            analyzer = GitDiffAnalyzer(project_path, debug_log_path=debug_log_path)
            diff_result = analyzer.analyze_diff(before, after)

            progress.update(task1, completed=True)

            # Display summary
            log_print(f"\n[bold]Analysis Complete:[/bold]")
            log_print(f"[dim]Before: {diff_result.before_description}[/dim]")
            log_print(f"[dim]After:  {diff_result.after_description}[/dim]")
            log_print(f"[dim]Files changed: {len(diff_result.file_changes)}[/dim]")
            log_print("")

            total_changes = diff_result.functions_added + diff_result.functions_modified + diff_result.functions_deleted
            if total_changes == 0:
                log_print("[dim]ℹ️  No function changes detected[/dim]")
                if before == "HEAD" and after == "working":
                    log_print("[dim]   (Try --before HEAD~1 to compare against previous commit)[/dim]")
            else:
                log_print(f"[green]🟢 {diff_result.functions_added} functions added[/green]")
                log_print(f"[yellow]🟡 {diff_result.functions_modified} functions modified[/yellow]")
                log_print(f"[red]🔴 {diff_result.functions_deleted} functions deleted[/red]")

            # Save reports (always, not optional)
            task2 = progress.add_task("💾 Saving reports...", total=None)

            project_name = project_path.name

            # Build tree data from diff result (has changes marked)
            from datetime import datetime
            tree_data = {
                "trees": [_serialize_tree_node(tree) for tree in diff_result.after_tree],
                "metadata": {
                    "project": project_path.name,
                    "run_dir": str(Path.cwd()),
                    "input_path": str(project_path),
                    "function_count": count_functions(diff_result.after_tree),
                    "entry_point_count": len(diff_result.after_tree),
                    "before_ref": diff_result.before_ref,
                    "after_ref": diff_result.after_ref,
                    "functions_added": diff_result.functions_added,
                    "functions_modified": diff_result.functions_modified,
                    "functions_deleted": diff_result.functions_deleted,
                    "analysis_timestamp": datetime.now().isoformat()
                }
            }

            # Save outputs (no timestamps - files get overwritten)
            json_path = output_dir / f"{project_name}.json"
            text_path = output_dir / f"{project_name}.txt"
            md_path = output_dir / f"{project_name}.md"
            html_path = output_dir / f"{project_name}.html"

            static_dir = Path(__file__).parent / "web" / "static"

            save_json_output(tree_data, json_path)
            save_text_report(tree_data, text_path)
            save_markdown_report(tree_data, md_path)
            save_html_output(tree_data, html_path, static_dir)

            progress.update(task2, completed=True)

            log_print(f"\n[dim]📄 Reports saved:[/dim]")
            log_print(f"[dim]   JSON:     {json_path.name}[/dim]")
            log_print(f"[dim]   Text:     {text_path.name}[/dim]")
            log_print(f"[dim]   Markdown: {md_path.name}[/dim]")
            log_print(f"[dim]   HTML:     {html_path.name}[/dim]")
            log_print(f"[dim]   Log:      {log_path.name}[/dim]")
            log_print(f"[dim]   Debug:    {debug_log_path.name}[/dim]")

    except ValueError as e:
        log_print(f"\n[red]Error: {e}[/red]")
        if log_file:
            log_file.close()
        raise typer.Exit(1)
    except Exception as e:
        log_print(f"\n[red]Error: {e}[/red]")
        import traceback
        tb = traceback.format_exc()
        log_print(tb)
        if log_file:
            log_file.close()
        raise typer.Exit(1)

    # Start server
    log_print("")
    log_print("[green]✓ Preparing visualization data...[/green]")

    # Use the after_tree from diff_result (already has changes marked)
    trees = diff_result.after_tree

    tree_data = {
        "trees": [_serialize_tree_node(tree) for tree in trees],
        "metadata": {
            "project": project_path.name,
            "run_dir": str(Path.cwd()),
            "input_path": str(project_path),
            "function_count": count_functions(trees),
            "entry_point_count": len(trees),
            "before_ref": diff_result.before_ref,
            "after_ref": diff_result.after_ref,
            "functions_added": diff_result.functions_added,
            "functions_modified": diff_result.functions_modified,
            "functions_deleted": diff_result.functions_deleted
        }
    }

    log_print("[green]✓ Opening visualization...[/green]")
    log_print("")

    try:
        if not no_browser:
            url = f"http://localhost:{port}/diff.html"
            log_print(f"🌐 Opening browser at {url}")
            webbrowser.open(url)

        # Close log file before starting server
        if log_file:
            log_file.close()

        start_server(tree_data, port=port, open_browser=False, project_path=project_path)
    except KeyboardInterrupt:
        log_print("\n\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        log_print(f"\n[red]Server error: {e}[/red]")
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
            "local_variables": node.function.local_variables,
            "is_entry_point": node.function.is_entry_point,
            "has_changes": node.function.has_changes,
            "documentation": node.function.documentation or ""
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
