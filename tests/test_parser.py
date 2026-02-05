"""
Unit tests for Python parser module.

Tests import extraction, function/class extraction, and import resolution.
"""

import tempfile
from pathlib import Path
import pytest
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parser.python_parser import (
    extract_imports,
    extract_functions,
    extract_classes,
    count_lines_of_code,
    parse_file
)
from parser.import_resolver import resolve_import, path_to_module_name
from parser.models import Import


class TestExtractImports:
    """Test import extraction from Python source files."""

    def test_extract_imports_absolute(self):
        """Test extraction of absolute import statements."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("import pandas as pd\n")
            f.write("import numpy\n")
            temp_path = f.name

        try:
            imports = extract_imports(temp_path)

            assert len(imports) == 2

            # Check first import: pandas as pd
            assert imports[0].module == "pandas"
            assert imports[0].alias == "pd"
            assert imports[0].is_relative is False
            assert imports[0].relative_level == 0
            assert imports[0].line == 1

            # Check second import: numpy
            assert imports[1].module == "numpy"
            assert imports[1].alias is None
            assert imports[1].is_relative is False
            assert imports[1].relative_level == 0
            assert imports[1].line == 2
        finally:
            Path(temp_path).unlink()

    def test_extract_imports_from(self):
        """Test extraction of 'from X import Y' statements."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("from src.core import constants\n")
            f.write("from typing import List, Dict\n")
            temp_path = f.name

        try:
            imports = extract_imports(temp_path)

            assert len(imports) == 3

            # Check: from src.core import constants
            assert imports[0].module == "src.core.constants"
            assert imports[0].is_relative is False

            # Check: from typing import List
            assert imports[1].module == "typing.List"
            assert imports[1].is_relative is False

            # Check: from typing import Dict
            assert imports[2].module == "typing.Dict"
            assert imports[2].is_relative is False
        finally:
            Path(temp_path).unlink()

    def test_extract_imports_relative_single_dot(self):
        """Test extraction of relative imports with single dot (same directory)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("from .schemas import MetricValue\n")
            f.write("from . import helper\n")
            temp_path = f.name

        try:
            imports = extract_imports(temp_path)

            assert len(imports) == 2

            # Check: from .schemas import MetricValue
            assert imports[0].module == "schemas.MetricValue"
            assert imports[0].is_relative is True
            assert imports[0].relative_level == 1
            assert imports[0].line == 1

            # Check: from . import helper
            assert imports[1].module == ".helper"
            assert imports[1].is_relative is True
            assert imports[1].relative_level == 1
        finally:
            Path(temp_path).unlink()

    def test_extract_imports_relative_double_dot(self):
        """Test extraction of relative imports with double dot (parent directory)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("from ..models import Node\n")
            f.write("from ...core.metrics import METRICS\n")
            temp_path = f.name

        try:
            imports = extract_imports(temp_path)

            assert len(imports) == 2

            # Check: from ..models import Node
            assert imports[0].module == "models.Node"
            assert imports[0].is_relative is True
            assert imports[0].relative_level == 2

            # Check: from ...core.metrics import METRICS
            assert imports[1].module == "core.metrics.METRICS"
            assert imports[1].is_relative is True
            assert imports[1].relative_level == 3
        finally:
            Path(temp_path).unlink()

    def test_extract_imports_malformed_file(self):
        """Test that malformed Python files return empty list gracefully."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("this is not valid python syntax {\n")
            temp_path = f.name

        try:
            imports = extract_imports(temp_path)
            # Should return empty list, not crash
            assert imports == []
        finally:
            Path(temp_path).unlink()


class TestExtractFunctionsAndClasses:
    """Test extraction of functions and classes."""

    def test_extract_functions(self):
        """Test extraction of top-level function names."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def foo():\n    pass\n")
            f.write("def bar():\n    pass\n")
            f.write("class MyClass:\n    def method(self):\n        pass\n")
            temp_path = f.name

        try:
            functions = extract_functions(temp_path)

            # Should only extract top-level functions, not methods
            assert len(functions) == 2
            assert "foo" in functions
            assert "bar" in functions
            assert "method" not in functions
        finally:
            Path(temp_path).unlink()

    def test_extract_classes(self):
        """Test extraction of top-level class names."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("class Foo:\n    pass\n")
            f.write("class Bar:\n    pass\n")
            f.write("def func():\n    class Nested:\n        pass\n")
            temp_path = f.name

        try:
            classes = extract_classes(temp_path)

            # Should only extract top-level classes, not nested
            assert len(classes) == 2
            assert "Foo" in classes
            assert "Bar" in classes
            assert "Nested" not in classes
        finally:
            Path(temp_path).unlink()


class TestLinesOfCode:
    """Test line counting functionality."""

    def test_count_lines_of_code(self):
        """Test counting non-empty lines."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("import pandas\n")
            f.write("\n")  # Empty line
            f.write("# Comment\n")
            f.write("def foo():\n")
            f.write("    pass\n")
            f.write("   \n")  # Whitespace-only line
            f.write("bar = 42\n")
            temp_path = f.name

        try:
            loc = count_lines_of_code(temp_path)
            # Should count: import, comment, def, pass, bar = 5 lines
            # Should not count: empty lines, whitespace-only lines
            assert loc == 5
        finally:
            Path(temp_path).unlink()


