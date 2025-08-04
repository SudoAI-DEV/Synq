"""
Synq - A modern, snapshot-based database migration tool for SQLAlchemy.

Synq brings the fast, offline-first workflow of tools like Drizzle ORM
to the Python and SQLAlchemy ecosystem.
"""

__version__ = "0.0.1"
__author__ = "Synq Contributors"
__license__ = "MIT"

from synq.core.config import SynqConfig
from synq.core.migration import MigrationManager
from synq.core.snapshot import SnapshotManager

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "SynqConfig",
    "SnapshotManager",
    "MigrationManager",
]
