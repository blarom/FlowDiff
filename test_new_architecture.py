"""Test script for new multi-language architecture."""

from pathlib import Path
from src.analyzer.orchestrator import FlowDiffOrchestrator


def main():
    # Test on StockAnalysis project
    project_root = Path("/Users/barlarom/PycharmProjects/Main/StockAnalysis")

    # Run analysis
    orchestrator = FlowDiffOrchestrator(project_root)
    symbol_tables = orchestrator.analyze()

    # Display results
    print("\n=== Results ===\n")

    # Entry points
    entry_points = orchestrator.get_entry_points(symbol_tables)
    print(f"Entry points: {len(entry_points)}")
    for ep in entry_points[:5]:  # Show first 5
        print(f"  - {ep.qualified_name} ({ep.language})")
        if ep.resolved_calls:
            print(f"    Calls: {ep.resolved_calls[:3]}")  # Show first 3 calls

    print()

    # Symbol counts
    for lang, table in symbol_tables.items():
        print(f"{lang} symbols: {len(table)}")
        # Show some symbols
        for symbol in list(table.get_all_symbols())[:3]:
            print(f"  - {symbol.qualified_name}")
            if symbol.resolved_calls:
                print(f"    → {symbol.resolved_calls[:2]}")

    print()

    # Check specific case: analyze.sh → api.analyze
    shell_table = symbol_tables.get("shell")
    if shell_table:
        analyze_script = shell_table.get_symbol("scripts.analyze")
        if analyze_script:
            print("=== analyze.sh Resolution ===")
            print(f"Raw calls: {analyze_script.raw_calls}")
            print(f"Resolved calls: {analyze_script.resolved_calls}")


if __name__ == "__main__":
    main()
