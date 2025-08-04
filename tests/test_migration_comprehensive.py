"""Comprehensive tests for migration management."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from sqlalchemy import Column, Integer, MetaData, Table

from synq.core.config import SynqConfig
from synq.core.diff import MigrationOperation, OperationType
from synq.core.migration import MigrationFile, MigrationManager, PendingMigration
from synq.core.snapshot import ColumnSnapshot, SchemaSnapshot, TableSnapshot


def test_migration_file_namedtuple():
    """Test MigrationFile NamedTuple."""
    migration = MigrationFile(
        number=1,
        name="create_users",
        filename="0001_create_users.sql",
        filepath=Path("migrations/0001_create_users.sql"),
        sql_content="CREATE TABLE users (id INTEGER);",
    )

    assert migration.number == 1
    assert migration.name == "create_users"
    assert migration.filename == "0001_create_users.sql"
    assert migration.sql_content == "CREATE TABLE users (id INTEGER);"


def test_pending_migration_dataclass():
    """Test PendingMigration dataclass."""
    pending = PendingMigration(
        filename="0001_test.sql", sql_content="CREATE TABLE test (id INTEGER);"
    )

    assert pending.filename == "0001_test.sql"
    assert pending.sql_content == "CREATE TABLE test (id INTEGER);"


def test_migration_manager_init():
    """Test MigrationManager initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        assert manager.config == config
        assert manager.migrations_path.exists()
        assert manager.differ is not None


def test_migration_manager_detect_changes():
    """Test change detection."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create snapshots
        old_snapshot = SchemaSnapshot(tables=[])
        new_snapshot = SchemaSnapshot(
            tables=[
                TableSnapshot(
                    name="users",
                    columns=[
                        ColumnSnapshot(
                            name="id", type="INTEGER", nullable=False, primary_key=True
                        )
                    ],
                    indexes=[],
                    foreign_keys=[],
                )
            ]
        )

        operations = manager.detect_changes(old_snapshot, new_snapshot)

        assert len(operations) == 1
        assert operations[0].operation_type == OperationType.CREATE_TABLE
        assert operations[0].table_name == "users"


def test_migration_manager_generate_sql_empty():
    """Test SQL generation with empty operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        sql = manager.generate_sql([], metadata)

        assert sql == ""


def test_migration_manager_generate_sql_create_table():
    """Test SQL generation for table creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create metadata with table
        metadata = MetaData()
        Table("users", metadata, Column("id", Integer, primary_key=True))

        # Create operation
        operation = MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="users"
        )

        sql = manager.generate_sql([operation], metadata)

        assert "CREATE TABLE users" in sql
        assert "-- CREATE TABLE users" in sql


def test_migration_manager_operation_to_sql_error_handling():
    """Test error handling in SQL generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        # Create operation for non-existent table
        operation = MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="nonexistent_table"
        )

        sql = manager.generate_sql([operation], metadata)

        assert "WARNING: Could not generate SQL" in sql


def test_migration_manager_create_migration_name():
    """Test migration name creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        name = manager.create_migration_name("Create users table")

        # Should sanitize the name
        assert name == "create_users_table"


def test_migration_manager_create_migration_name_sanitization():
    """Test migration name sanitization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Test various special characters
        name = manager.create_migration_name("Add user-profile & settings!")

        # Should only contain alphanumeric and underscores
        assert name == "add_user_profile_settings"


def test_migration_manager_save_migration():
    """Test saving migration to file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        sql_content = "CREATE TABLE users (id INTEGER PRIMARY KEY);"
        filepath = manager.save_migration(1, "create_users", sql_content)

        assert filepath.exists()
        assert filepath.name == "0001_create_users.sql"
        assert filepath.read_text() == sql_content


def test_migration_manager_get_all_migrations():
    """Test getting all migration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create some migration files
        (manager.migrations_path / "0001_first.sql").write_text(
            "CREATE TABLE first (id INTEGER);"
        )
        (manager.migrations_path / "0002_second.sql").write_text(
            "CREATE TABLE second (id INTEGER);"
        )
        (manager.migrations_path / "not_a_migration.txt").write_text("Not a migration")

        migrations = manager.get_all_migrations()

        assert len(migrations) == 2
        assert migrations[0].filename == "0001_first.sql"
        assert migrations[1].filename == "0002_second.sql"


def test_migration_manager_get_pending_migrations():
    """Test getting pending migrations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create migration files
        (manager.migrations_path / "0001_first.sql").write_text(
            "CREATE TABLE first (id INTEGER);"
        )
        (manager.migrations_path / "0002_second.sql").write_text(
            "CREATE TABLE second (id INTEGER);"
        )

        # Create mock db_manager
        mock_db_manager = Mock()
        mock_db_manager.get_applied_migrations.return_value = ["0001_first.sql"]

        pending = manager.get_pending_migrations(mock_db_manager)

        assert len(pending) == 1
        assert pending[0].filename == "0002_second.sql"
        assert pending[0].sql_content == "CREATE TABLE second (id INTEGER);"


def test_migration_manager_parse_migration_filename():
    """Test parsing migration filenames."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Test valid filename
        number, name = manager._parse_migration_filename("0001_create_users.sql")
        assert number == 1
        assert name == "create_users"

        # Test invalid filename
        result = manager._parse_migration_filename("invalid_filename.sql")
        assert result is None


