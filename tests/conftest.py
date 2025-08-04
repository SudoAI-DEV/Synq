"""Pytest configuration and fixtures."""

import shutil
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table

from synq.core.config import SynqConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration."""
    return SynqConfig(
        metadata_path="tests.fixtures:test_metadata",
        db_uri="sqlite:///test.db",
        migrations_dir=str(temp_dir / "migrations"),
        snapshot_dir=str(temp_dir / "migrations" / "meta"),
    )


@pytest.fixture
def test_metadata():
    """Create test SQLAlchemy metadata."""
    metadata = MetaData()

    Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50), nullable=False),
        Column("email", String(50), unique=True),
    )

    return metadata


@pytest.fixture
def modified_metadata():
    """Create modified test SQLAlchemy metadata."""
    metadata = MetaData()

    # Modified users table
    Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(100), nullable=False),  # Changed length
        Column("email", String(50), unique=True),
        Column("created_at", String),  # New column
    )

    # New table
    Table(
        "posts",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(200), nullable=False),
        Column("user_id", Integer),
    )

    return metadata
