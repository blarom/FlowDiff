"""
Unit tests for graph builder module.

Tests graph construction from parsed files, edge creation, and external dependency handling.
"""

from pathlib import Path
import tempfile
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser.models import FileMetadata, Import
from graph.builder import GraphBuilder
from graph.models import Graph, Node, Edge, NodeType, EdgeType


class TestGraphBuilder:
    """Test basic graph building functionality."""

    def test_build_graph_single_file(self):
        """Test building graph from single file with no imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create simple FileMetadata with no imports
            metadata = FileMetadata(
                path=project_root / "test.py",
                module_name="test",
                imports=[],
                functions=["foo"],
                classes=["Bar"],
                lines_of_code=10,
                is_test=False
            )

            builder = GraphBuilder(project_root)
            graph = builder.build([metadata])

            # Verify graph structure
            assert graph.node_count() == 1
            assert graph.edge_count() == 0

            # Verify node properties
            node = graph.get_node("test")
            assert node is not None
            assert node.id == "test"
            assert node.type == NodeType.MODULE
            assert node.size == 10
            assert node.metadata == metadata

    def test_build_graph_with_imports(self):
        """Test building graph with import relationships between files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create two files: file_a imports file_b
            metadata_a = FileMetadata(
                path=project_root / "file_a.py",
                module_name="file_a",
                imports=[
                    Import(module="file_b", is_relative=False, relative_level=0, line=1)
                ],
                functions=[],
                classes=[],
                lines_of_code=5,
                is_test=False
            )

            metadata_b = FileMetadata(
                path=project_root / "file_b.py",
                module_name="file_b",
                imports=[],
                functions=[],
                classes=[],
                lines_of_code=8,
                is_test=False
            )

            builder = GraphBuilder(project_root)
            graph = builder.build([metadata_a, metadata_b])

            # Verify graph structure
            assert graph.node_count() == 2
            assert graph.edge_count() == 1

            # Verify nodes exist
            assert graph.get_node("file_a") is not None
            assert graph.get_node("file_b") is not None

            # Verify edge
            edges = graph.edges
            assert len(edges) == 1
            assert edges[0].source == "file_a"
            assert edges[0].target == "file_b"
            assert edges[0].type == EdgeType.IMPORT
            assert edges[0].weight == 1

    def test_multiple_imports_same_module(self):
        """Test that multiple imports to same module increment edge weight."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # File A imports file B twice
            metadata_a = FileMetadata(
                path=project_root / "file_a.py",
                module_name="file_a",
                imports=[
                    Import(module="file_b.foo", is_relative=False, relative_level=0, line=1),
                    Import(module="file_b.bar", is_relative=False, relative_level=0, line=2),
                ],
                functions=[],
                classes=[],
                lines_of_code=5,
                is_test=False
            )

            metadata_b = FileMetadata(
                path=project_root / "file_b.py",
                module_name="file_b",
                imports=[],
                functions=[],
                classes=[],
                lines_of_code=8,
                is_test=False
            )

            builder = GraphBuilder(project_root)
            graph = builder.build([metadata_a, metadata_b])

            # Should have 2 edges: file_a → file_b.foo and file_a → file_b.bar
            # These are different targets (file_b.foo vs file_b.bar)
            assert graph.edge_count() == 2

    def test_external_dependency_handling(self):
        """Test that external dependencies create EXTERNAL nodes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # File imports external library (pandas)
            metadata = FileMetadata(
                path=project_root / "file_a.py",
                module_name="file_a",
                imports=[
                    Import(module="pandas", is_relative=False, relative_level=0, line=1),
                    Import(module="numpy", is_relative=False, relative_level=0, line=2),
                ],
                functions=[],
                classes=[],
                lines_of_code=5,
                is_test=False
            )

            builder = GraphBuilder(project_root)
            graph = builder.build([metadata])

            # Should have 3 nodes: file_a (MODULE), pandas (EXTERNAL), numpy (EXTERNAL)
            assert graph.node_count() == 3

            # Verify file_a is MODULE
            node_a = graph.get_node("file_a")
            assert node_a.type == NodeType.MODULE

            # Verify pandas is EXTERNAL
            node_pandas = graph.get_node("pandas")
            assert node_pandas is not None
            assert node_pandas.type == NodeType.EXTERNAL
            assert node_pandas.metadata is None

            # Verify numpy is EXTERNAL
            node_numpy = graph.get_node("numpy")
            assert node_numpy is not None
            assert node_numpy.type == NodeType.EXTERNAL

            # Should have 2 edges: file_a → pandas, file_a → numpy
            assert graph.edge_count() == 2

    def test_graph_metadata(self):
        """Test that graph metadata is populated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            metadata_a = FileMetadata(
                path=project_root / "file_a.py",
                module_name="file_a",
                imports=[
                    Import(module="file_b", is_relative=False, relative_level=0, line=1),
                    Import(module="pandas", is_relative=False, relative_level=0, line=2),
                ],
                functions=[],
                classes=[],
                lines_of_code=5,
                is_test=False
            )

            metadata_b = FileMetadata(
                path=project_root / "file_b.py",
                module_name="file_b",
                imports=[],
                functions=[],
                classes=[],
                lines_of_code=8,
                is_test=False
            )

            builder = GraphBuilder(project_root)
            graph = builder.build([metadata_a, metadata_b])

            # Check metadata
            assert graph.metadata["total_files"] == 2
            assert graph.metadata["total_modules"] == 2  # file_a, file_b
            assert graph.metadata["total_external"] == 1  # pandas
            assert graph.metadata["total_edges"] == 2
            assert graph.metadata["project_root"] == str(project_root)


class TestGraphBuilderDiscovery:
    """Test file discovery functionality."""

    def test_discover_python_files(self):
        """Test discovering Python files in a directory tree."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Create directory structure
            src_dir = project_root / "src"
            src_dir.mkdir()
            data_dir = src_dir / "data"
            data_dir.mkdir()

            # Create Python files
            (project_root / "root.py").write_text("pass\n")
            (src_dir / "main.py").write_text("pass\n")
            (data_dir / "extraction.py").write_text("pass\n")

            # Create files that should be ignored
            pycache_dir = src_dir / "__pycache__"
            pycache_dir.mkdir()
            (pycache_dir / "cached.py").write_text("pass\n")

            venv_dir = project_root / "venv"
            venv_dir.mkdir()
            (venv_dir / "lib.py").write_text("pass\n")

            builder = GraphBuilder(project_root)
            files = builder.discover_python_files(project_root)

            # Should find 3 Python files (root.py, main.py, extraction.py)
            # Should NOT find cached.py or lib.py
            assert len(files) == 3

            file_names = {f.name for f in files}
            assert "root.py" in file_names
            assert "main.py" in file_names
            assert "extraction.py" in file_names
            assert "cached.py" not in file_names
            assert "lib.py" not in file_names

    def test_discover_python_files_empty_directory(self):
        """Test discovering files in empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            builder = GraphBuilder(project_root)
            files = builder.discover_python_files(project_root)

            assert len(files) == 0


class TestGraphBuilderEndToEnd:
    """Test end-to-end graph building from directory."""

    def test_build_from_directory(self):
        """Test complete pipeline from directory to graph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            src_dir = project_root / "src"
            src_dir.mkdir()

            # Create file_a.py that imports file_b
            file_a = src_dir / "file_a.py"
            file_a.write_text(
                "from src.file_b import helper\n"
                "\n"
                "def main():\n"
                "    pass\n"
            )

            # Create file_b.py with a helper function
            file_b = src_dir / "file_b.py"
            file_b.write_text(
                "def helper():\n"
                "    pass\n"
            )

            # Build graph from directory
            builder = GraphBuilder(project_root)
            graph = builder.build_from_directory(src_dir)

            # Verify graph was built
            assert graph.node_count() >= 2  # At least file_a and file_b

            # Verify nodes exist
            node_a = graph.get_node("src.file_a")
            node_b = graph.get_node("src.file_b")

            assert node_a is not None
            assert node_b is not None
            assert node_a.type == NodeType.MODULE
            assert node_b.type == NodeType.MODULE

            # Verify edge exists
            assert graph.edge_count() >= 1

    def test_build_from_directory_empty(self):
        """Test building from directory with no Python files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            empty_dir = project_root / "empty"
            empty_dir.mkdir()

            builder = GraphBuilder(project_root)
            graph = builder.build_from_directory(empty_dir)

            # Should return empty graph
            assert graph.node_count() == 0
            assert graph.edge_count() == 0
