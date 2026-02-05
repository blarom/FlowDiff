"""Export framework (Phase 2)."""
from pathlib import Path
from analyzer.git.diff_analyzer import DiffResult

class HTMLExporter:
    """Export diff results to HTML."""

    def export(self, diff_result: DiffResult, output_path: Path) -> None:
        """Export diff result to standalone HTML file.

        Args:
            diff_result: The diff analysis result
            output_path: Path to save HTML file

        Raises:
            NotImplementedError: This feature is planned for Phase 2
        """
        raise NotImplementedError("HTML export coming in Phase 2")

class PDFExporter:
    """Export diff results to PDF."""

    def export(self, diff_result: DiffResult, output_path: Path) -> None:
        """Export diff result to PDF file.

        Args:
            diff_result: The diff analysis result
            output_path: Path to save PDF file

        Raises:
            NotImplementedError: This feature is planned for Phase 2
        """
        raise NotImplementedError("PDF export coming in Phase 2")
