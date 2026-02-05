"""Test script to verify analyze_stock has children."""

from pathlib import Path
from src.analyzer.orchestrator import FlowDiffOrchestrator


def main():
    project_root = Path("/Users/barlarom/PycharmProjects/Main/StockAnalysis")

    orchestrator = FlowDiffOrchestrator(project_root)
    symbol_tables = orchestrator.analyze()

    # Find analyze_stock function
    python_table = symbol_tables.get("python")
    if python_table:
        analyze_stock = python_table.get_symbol("src.analyzer.analyze_stock")

        if analyze_stock:
            print("\n=== analyze_stock Symbol ===")
            print(f"Name: {analyze_stock.name}")
            print(f"Qualified name: {analyze_stock.qualified_name}")
            print(f"File: {analyze_stock.file_path}:{analyze_stock.line_number}")
            print(f"\nRaw calls ({len(analyze_stock.raw_calls)}):")
            for call in analyze_stock.raw_calls[:10]:
                print(f"  - {call}")
            print(f"\nResolved calls ({len(analyze_stock.resolved_calls)}):")
            for call in analyze_stock.resolved_calls[:10]:
                print(f"  - {call}")

            # Check metadata
            print(f"\nMetadata:")
            print(f"  Parameters: {analyze_stock.metadata.get('parameters')}")
            print(f"  Local bindings: {analyze_stock.metadata.get('local_bindings')}")
        else:
            print("analyze_stock not found!")

            # Try to find it with different name
            print("\nAll symbols with 'analyze' in name:")
            for symbol in python_table.get_all_symbols():
                if 'analyze' in symbol.qualified_name.lower():
                    print(f"  - {symbol.qualified_name}")

    # Also check for StockAnalyzer class
    python_table = symbol_tables.get("python")
    if python_table:
        print("\n=== StockAnalyzer Class ===")
        if hasattr(python_table, 'classes'):
            stock_analyzer = python_table.classes.get("StockAnalyzer")
            if stock_analyzer:
                print(f"Found class: {stock_analyzer.qualified_name}")
                print(f"Methods ({len(stock_analyzer.methods)}):")
                for method_name, method_symbol in list(stock_analyzer.methods.items())[:5]:
                    print(f"  - {method_name}: {method_symbol.qualified_name}")
            else:
                print("StockAnalyzer class not found")
                print(f"Available classes: {list(python_table.classes.keys())[:10]}")


if __name__ == "__main__":
    main()
