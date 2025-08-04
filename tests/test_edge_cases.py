"""Tests for edge cases and error conditions."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table

from synq.core.config import SynqConfig
from synq.core.diff import SchemaDiffer
from synq.core.migration import MigrationManager
from synq.core.naming import MigrationNamer
from synq.core.snapshot import (
    ColumnSnapshot,
    SchemaSnapshot,
    SnapshotManager,
    TableSnapshot,
)


def test_schema_differ_fallback_string_representation():
    """Test the fallback string representation in MigrationOperation."""
    from synq.core.diff import MigrationOperation, OperationType

    # Create operation with unknown operation type (this tests the fallback)
    operation = MigrationOperation(
        operation_type=OperationType.CREATE_TABLE,  # Use valid type but mock unknown behavior
        table_name="test_table",
    )

    # Patch the operation type to simulate unknown type
    with patch.object(operation, "operation_type") as mock_op_type:
        mock_op_type.value = "unknown_operation"
        result = str(operation)
        assert "unknown_operation test_table" in result


def test_snapshot_manager_handle_malformed_snapshot_files():
    """Test handling of malformed snapshot files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = SnapshotManager(config)

        # Create malformed snapshot file
        malformed_file = manager.snapshot_path / "0001_snapshot.json"
        malformed_file.write_text("invalid json content {{{")

        # Should handle gracefully and return None
        snapshot = manager.load_snapshot(1)
        assert snapshot is None


def test_migration_namer_edge_case_sanitization():
    """Test edge cases in migration name sanitization."""
    from synq.core.diff import MigrationOperation, OperationType

    namer = MigrationNamer()

    # Test with only special characters
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE,
            table_name="___---!!!",
            object_name=None,
        )
    ]

    # Test with actual implementation
    name = namer.generate_name(operations)

    # Should generate a valid name even with special characters
    assert isinstance(name, str)
    assert len(name) > 0
    # Should sanitize the table name
    assert "create_" in name and "_table" in name


def test_migration_namer_analyze_operations():
    """Test operation analysis in MigrationNamer."""
    from synq.core.diff import MigrationOperation, OperationType

    namer = MigrationNamer()

    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="users"
        ),
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="posts"
        ),
    ]

    analysis = namer._analyze_operations(operations)

    assert analysis.operation_counts[OperationType.CREATE_TABLE] == 2
    assert analysis.operation_counts[OperationType.ADD_COLUMN] == 1
    assert "users" in analysis.table_names
    assert "posts" in analysis.table_names


def test_migration_namer_get_primary_operation():
    """Test primary operation detection."""
    from synq.core.diff import MigrationOperation, OperationType

    namer = MigrationNamer()

    # Test with table creation priority
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="posts"
        ),
    ]

    # Test that namer can generate names for mixed operations
    name = namer.generate_name(operations)
    assert isinstance(name, str)
    assert len(name) > 0


def test_migration_namer_sanitize_name():
    """Test name sanitization function."""
    namer = MigrationNamer()

    # Test various inputs
    assert namer._sanitize_name("Create Users Table") == "create_users_table"
    assert namer._sanitize_name("add-user_profile!") == "add_user_profile"
    assert namer._sanitize_name("123_starts_with_number") == "123_starts_with_number"
    assert namer._sanitize_name("___only_underscores___") == "only_underscores"
    assert namer._sanitize_name("") == "unnamed"


def test_migration_namer_generate_table_creation_name():
    """Test table creation name generation."""
    from synq.core.diff import MigrationOperation, OperationType

    namer = MigrationNamer()

    # Single table creation
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="user_profiles"
        )
    ]

    name = namer.generate_name(operations)
    assert "create" in name.lower()
    assert "user_profiles" in name.lower() or "profile" in name.lower()


def test_migration_namer_generate_column_name():
    """Test column operation name generation."""
    from synq.core.diff import MigrationOperation, OperationType

    namer = MigrationNamer()

    # Single column addition
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email_address",
        )
    ]

    name = namer.generate_name(operations)
    assert "add" in name.lower()
    assert "email" in name.lower()
    assert "users" in name.lower()


def test_migration_namer_generate_mixed_name():
    """Test mixed operations name generation."""
    from synq.core.diff import MigrationOperation, OperationType

    namer = MigrationNamer()

    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_INDEX,
            table_name="users",
            object_name="idx_email",
        ),
    ]

    name = namer.generate_name(operations)
    assert "update" in name.lower()
    assert "schema" in name.lower()


