"""
Unit tests for graph collapser module.

Tests filtering, grouping, custom rules, and node limit enforcement.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from graph.models import Graph, Node, Edge, NodeType, EdgeType
from graph.collapser import GraphCollapser
from graph.collapse_rules import CollapseRule, CollapseConfig
from config.default_rules import get_default_config, get_stockanalysis_config


class TestFilterExternal:
    """Test external dependency filtering."""

    def test_filter_external_removes_external_nodes(self):
        """Test that filter_external removes EXTERNAL nodes."""
        graph = Graph(root="/project")

        # Add MODULE nodes
        graph.add_node(Node(id="src.core", label="core", type=NodeType.MODULE, size=100))
        graph.add_node(Node(id="src.data", label="data", type=NodeType.MODULE, size=200))

        # Add EXTERNAL nodes
        graph.add_node(Node(id="pandas", label="pandas", type=NodeType.EXTERNAL, size=0))
        graph.add_node(Node(id="numpy", label="numpy", type=NodeType.EXTERNAL, size=0))

        # Add edges (including to external)
        graph.add_edge(Edge(source="src.core", target="src.data", type=EdgeType.IMPORT))
        graph.add_edge(Edge(source="src.data", target="pandas", type=EdgeType.IMPORT))
        graph.add_edge(Edge(source="src.data", target="numpy", type=EdgeType.IMPORT))

        # Filter
        config = CollapseConfig(filter_external=True)
        collapser = GraphCollapser(config)
        filtered = collapser.filter_external(graph)

        # Check results
        assert filtered.node_count() == 2  # Only MODULE nodes
        assert filtered.edge_count() == 1  # Only internal edge
        assert filtered.get_node("src.core") is not None
        assert filtered.get_node("src.data") is not None
        assert filtered.get_node("pandas") is None
        assert filtered.get_node("numpy") is None

    def test_filter_external_preserves_module_edges(self):
        """Test that internal edges are preserved."""
        graph = Graph(root="/project")

        # Create chain: mod_a → mod_b → mod_c
        graph.add_node(Node(id="mod_a", label="a", type=NodeType.MODULE, size=10))
        graph.add_node(Node(id="mod_b", label="b", type=NodeType.MODULE, size=20))
        graph.add_node(Node(id="mod_c", label="c", type=NodeType.MODULE, size=30))

        graph.add_edge(Edge(source="mod_a", target="mod_b", type=EdgeType.IMPORT, weight=2))
        graph.add_edge(Edge(source="mod_b", target="mod_c", type=EdgeType.IMPORT, weight=3))

        config = CollapseConfig()
        collapser = GraphCollapser(config)
        filtered = collapser.filter_external(graph)

        assert filtered.edge_count() == 2
        assert any(e.source == "mod_a" and e.target == "mod_b" for e in filtered.edges)
        assert any(e.source == "mod_b" and e.target == "mod_c" for e in filtered.edges)


class TestCustomRules:
    """Test custom collapsing rules."""

    def test_apply_custom_rules_simple(self):
        """Test applying a simple pattern-based rule."""
        graph = Graph(root="/project")

        # Add nodes matching pattern
        graph.add_node(Node(id="src.nodes.node1", label="node1", type=NodeType.MODULE, size=100))
        graph.add_node(Node(id="src.nodes.node2", label="node2", type=NodeType.MODULE, size=150))
        graph.add_node(Node(id="src.core", label="core", type=NodeType.MODULE, size=200))

        # Add edges
        graph.add_edge(Edge(source="src.core", target="src.nodes.node1", type=EdgeType.IMPORT))
        graph.add_edge(Edge(source="src.core", target="src.nodes.node2", type=EdgeType.IMPORT))

        # Create rule to collapse nodes
        rule = CollapseRule(
            pattern=r"src\.nodes\..*",
            target_name="src.all_nodes",
            target_label="All Nodes",
            priority=10
        )

        config = CollapseConfig(custom_rules=[rule])
        collapser = GraphCollapser(config)
        collapsed = collapser.apply_custom_rules(graph)

        # Should have 2 nodes: src.core and src.all_nodes
        assert collapsed.node_count() == 2
        assert collapsed.get_node("src.core") is not None
        assert collapsed.get_node("src.all_nodes") is not None
        assert collapsed.get_node("src.nodes.node1") is None
        assert collapsed.get_node("src.nodes.node2") is None

        # Check collapsed node properties
        all_nodes = collapsed.get_node("src.all_nodes")
        assert all_nodes.type == NodeType.FOLDER
        assert all_nodes.size == 250  # 100 + 150
        assert len(all_nodes.children) == 2

    def test_apply_custom_rules_priority(self):
        """Test that higher priority rules are applied first."""
        graph = Graph(root="/project")

        graph.add_node(Node(id="src.data.models.user", label="user", type=NodeType.MODULE, size=50))

        # Two rules that could match
        rule1 = CollapseRule(
            pattern=r"src\.data\..*",
            target_name="src.data_all",
            target_label="All Data",
            priority=5
        )

        rule2 = CollapseRule(
            pattern=r"src\.data\.models\..*",
            target_name="src.data.models_all",
            target_label="All Models",
            priority=10  # Higher priority
        )

        config = CollapseConfig(custom_rules=[rule1, rule2])
        collapser = GraphCollapser(config)
        collapsed = collapser.apply_custom_rules(graph)

        # Higher priority rule should win
        assert collapsed.get_node("src.data.models_all") is not None
        assert collapsed.get_node("src.data_all") is None


class TestGroupByDirectory:
    """Test directory-based grouping."""

    def test_group_by_directory_depth_2(self):
        """Test grouping at depth=2."""
        graph = Graph(root="/project")

        # Add modules with 3+ level paths
        graph.add_node(Node(id="src.data.extraction", label="extraction", type=NodeType.MODULE, size=100))
        graph.add_node(Node(id="src.data.computation", label="computation", type=NodeType.MODULE, size=150))
        graph.add_node(Node(id="src.core.metrics", label="metrics", type=NodeType.MODULE, size=200))

        config = CollapseConfig(directory_depth=2)
        collapser = GraphCollapser(config)
        grouped = collapser.group_by_directory(graph, depth=2)

        # Should create: src.data (folder), src.core (single module kept as-is)
        assert grouped.node_count() == 2

        # Check src.data folder
        data_folder = grouped.get_node("src.data")
        assert data_folder is not None
        assert data_folder.type == NodeType.FOLDER
        assert data_folder.size == 250  # 100 + 150
        assert len(data_folder.children) == 2

        # src.core.metrics has only one file at src.core level, so kept as MODULE
        core_metrics = grouped.get_node("src.core.metrics")
        assert core_metrics is not None
        assert core_metrics.type == NodeType.MODULE

    def test_group_by_directory_depth_1(self):
        """Test grouping at depth=1 (top-level only)."""
        graph = Graph(root="/project")

        graph.add_node(Node(id="src.data.extraction", label="extraction", type=NodeType.MODULE, size=100))
        graph.add_node(Node(id="src.core.metrics", label="metrics", type=NodeType.MODULE, size=200))
        graph.add_node(Node(id="lib.utils", label="utils", type=NodeType.MODULE, size=50))

        config = CollapseConfig(directory_depth=1)
        collapser = GraphCollapser(config)
        grouped = collapser.group_by_directory(graph, depth=1)

        # Should create: src (folder), lib (single module)
        assert grouped.node_count() == 2

        src_folder = grouped.get_node("src")
        assert src_folder is not None
        assert src_folder.type == NodeType.FOLDER
        assert src_folder.size == 300  # 100 + 200

    def test_group_by_directory_preserves_edges(self):
        """Test that edges are correctly routed through grouped folders."""
        graph = Graph(root="/project")

        # Create modules
        graph.add_node(Node(id="src.data.extraction", label="extraction", type=NodeType.MODULE, size=100))
        graph.add_node(Node(id="src.data.computation", label="computation", type=NodeType.MODULE, size=150))
        graph.add_node(Node(id="src.core.metrics", label="metrics", type=NodeType.MODULE, size=200))

        # extraction → computation (should become internal to src.data)
        graph.add_edge(Edge(source="src.data.extraction", target="src.data.computation", type=EdgeType.IMPORT))

        # computation → metrics (should become src.data → src.core.metrics)
        graph.add_edge(Edge(source="src.data.computation", target="src.core.metrics", type=EdgeType.IMPORT))

        config = CollapseConfig(directory_depth=2)
        collapser = GraphCollapser(config)
        grouped = collapser.group_by_directory(graph, depth=2)

        # Should have 1 edge: src.data → src.core.metrics
        # (internal edge within src.data folder is removed)
        assert grouped.edge_count() == 1
        edge = grouped.edges[0]
        assert edge.source == "src.data"
        assert edge.target == "src.core.metrics"


class TestEnforceNodeLimit:
    """Test node limit enforcement."""

    def test_enforce_node_limit_no_merge_if_under(self):
        """Test that nothing is merged if already under limit."""
        graph = Graph(root="/project")

        for i in range(5):
            graph.add_node(Node(id=f"module_{i}", label=f"mod{i}", type=NodeType.MODULE, size=100))

        config = CollapseConfig(max_nodes=10)
        collapser = GraphCollapser(config)
        limited = collapser.enforce_node_limit(graph, max_nodes=10)

        # Should be unchanged
        assert limited.node_count() == 5

    def test_enforce_node_limit_merges_folders(self):
        """Test that folders are merged when over limit."""
        graph = Graph(root="/project")

        # Create FOLDER nodes
        graph.add_node(Node(
            id="src.data",
            label="data",
            type=NodeType.FOLDER,
            children=["src.data.a", "src.data.b"],
            size=100
        ))

        graph.add_node(Node(
            id="src.core",
            label="core",
            type=NodeType.FOLDER,
            children=["src.core.x", "src.core.y"],
            size=150
        ))

        graph.add_node(Node(
            id="lib.utils",
            label="utils",
            type=NodeType.MODULE,
            size=50
        ))

        config = CollapseConfig(max_nodes=2)
        collapser = GraphCollapser(config)
        limited = collapser.enforce_node_limit(graph, max_nodes=2)

        # Should merge src.data and src.core into "src"
        assert limited.node_count() == 2
        assert limited.get_node("src") is not None or limited.get_node("lib.utils") is not None


class TestEndToEndCollapse:
    """Test full collapsing pipeline."""

    def test_collapse_full_pipeline(self):
        """Test complete collapsing workflow."""
        graph = Graph(root="/project")

        # Add internal modules
        graph.add_node(Node(id="src.data.extraction", label="extraction", type=NodeType.MODULE, size=100))
        graph.add_node(Node(id="src.data.computation", label="computation", type=NodeType.MODULE, size=150))
        graph.add_node(Node(id="src.core.metrics", label="metrics", type=NodeType.MODULE, size=200))

        # Add external dependencies
        graph.add_node(Node(id="pandas", label="pandas", type=NodeType.EXTERNAL, size=0))

        # Add edges
        graph.add_edge(Edge(source="src.data.extraction", target="src.data.computation", type=EdgeType.IMPORT))
        graph.add_edge(Edge(source="src.data.extraction", target="pandas", type=EdgeType.IMPORT))
        graph.add_edge(Edge(source="src.core.metrics", target="src.data.computation", type=EdgeType.IMPORT))

        config = CollapseConfig(
            max_nodes=30,
            directory_depth=2,
            filter_external=True
        )

        collapser = GraphCollapser(config)
        collapsed = collapser.collapse(graph)

        # Should filter external, then group by directory
        assert collapsed.get_node("pandas") is None  # External filtered
        assert collapsed.node_count() <= 30  # Under limit
        # Should have src.data folder and src.core.metrics
        assert collapsed.get_node("src.data") is not None or collapsed.get_node("src.core.metrics") is not None


class TestDefaultConfigs:
    """Test default configuration presets."""

    def test_default_config_has_rules(self):
        """Test that default config includes common rules."""
        config = get_default_config()

        assert config.max_nodes == 30
        assert config.directory_depth == 2
        assert config.filter_external is True
        assert len(config.custom_rules) > 0

    def test_stockanalysis_config(self):
        """Test StockAnalysis-specific configuration."""
        config = get_stockanalysis_config()

        assert config.max_nodes == 20  # Aggressive
        # Should have rule for decision nodes
        assert any("decision_engine.nodes" in r.pattern for r in config.custom_rules)
