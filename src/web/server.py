"""
FastAPI web server for FlowDiff visualization.

Serves the interactive call tree viewer and provides API endpoints for tree data.
"""

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pathlib import Path
import sys
import webbrowser
import uvicorn
import subprocess
import os
import shutil
from typing import Optional, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from analyzer.git.diff_analyzer import GitDiffAnalyzer, DiffResult
from analyzer.legacy import CallTreeNode


# Global state for tree data
_current_tree_data: Optional[Dict] = None
_saved_html_path: Optional[str] = None
_project_path: Optional[Path] = None


def create_app() -> FastAPI:
    """Create FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="FlowDiff",
        description="Function call tree visualizer",
        version="0.2.0"
    )

    # Get paths
    web_dir = Path(__file__).parent
    static_dir = web_dir / "static"

    # Add middleware to disable caching for static files (development mode)
    @app.middleware("http")
    async def add_no_cache_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Mount static files
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Serve main HTML page."""
        html_file = static_dir / "index.html"
        if not html_file.exists():
            raise HTTPException(status_code=404, detail="index.html not found")

        return html_file.read_text()

    @app.get("/api/tree")
    async def get_tree():
        """Get current call tree data.

        Returns:
            JSON tree data with function call hierarchy
        """
        if _current_tree_data is None:
            raise HTTPException(status_code=404, detail="No tree data loaded")

        return JSONResponse(_current_tree_data)

    @app.get("/api/saved-html-path")
    async def get_saved_html_path():
        """Get path to saved HTML file.

        Returns:
            JSON with saved HTML file path
        """
        return JSONResponse({
            "html_path": _saved_html_path,
            "file_url": f"file://{_saved_html_path}" if _saved_html_path else None
        })

    @app.get("/api/diff/{qualified_name:path}")
    async def get_function_diff(qualified_name: str):
        """Get diff for a specific function.

        Args:
            qualified_name: Qualified function name (e.g., "src.analyzer.StockAnalyzer.analyze")

        Returns:
            JSON with diff content and external viewer status
        """
        try:
            if _project_path is None:
                raise HTTPException(status_code=500, detail="Project path not set")

            if _current_tree_data is None:
                raise HTTPException(status_code=404, detail="No tree data loaded")

            # Find the function in the tree data
            func_info = _find_function_in_tree(qualified_name)
            if func_info is None:
                raise HTTPException(status_code=404, detail=f"Function {qualified_name} not found in tree")

            file_path = func_info["file_path"]

            # Always get diff content as fallback
            diff_content = _get_file_diff(file_path, _project_path)

            # Try to open in external diff viewer
            external_result = _open_external_diff(file_path, _project_path)

            return JSONResponse({
                "success": True,
                "method": "external" if external_result["success"] else "inline",
                "viewer": external_result.get("viewer"),
                "diff_content": diff_content,
                "file_path": file_path
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    @app.post("/api/diff")
    async def get_diff(request: Request):
        """Get diff between two git refs."""
        try:
            body = await request.json()
            before_ref = body.get("before", "HEAD")
            after_ref = body.get("after", "working")

            if _project_path is None:
                raise HTTPException(status_code=500, detail="Project path not set")

            analyzer = GitDiffAnalyzer(_project_path)
            diff_result = analyzer.analyze_diff(before_ref, after_ref)

            return JSONResponse(content=_serialize_diff_result(diff_result))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    @app.get("/diff.html")
    async def diff_page():
        """Serve diff visualization page."""
        html_path = static_dir / "diff.html"
        if not html_path.exists():
            raise HTTPException(status_code=404, detail="diff.html not found")
        return FileResponse(html_path)

    return app


def _serialize_diff_result(diff: DiffResult) -> dict:
    """Convert DiffResult to JSON."""
    return {
        "before_ref": diff.before_ref,
        "after_ref": diff.after_ref,
        "before_description": diff.before_description,
        "after_description": diff.after_description,
        "summary": {
            "added": diff.functions_added,
            "deleted": diff.functions_deleted,
            "modified": diff.functions_modified
        },
        "before_tree": [_serialize_tree_node(n) for n in diff.before_tree],
        "after_tree": [_serialize_tree_node(n) for n in diff.after_tree]
    }


def _serialize_tree_node(node: CallTreeNode) -> dict:
    """Convert CallTreeNode to JSON."""
    return {
        "function": {
            "name": node.function.name,
            "qualified_name": node.function.qualified_name,
            "file_path": node.function.file_path,
            "line_number": node.function.line_number,
            "has_changes": node.function.has_changes
        },
        "children": [_serialize_tree_node(c) for c in node.children],
        "is_expanded": node.is_expanded,
        "depth": node.depth
    }


def _find_function_in_tree(qualified_name: str) -> Optional[Dict]:
    """Find a function in the tree data by qualified name.

    Args:
        qualified_name: Qualified function name to search for

    Returns:
        Function info dict if found, None otherwise
    """
    if _current_tree_data is None:
        return None

    def search_tree(trees):
        for tree in trees:
            if tree["function"]["qualified_name"] == qualified_name:
                return tree["function"]
            # Search children
            result = search_tree(tree.get("children", []))
            if result:
                return result
        return None

    return search_tree(_current_tree_data.get("trees", []))


def _open_external_diff(file_path: str, project_path: Path) -> Dict:
    """Try to open diff in an external viewer.

    Tries in order:
    1. VS Code diff (if `code` is available)
    2. Difftastic (if `difft` is available)
    3. Git difftool (with configured or default tool)

    Args:
        file_path: Path to the file to diff
        project_path: Root path of the git repository

    Returns:
        Dict with "success" bool and "viewer" name
    """
    # Convert absolute path to relative path from project root
    try:
        rel_path = Path(file_path).relative_to(project_path)
    except ValueError:
        rel_path = file_path

    # Try VS Code - check if it exists first
    if shutil.which("code"):
        try:
            result = subprocess.run(
                ["code", "--diff", f"HEAD:{rel_path}", str(rel_path)],
                cwd=str(project_path),
                capture_output=True,
                timeout=2
            )
            if result.returncode == 0:
                return {"success": True, "viewer": "VS Code"}
        except (subprocess.TimeoutExpired, Exception):
            pass

    # Try Difftastic - check if it exists first
    if shutil.which("difft"):
        try:
            subprocess.Popen(
                ["difft", f"HEAD:{rel_path}", str(rel_path)],
                cwd=str(project_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return {"success": True, "viewer": "Difftastic"}
        except Exception:
            pass

    # Try git difftool - git should always be available
    try:
        subprocess.Popen(
            ["git", "difftool", "--no-prompt", "HEAD", "--", str(rel_path)],
            cwd=str(project_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return {"success": True, "viewer": "git difftool"}
    except Exception:
        pass

    return {"success": False, "viewer": None}


def _get_file_diff(file_path: str, project_path: Path) -> str:
    """Get raw diff content for a file.

    Args:
        file_path: Path to the file to diff
        project_path: Root path of the git repository

    Returns:
        Diff content as string
    """
    rel_path = Path(file_path).relative_to(project_path) if file_path.startswith(str(project_path)) else file_path

    try:
        result = subprocess.run(
            ["git", "diff", "HEAD", "--", str(rel_path)],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout or "No changes detected"
        else:
            return f"Error getting diff: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Timeout getting diff"
    except Exception as e:
        return f"Error: {str(e)}"


def set_tree_data(tree_data: Dict, html_path: Optional[str] = None, project_path: Optional[Path] = None):
    """Set the current tree data to be served.

    Args:
        tree_data: Tree data dictionary with function call hierarchy
        html_path: Path to saved HTML file (optional)
        project_path: Path to the project root (optional)
    """
    global _current_tree_data, _saved_html_path, _project_path
    _current_tree_data = tree_data
    _saved_html_path = html_path
    if project_path:
        _project_path = project_path


def start_server(tree_data: Dict, port: int = 8080, open_browser: bool = True, html_path: Optional[str] = None, project_path: Optional[Path] = None):
    """Start the web server and optionally open browser.

    Args:
        tree_data: Call tree data to visualize
        port: Port number (default: 8080)
        open_browser: Whether to auto-open browser (default: True)
        html_path: Path to saved HTML file (optional)
        project_path: Path to the project root (optional)
    """
    # Set tree data
    set_tree_data(tree_data, html_path, project_path)

    # Create app
    app = create_app()

    # Open browser
    if open_browser:
        url = f"http://localhost:{port}"
        print(f"\n🌐 Opening browser at {url}")
        webbrowser.open(url)

    # Start server
    print(f"🚀 Server running on http://localhost:{port}")
    print("Press Ctrl+C to stop\n")

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
