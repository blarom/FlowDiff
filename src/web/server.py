"""
FastAPI web server for FlowDiff visualization.

Serves the interactive call tree viewer and provides API endpoints for tree data.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pathlib import Path
import sys
import webbrowser
import uvicorn
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