def test_migration_manager_generate_sql_with_multiple_operations():
    """Test SQL generation with multiple operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create metadata with tables
        metadata = MetaData()
        Table("users", metadata, Column("id", Integer, primary_key=True))
        Table("posts", metadata, Column("id", Integer, primary_key=True))

        # Create multiple operations
        operations = [
            MigrationOperation(
                operation_type=OperationType.CREATE_TABLE, table_name="users"
            ),
            MigrationOperation(
                operation_type=OperationType.CREATE_TABLE, table_name="posts"
            ),
        ]

        sql = manager.generate_sql(operations, metadata)

        assert "CREATE TABLE users" in sql
        assert "CREATE TABLE posts" in sql
        assert sql.count("-- CREATE TABLE") == 2


def test_migration_manager_sql_generation_error_recovery():
    """Test SQL generation continues after errors."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create metadata with one valid table
        metadata = MetaData()
        Table("users", metadata, Column("id", Integer, primary_key=True))

        # Create operations with one invalid
        operations = [
            MigrationOperation(
                operation_type=OperationType.CREATE_TABLE,
                table_name="nonexistent",  # This will fail
            ),
            MigrationOperation(
                operation_type=OperationType.CREATE_TABLE,
                table_name="users",  # This should succeed
            ),
        ]

        sql = manager.generate_sql(operations, metadata)

        # Should contain warning about failed operation
        assert "WARNING: Could not generate SQL" in sql
        # Should still contain successful operation
        assert "CREATE TABLE users" in sql


def test_migration_manager_drop_table_operation():
    """Test DROP TABLE operation SQL generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        operation = MigrationOperation(
            operation_type=OperationType.DROP_TABLE, table_name="old_table"
        )

        sql = manager.generate_sql([operation], metadata)

        assert "DROP TABLE old_table" in sql


def test_migration_manager_add_column_operation():
    """Test ADD COLUMN operation SQL generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        # Mock new column definition
        new_column = ColumnSnapshot(name="email", type="VARCHAR(255)", nullable=True)

        operation = MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
            new_definition=new_column,
        )

        sql = manager.generate_sql([operation], metadata)

        assert "ALTER TABLE users ADD COLUMN email" in sql


def test_migration_manager_drop_column_operation():
    """Test DROP COLUMN operation SQL generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        operation = MigrationOperation(
            operation_type=OperationType.DROP_COLUMN,
            table_name="users",
            object_name="old_column",
        )

        sql = manager.generate_sql([operation], metadata)

        assert "ALTER TABLE users DROP COLUMN old_column" in sql


def test_migration_manager_create_index_operation():
    """Test CREATE INDEX operation SQL generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        from synq.core.snapshot import IndexSnapshot

        index_def = IndexSnapshot(name="idx_email", columns=["email"], unique=True)

        operation = MigrationOperation(
            operation_type=OperationType.CREATE_INDEX,
            table_name="users",
            object_name="idx_email",
            new_definition=index_def,
        )

        sql = manager.generate_sql([operation], metadata)

        assert "CREATE" in sql
        assert "INDEX" in sql


def test_migration_manager_long_migration_name():
    """Test handling of very long migration names."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Very long name
        long_name = "create_a_very_long_migration_name_that_exceeds_normal_limits_and_should_be_truncated"

        result = manager.create_migration_name(long_name)

        # Should be truncated to reasonable length
        assert len(result) <= 100
        assert result.startswith("create_a_very_long")


def test_migration_manager_empty_migration_name():
    """Test handling of empty migration name."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        name = manager.create_migration_name("")

        # Should provide a default name
        assert name == "migration"


def test_migration_manager_get_migration_by_number():
    """Test getting specific migration by number."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create migration files
        (manager.migrations_path / "0001_first.sql").write_text(
            "CREATE TABLE first (id INTEGER);"
        )
        (manager.migrations_path / "0003_third.sql").write_text(
            "CREATE TABLE third (id INTEGER);"
        )

        # Get existing migration
        migration = manager.get_migration_by_number(1)
        assert migration is not None
        assert migration.filename == "0001_first.sql"

        # Get non-existent migration
        migration = manager.get_migration_by_number(2)
        assert migration is None


def test_migration_manager_validate_migration_sql():
    """Test basic SQL validation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Valid SQL
        valid_sql = "CREATE TABLE users (id INTEGER PRIMARY KEY);"
        assert manager.validate_migration_sql(valid_sql) is True

        # Invalid SQL (empty)
        assert manager.validate_migration_sql("") is False
        assert manager.validate_migration_sql("   ") is False
