"""Tests for import utilities."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from sqlalchemy import MetaData

from synq.utils.import_utils import import_metadata_from_path, validate_metadata_object


def test_import_metadata_from_path_invalid_format():
    """Test import_metadata_from_path with invalid format."""
    with pytest.raises(ValueError, match="Invalid metadata path format"):
        import_metadata_from_path("invalid_format")


def test_import_metadata_from_path_module_not_found():
    """Test import_metadata_from_path with non-existent module."""
    with pytest.raises(ImportError, match="Could not import module"):
        import_metadata_from_path("nonexistent_module:metadata")


def test_import_metadata_from_path_object_not_found():
    """Test import_metadata_from_path with non-existent object."""
    with pytest.raises(AttributeError, match="Object 'nonexistent' not found"):
        import_metadata_from_path("sys:nonexistent")


def test_import_metadata_from_path_success():
    """Test successful import of metadata object."""
    # Create a temporary module
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        module_file = temp_path / "test_module.py"

        # Write a test module with MetaData
        module_file.write_text("""
from sqlalchemy import MetaData
metadata_obj = MetaData()
""")

        # Add temp directory to path
        original_path = sys.path[:]
        sys.path.insert(0, str(temp_path))

        try:
            # Import should work
            metadata = import_metadata_from_path("test_module:metadata_obj")
            assert isinstance(metadata, MetaData)
        finally:
            # Restore original path
            sys.path[:] = original_path


def test_import_metadata_from_path_adds_current_dir():
    """Test that current directory is added to Python path."""
    with patch("sys.path", []) as mock_path:  # Empty path list
        with patch("importlib.import_module") as mock_import:
            mock_module = type("Module", (), {"metadata_obj": MetaData()})()
            mock_import.return_value = mock_module

            result = import_metadata_from_path("test:metadata_obj")

            # Should have added current directory to path
            assert len(mock_path) == 1
            assert isinstance(result, MetaData)


def test_validate_metadata_object_success():
    """Test validate_metadata_object with valid MetaData."""
    metadata = MetaData()
    # Should not raise any exception
    validate_metadata_object(metadata)


def test_validate_metadata_object_invalid_type():
    """Test validate_metadata_object with invalid object."""
    with pytest.raises(TypeError, match="Expected SQLAlchemy MetaData object"):
        validate_metadata_object("not_metadata")


def test_validate_metadata_object_none():
    """Test validate_metadata_object with None."""
    with pytest.raises(TypeError, match="Expected SQLAlchemy MetaData object"):
        validate_metadata_object(None)


def test_validate_metadata_object_other_types():
    """Test validate_metadata_object with various invalid types."""
    invalid_objects = [
        123,
        [],
        {},
        object(),
        "string",
    ]

    for obj in invalid_objects:
        with pytest.raises(TypeError, match="Expected SQLAlchemy MetaData object"):
            validate_metadata_object(obj)


def test_import_metadata_from_path_complex_module_path():
    """Test import with complex module path like package.subpackage:object."""
    # Create a nested package structure
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create package structure
        package_dir = temp_path / "test_package"
        package_dir.mkdir()
        (package_dir / "__init__.py").write_text("")

        subpackage_dir = package_dir / "subpackage"
        subpackage_dir.mkdir()
        (subpackage_dir / "__init__.py").write_text("")

        module_file = subpackage_dir / "models.py"
        module_file.write_text("""
from sqlalchemy import MetaData
metadata_obj = MetaData()
""")

        # Add temp directory to path
        original_path = sys.path[:]
        sys.path.insert(0, str(temp_path))

        try:
            # Import should work with complex path
            metadata = import_metadata_from_path(
                "test_package.subpackage.models:metadata_obj"
            )
            assert isinstance(metadata, MetaData)
        finally:
            # Restore original path
            sys.path[:] = original_path


def test_import_metadata_from_path_current_dir_already_in_path():
    """Test that current directory path addition is skipped if already present."""
    current_dir = str(Path.cwd())

    with patch("importlib.import_module") as mock_import:
        mock_module = type("Module", (), {"metadata_obj": MetaData()})()
        mock_import.return_value = mock_module

        # Current directory should already be in path in normal circumstances
        result = import_metadata_from_path("test:metadata_obj")
        assert isinstance(result, MetaData)
