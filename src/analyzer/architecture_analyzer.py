"""
Architecture Analyzer - LLM-powered architectural block identification.

Uses LLM to analyze codebase structure and identify 10-15 high-level
architectural components, their relationships, and function mappings.
"""
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import subprocess
from dataclasses import dataclass, asdict

from .llm_providers import LLMProvider, create_provider
from .legacy import CallTreeNode


@dataclass
class ArchitectureBlock:
    """Represents a high-level architectural component."""
    id: str
    label: str
    description: str
    functions: List[str]  # Qualified function names
    color: str


@dataclass
class BlockConnection:
    """Represents a dependency/flow between architectural blocks."""
    from_block: str
    to_block: str
    label: str


@dataclass
class ArchitectureDiagram:
    """Complete architecture diagram with blocks and connections."""
    blocks: List[ArchitectureBlock]
    connections: List[BlockConnection]


class ArchitectureAnalyzer:
    """Analyzes codebase to identify architectural blocks using LLM."""

    # Color palette for blocks
    COLORS = [
        "#3498db",  # Blue - API/Entry points
        "#2ecc71",  # Green - Core logic
        "#e74c3c",  # Red - External integrations
        "#f39c12",  # Orange - Data processing
        "#9b59b6",  # Purple - Storage/Cache
        "#1abc9c",  # Teal - Utilities
        "#34495e",  # Dark gray - Tests
        "#e67e22",  # Dark orange - Configuration
        "#16a085",  # Dark teal - Reporting
        "#c0392b",  # Dark red - Error handling
        "#8e44ad",  # Dark purple - Analytics
        "#27ae60",  # Dark green - Validation
        "#2980b9",  # Dark blue - Security
        "#d35400",  # Burnt orange - Monitoring
        "#7f8c8d",  # Gray - Other
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize architecture analyzer.

        Args:
            llm_provider: LLM provider for analysis. If None, uses auto-detect.
        """
        self.llm_provider = llm_provider

    def analyze(
        self,
        call_trees: List[CallTreeNode],
        project_path: Path
    ) -> ArchitectureDiagram:
        """
        Analyze codebase and generate architecture blocks.

        Args:
            call_trees: List of call tree root nodes
            project_path: Root path of the project

        Returns:
            ArchitectureDiagram with blocks and connections
        """
        # Extract all functions from call trees
        all_functions = self._extract_all_functions(call_trees)

        # Prepare data for LLM
        function_summary = self._summarize_functions(all_functions, project_path)

        # Use LLM to identify architectural blocks
        blocks_data = self._llm_identify_blocks(function_summary, project_path)

        # Parse LLM response into structured data
        diagram = self._parse_llm_response(blocks_data)

        return diagram

    def _extract_all_functions(self, trees: List[CallTreeNode]) -> List[Dict[str, Any]]:
        """
        Extract all functions from call trees recursively.

        Args:
            trees: List of call tree root nodes

        Returns:
            List of function dictionaries with metadata
        """
        functions = []

        def traverse(node: CallTreeNode):
            functions.append({
                "qualified_name": node.function.qualified_name,
                "name": node.function.name,
                "file_path": node.function.file_path,
                "file_name": node.function.file_name,
                "is_entry_point": node.function.is_entry_point,
                "calls": node.function.calls,
                "called_by": node.function.called_by,
            })

            for child in node.children:
                traverse(child)

        for tree in trees:
            traverse(tree)

        return functions

    def _summarize_functions(
        self,
        functions: List[Dict[str, Any]],
        project_path: Path
    ) -> str:
        """
        Create a summary of functions for LLM analysis.

        Args:
            functions: List of function metadata
            project_path: Root path of the project

        Returns:
            Formatted summary string
        """
        # Group by file
        by_file: Dict[str, List[Dict]] = {}
        for func in functions:
            file_path = func["file_path"]
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(func)

        # Create summary
        summary_lines = [
            f"Project: {project_path.name}",
            f"Total Functions: {len(functions)}",
            f"Files: {len(by_file)}",
            "",
            "Function Breakdown by File:",
            ""
        ]

        for file_path, funcs in sorted(by_file.items())[:50]:  # Limit to 50 files
            # Make path relative
            try:
                rel_path = Path(file_path).relative_to(project_path)
            except ValueError:
                rel_path = Path(file_path)

            summary_lines.append(f"  {rel_path} ({len(funcs)} functions):")

            for func in funcs[:10]:  # Limit to 10 functions per file
                entry_marker = " [ENTRY]" if func["is_entry_point"] else ""
                calls_count = len(func["calls"]) if func["calls"] else 0
                summary_lines.append(
                    f"    - {func['name']}{entry_marker} (calls {calls_count} functions)"
                )

            if len(funcs) > 10:
                summary_lines.append(f"    ... and {len(funcs) - 10} more")

        return "\n".join(summary_lines)

    def _llm_identify_blocks(
        self,
        function_summary: str,
        project_path: Path
    ) -> Dict[str, Any]:
        """
        Use LLM to identify architectural blocks.

        Args:
            function_summary: Summary of functions in the codebase
            project_path: Root path of the project

        Returns:
            Dict with blocks and connections
        """
        prompt = f"""Analyze this Python codebase and identify 10-15 high-level architectural blocks.

{function_summary}

Group functions into architectural components based on:
- Directory structure (e.g., src/web/, src/analyzer/, src/cli/)
- Functional purpose (e.g., "API Layer", "Code Analysis", "Git Integration", "Web Server", "Utilities")
- Common patterns in software architecture (presentation layer, business logic, data access, etc.)

Provide:
1. Block ID (lowercase_with_underscores, e.g., "api_layer")
2. Block label (human-readable, e.g., "API Layer")
3. Description (1-2 sentences about the block's purpose)
4. List of function prefixes that belong to this block (e.g., ["api::", "server::"])
5. Connections between blocks showing data flow or dependencies

Special handling:
- Group test files into a single "Tests" block
- Group small utility files into "Utilities" block
- Main entry points should map to their respective workflow blocks
- CLI commands go to "CLI Interface" block

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
    "blocks": [
        {{
            "id": "api_layer",
            "label": "API Layer",
            "description": "FastAPI endpoints for analysis requests",
            "function_prefixes": ["api::", "endpoints::"],
            "color": "#3498db"
        }}
    ],
    "connections": [
        {{
            "from": "api_layer",
            "to": "analyzer",
            "label": "analyzes code"
        }}
    ]
}}"""

        # Call LLM (use auto-detect if provider not set)
        if self.llm_provider is None:
            from .llm_providers import auto_detect_provider
            self.llm_provider = auto_detect_provider()

        response = self.llm_provider.complete(prompt, max_tokens=4000)

        # Parse JSON response
        try:
            # Try to extract JSON from response
            response_text = response.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])  # Remove first and last line
                if response_text.startswith("json"):
                    response_text = response_text[4:].strip()

            return json.loads(response_text)
        except json.JSONDecodeError as e:
            # Fallback: Return basic structure
            return {
                "blocks": [
                    {
                        "id": "main",
                        "label": "Main Codebase",
                        "description": "Primary application code",
                        "function_prefixes": [""],
                        "color": "#3498db"
                    }
                ],
                "connections": []
            }

    def _parse_llm_response(self, llm_data: Dict[str, Any]) -> ArchitectureDiagram:
        """
        Parse LLM response into structured ArchitectureDiagram.

        Args:
            llm_data: Raw data from LLM

        Returns:
            Structured ArchitectureDiagram
        """
        blocks = []
        for i, block_data in enumerate(llm_data.get("blocks", [])):
            # Assign color from palette
            color = block_data.get("color", self.COLORS[i % len(self.COLORS)])

            block = ArchitectureBlock(
                id=block_data["id"],
                label=block_data["label"],
                description=block_data["description"],
                functions=block_data.get("function_prefixes", []),
                color=color
            )
            blocks.append(block)

        connections = []
        for conn_data in llm_data.get("connections", []):
            conn = BlockConnection(
                from_block=conn_data["from"],
                to_block=conn_data["to"],
                label=conn_data.get("label", "")
            )
            connections.append(conn)

        return ArchitectureDiagram(blocks=blocks, connections=connections)

    def generate_svg_diagram(self, diagram: ArchitectureDiagram) -> str:
        """
        Generate SVG diagram using Graphviz.

        Args:
            diagram: Architecture diagram to visualize

        Returns:
            SVG string
        """
        # Generate DOT graph
        dot_lines = [
            "digraph Architecture {",
            "    rankdir=LR;",
            "    node [shape=box, style=filled, fontname=\"Arial\", fontsize=12];",
            "    edge [fontname=\"Arial\", fontsize=10];",
            "    bgcolor=transparent;",
            ""
        ]

        # Add blocks as nodes
        for block in diagram.blocks:
            # Escape quotes in label and description
            label = block.label.replace('"', '\\"')
            desc = block.description.replace('"', '\\"')

            # Create label with title and description
            node_label = f"{label}\\n{desc}"

            dot_lines.append(
                f'    {block.id} [label="{node_label}", '
                f'fillcolor="{block.color}", fontcolor="#ffffff"];'
            )

        dot_lines.append("")

        # Add connections as edges
        for conn in diagram.connections:
            label = conn.label.replace('"', '\\"')
            dot_lines.append(
                f'    {conn.from_block} -> {conn.to_block} [label="{label}"];'
            )

        dot_lines.append("}")

        dot_source = "\n".join(dot_lines)

        # Render to SVG using Graphviz
        try:
            result = subprocess.run(
                ["dot", "-Tsvg"],
                input=dot_source.encode(),
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.decode()
            else:
                # Fallback: return error message
                return f"<!-- Error rendering diagram: {result.stderr.decode()} -->"

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            # Graphviz not installed or timeout
            return f"<!-- Graphviz not available: {e} -->"

    def to_json(self, diagram: ArchitectureDiagram) -> str:
        """
        Convert diagram to JSON for web consumption.

        Args:
            diagram: Architecture diagram

        Returns:
            JSON string
        """
        return json.dumps({
            "blocks": [asdict(block) for block in diagram.blocks],
            "connections": [asdict(conn) for conn in diagram.connections]
        }, indent=2)