def test_snapshot_manager_create_table_snapshot_edge_cases():
    """Test table snapshot creation with edge cases."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = SnapshotManager(config)

        # Create table with complex column types
        metadata = MetaData()
        table = Table(
            "complex_table",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("data", String(length=None)),  # No length specified
            Column("nullable_col", String(50), nullable=True),
            Column("default_col", String(50), default="default_value"),
        )

        table_snapshot = manager._create_table_snapshot(table)

        assert table_snapshot.name == "complex_table"
        assert len(table_snapshot.columns) == 4

        # Check specific column properties
        id_col = next(c for c in table_snapshot.columns if c.name == "id")
        assert id_col.primary_key is True
        assert id_col.autoincrement is True


def test_database_manager_edge_cases():
    """Test database manager edge cases."""
    from synq.core.database import DatabaseManager

    # Test with invalid connection string
    with pytest.raises(Exception):  # Should raise some kind of database error
        DatabaseManager("invalid://connection/string")


def test_config_edge_cases():
    """Test configuration edge cases."""
    # Test config with minimal required fields
    config = SynqConfig(metadata_path="test:metadata")

    assert config.db_uri is None
    assert config.migrations_dir == "migrations"
    assert config.snapshot_dir == "migrations/meta"


def test_diff_algorithm_edge_cases():
    """Test schema diff algorithm edge cases."""
    differ = SchemaDiffer()

    # Test with identical complex snapshots
    tables = [
        TableSnapshot(
            name="complex_table",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="data", type="TEXT", nullable=True),
                ColumnSnapshot(
                    name="created_at",
                    type="DATETIME",
                    nullable=False,
                    default="CURRENT_TIMESTAMP",
                ),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]

    snapshot1 = SchemaSnapshot(tables=tables)
    snapshot2 = SchemaSnapshot(tables=tables)

    operations = differ.detect_changes(snapshot1, snapshot2)
    assert len(operations) == 0  # Should detect no changes


def test_column_snapshot_equality():
    """Test column snapshot comparison for equality."""
    col1 = ColumnSnapshot(
        name="test_col", type="VARCHAR(50)", nullable=False, primary_key=True
    )

    col2 = ColumnSnapshot(
        name="test_col", type="VARCHAR(50)", nullable=False, primary_key=True
    )

    col3 = ColumnSnapshot(
        name="test_col",
        type="VARCHAR(100)",  # Different type
        nullable=False,
        primary_key=True,
    )

    # Should be equal
    assert col1 == col2
    # Should not be equal
    assert col1 != col3


def test_migration_manager_file_handling_edge_cases():
    """Test migration manager file handling edge cases."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Test with empty migration directory
        migrations = manager.get_all_migrations()
        assert len(migrations) == 0

        # Test with non-migration files
        (manager.migrations_path / "README.txt").write_text("Not a migration")
        (manager.migrations_path / "0001_invalid").write_text("No .sql extension")

        migrations = manager.get_all_migrations()
        assert len(migrations) == 0


def test_naming_context_edge_cases():
    """Test NamingContext with edge cases."""
    from synq.core.naming import NamingContext

    # Empty context
    context = NamingContext(operations=[], table_names=set(), operation_counts={})

    assert len(context.operations) == 0
    assert len(context.table_names) == 0
    assert len(context.operation_counts) == 0


def test_operation_type_coverage():
    """Test that all operation types are covered."""
    from synq.core.diff import OperationType

    # Ensure all operation types have string values
    all_ops = [
        OperationType.CREATE_TABLE,
        OperationType.DROP_TABLE,
        OperationType.ADD_COLUMN,
        OperationType.DROP_COLUMN,
        OperationType.ALTER_COLUMN,
        OperationType.CREATE_INDEX,
        OperationType.DROP_INDEX,
        OperationType.ADD_FOREIGN_KEY,
        OperationType.DROP_FOREIGN_KEY,
    ]

    for op in all_ops:
        assert isinstance(op.value, str)
        assert len(op.value) > 0


def test_schema_snapshot_version_handling():
    """Test schema snapshot version handling."""
    # Test with different versions
    snapshot_v1 = SchemaSnapshot(tables=[], version="1.0")
    snapshot_v2 = SchemaSnapshot(tables=[], version="2.0")

    assert snapshot_v1.version == "1.0"
    assert snapshot_v2.version == "2.0"

    # Test default version
    snapshot_default = SchemaSnapshot(tables=[])
    assert snapshot_default.version == "1.0"


def test_error_message_formatting():
    """Test that error messages are properly formatted."""
    from synq.core.config import SynqConfig

    # Test missing file error message
    with pytest.raises(FileNotFoundError) as exc_info:
        SynqConfig.from_file(Path("nonexistent_config.toml"))

    error_message = str(exc_info.value)
    assert "Configuration file not found" in error_message
    assert "synq init" in error_message
