"""Test the new adapter integration."""

from pathlib import Path
import sys
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from analyzer.call_tree_adapter import CallTreeAdapter


def main():
    project_root = Path("/Users/barlarom/PycharmProjects/Main/StockAnalysis")

    print("Creating adapter...")
    adapter = CallTreeAdapter(project_root)

    print("\nRunning analysis...")
    trees = adapter.analyze_project()

    print(f"\nFound {len(trees)} entry points")

    # Check analyze.sh
    for tree in trees:
        if "analyze" in tree.function.qualified_name and tree.function.language == "shell":
            print(f"\n=== {tree.function.qualified_name} ===")
            print(f"Language: {tree.function.language}")
            print(f"Calls: {tree.function.calls}")
            print(f"Children: {len(tree.children)}")

            if tree.children:
                print("\nChildren:")
                for child in tree.children:
                    print(f"  - {child.function.qualified_name}")
                    print(f"    Children: {len(child.children)}")

    # Check analyze_stock
    functions = adapter.get_functions_dict()
    analyze_stock = functions.get("src.analyzer.analyze_stock")
    if analyze_stock:
        print(f"\n=== src.analyzer.analyze_stock ===")
        print(f"Calls: {analyze_stock.calls}")
        print(f"Called by: {analyze_stock.called_by}")

        # Find it in trees
        for tree in trees:
            if tree.function.qualified_name == "src.analyzer.analyze_stock":
                print(f"Children in tree: {len(tree.children)}")
                for child in tree.children[:5]:
                    print(f"  - {child.function.qualified_name}")


if __name__ == "__main__":
    main()
