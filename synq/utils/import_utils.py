"""Utilities for importing Python modules and objects."""

import importlib
import sys
from pathlib import Path
from typing import Any


def import_metadata_from_path(metadata_path: str) -> Any:
    """
    Import SQLAlchemy MetaData object from a module path.

    Args:
        metadata_path: Path in format "module.submodule:object_name"

    Returns:
        The imported MetaData object

    Raises:
        ImportError: If module or object cannot be imported
        AttributeError: If object doesn't exist in module
        ValueError: If path format is invalid
    """
    if ":" not in metadata_path:
        raise ValueError(
            f"Invalid metadata path format: {metadata_path}\n"
            "Expected format: 'module.path:object_name'"
        )

    module_path, object_name = metadata_path.split(":", 1)

    # Add current directory to Python path if needed
    current_dir = Path.cwd()
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

    try:
        module = importlib.import_module(module_path)
        return getattr(module, object_name)
    except ImportError as e:
        raise ImportError(
            f"Could not import module '{module_path}': {e}\n"
            "Make sure the module exists and is in your Python path."
        ) from e
    except AttributeError as e:
        raise AttributeError(
            f"Object '{object_name}' not found in module '{module_path}': {e}\n"
            "Make sure the object name is correct."
        ) from e


def validate_metadata_object(metadata_obj: Any) -> None:
    """
    Validate that an object is a SQLAlchemy MetaData instance.

    Args:
        metadata_obj: Object to validate

    Raises:
        TypeError: If object is not a MetaData instance
    """
    from sqlalchemy import MetaData

    if not isinstance(metadata_obj, MetaData):
        raise TypeError(
            f"Expected SQLAlchemy MetaData object, got {type(metadata_obj)}\n"
            "Make sure your metadata_path points to a MetaData instance."
        )


def import_from_string(import_name: str) -> Any:
    """
    Import and return a module or object from a string.

    Args:
        import_name: String in format "module.path" or "module.path:object_name"

    Returns:
        The imported module or object
    """
    # If there's a colon, it's an object reference
    if ":" in import_name:
        return import_metadata_from_path(import_name)
    # Just import the module
    return importlib.import_module(import_name)