class TestImportResolution:
    """Test import resolution functionality."""

    def test_resolve_absolute_import(self):
        """Test that absolute imports are unchanged."""
        import_obj = Import(
            module="pandas",
            is_relative=False,
            relative_level=0
        )

        result = resolve_import(
            import_obj,
            current_module="src.data.extraction",
            project_root=Path("/project")
        )

        assert result == "pandas"

    def test_resolve_relative_import_same_dir(self):
        """Test resolving relative import in same directory (single dot)."""
        import_obj = Import(
            module="schemas.MetricValue",
            is_relative=True,
            relative_level=1
        )

        result = resolve_import(
            import_obj,
            current_module="src.data.extraction_layer",
            project_root=Path("/project")
        )

        # src.data.extraction_layer → src.data + .schemas → src.data.schemas
        assert result == "src.data.schemas.MetricValue"

    def test_resolve_relative_import_parent_dir(self):
        """Test resolving relative import in parent directory (double dot)."""
        import_obj = Import(
            module="core.metrics.METRICS",
            is_relative=True,
            relative_level=2
        )

        result = resolve_import(
            import_obj,
            current_module="src.data.extraction_layer",
            project_root=Path("/project")
        )

        # src.data.extraction_layer → src.data → go up 1 → src + core.metrics
        assert result == "src.core.metrics.METRICS"

    def test_resolve_relative_import_grandparent_dir(self):
        """Test resolving relative import in grandparent directory (triple dot)."""
        import_obj = Import(
            module="utils.helpers",
            is_relative=True,
            relative_level=3
        )

        result = resolve_import(
            import_obj,
            current_module="src.data.extraction.layer",
            project_root=Path("/project")
        )

        # src.data.extraction.layer → src.data.extraction → go up 2 → src + utils.helpers
        assert result == "src.utils.helpers"


class TestPathToModuleName:
    """Test path-to-module-name conversion."""

    def test_path_to_module_name_simple(self):
        """Test converting file path to module name."""
        file_path = Path("/project/src/data/extraction_layer.py")
        project_root = Path("/project")

        result = path_to_module_name(file_path, project_root)

        assert result == "src.data.extraction_layer"

    def test_path_to_module_name_root_file(self):
        """Test file at project root."""
        file_path = Path("/project/analyzer.py")
        project_root = Path("/project")

        result = path_to_module_name(file_path, project_root)

        assert result == "analyzer"

    def test_path_to_module_name_init_file(self):
        """Test __init__.py file handling."""
        file_path = Path("/project/src/data/__init__.py")
        project_root = Path("/project")

        result = path_to_module_name(file_path, project_root)

        # Should be src.data, not src.data.__init__
        assert result == "src.data"


class TestParseFile:
    """Test the complete parse_file function."""

    def test_parse_file_complete(self):
        """Test parsing a complete Python file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            src_dir = project_root / "src"
            src_dir.mkdir()

            test_file = src_dir / "test_module.py"
            test_file.write_text(
                "import pandas as pd\n"
                "from typing import List\n"
                "\n"
                "def foo():\n"
                "    pass\n"
                "\n"
                "class Bar:\n"
                "    pass\n"
            )

            metadata = parse_file(test_file, project_root)

            # Check module name
            assert metadata.module_name == "src.test_module"

            # Check path
            assert metadata.path == test_file

            # Check imports
            assert len(metadata.imports) == 2
            assert metadata.imports[0].module == "pandas"
            assert metadata.imports[1].module == "typing.List"

            # Check functions
            assert len(metadata.functions) == 1
            assert "foo" in metadata.functions

            # Check classes
            assert len(metadata.classes) == 1
            assert "Bar" in metadata.classes

            # Check LOC (should be 8 total lines, 6 non-empty)
            assert metadata.lines_of_code == 6

            # Check is_test flag (should be False for non-test file)
            assert metadata.is_test is False

    def test_parse_file_test_detection(self):
        """Test detection of test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            # Test file starting with test_
            test_file1 = project_root / "test_foo.py"
            test_file1.write_text("pass\n")

            metadata1 = parse_file(test_file1, project_root)
            assert metadata1.is_test is True

            # Test file in tests/ directory
            tests_dir = project_root / "tests"
            tests_dir.mkdir()
            test_file2 = tests_dir / "bar.py"
            test_file2.write_text("pass\n")

            metadata2 = parse_file(test_file2, project_root)
            assert metadata2.is_test is True
