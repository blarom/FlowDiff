"""Check the full call chain: analyze.sh → api.analyze → analyze_stock"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from analyzer.call_tree_adapter import CallTreeAdapter


def print_tree(node, indent=0, max_depth=5):
    """Print tree structure recursively."""
    if indent > max_depth:
        return

    prefix = "  " * indent
    print(f"{prefix}- {node.function.qualified_name} ({node.function.language})")

    for child in node.children:
        print_tree(child, indent + 1, max_depth)


def main():
    project_root = Path("/Users/barlarom/PycharmProjects/Main/StockAnalysis")

    adapter = CallTreeAdapter(project_root)
    trees = adapter.analyze_project()

    # Find analyze.sh tree
    for tree in trees:
        if tree.function.qualified_name == "scripts.analyze":
            print("=== Full call tree from scripts.analyze ===\n")
            print_tree(tree, max_depth=6)
            break


if __name__ == "__main__":
    main()
