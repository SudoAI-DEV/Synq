"""Final tests to push coverage to 90%+."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from sqlalchemy import MetaData

from synq.core.config import SynqConfig
from synq.core.diff import MigrationOperation, OperationType
from synq.core.migration import MigrationManager
from synq.core.naming import MigrationNamer


def test_migration_manager_build_sqlalchemy_table():
    """Test _build_sqlalchemy_table method."""
    from synq.core.snapshot import ColumnSnapshot, TableSnapshot

    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        # Create table snapshot
        table_def = TableSnapshot(
            name="test_table",
            columns=[
                ColumnSnapshot(
                    name="id",
                    type="INTEGER",
                    nullable=False,
                    primary_key=True,
                    autoincrement=True,
                ),
                ColumnSnapshot(name="name", type="VARCHAR(50)", nullable=True),
                ColumnSnapshot(name="description", type="TEXT", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )

        # Test building table
        table = manager._build_sqlalchemy_table(table_def, metadata)

        assert table.name == "test_table"
        assert len(table.columns) == 3
        assert "id" in table.columns
        assert "name" in table.columns
        assert "description" in table.columns


def test_migration_manager_operation_to_sql_create_table():
    """Test CREATE_TABLE SQL generation."""
    from synq.core.snapshot import ColumnSnapshot, TableSnapshot

    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        # Create table definition
        table_def = TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                )
            ],
            indexes=[],
            foreign_keys=[],
        )

        operation = MigrationOperation(
            operation_type=OperationType.CREATE_TABLE,
            table_name="users",
            new_definition=table_def,
        )

        sql = manager.generate_sql([operation], metadata)

        assert "CREATE TABLE users" in sql
        assert "id" in sql
        assert "INTEGER" in sql


def test_migration_manager_operation_to_sql_alter_column():
    """Test ALTER_COLUMN SQL generation."""
    from synq.core.snapshot import ColumnSnapshot

    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        old_col = ColumnSnapshot(name="name", type="VARCHAR(50)", nullable=True)

        new_col = ColumnSnapshot(name="name", type="VARCHAR(100)", nullable=False)

        operation = MigrationOperation(
            operation_type=OperationType.ALTER_COLUMN,
            table_name="users",
            object_name="name",
            old_definition=old_col,
            new_definition=new_col,
        )

        sql = manager.generate_sql([operation], metadata)

        assert "ALTER COLUMN" in sql
        assert "users.name" in sql
        assert "VARCHAR(50)" in sql
        assert "VARCHAR(100)" in sql


def test_migration_manager_operation_to_sql_create_index():
    """Test CREATE_INDEX SQL generation."""
    from synq.core.snapshot import IndexSnapshot

    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        index_def = IndexSnapshot(
            name="idx_users_email", columns=["email"], unique=True
        )

        operation = MigrationOperation(
            operation_type=OperationType.CREATE_INDEX,
            table_name="users",
            object_name="idx_users_email",
            new_definition=index_def,
        )

        sql = manager.generate_sql([operation], metadata)

        assert "CREATE UNIQUE INDEX idx_users_email" in sql
        assert "users" in sql
        assert "email" in sql


def test_migration_manager_operation_to_sql_add_foreign_key():
    """Test ADD_FOREIGN_KEY SQL generation."""
    from synq.core.snapshot import ForeignKeySnapshot

    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        fk_def = ForeignKeySnapshot(
            name="fk_posts_user_id",
            columns=["user_id"],
            referred_table="users",
            referred_columns=["id"],
            ondelete="CASCADE",
            onupdate="RESTRICT",
        )

        operation = MigrationOperation(
            operation_type=OperationType.ADD_FOREIGN_KEY,
            table_name="posts",
            object_name="fk_posts_user_id",
            new_definition=fk_def,
        )

        sql = manager.generate_sql([operation], metadata)

        assert "ALTER TABLE posts ADD" in sql
        assert "FOREIGN KEY" in sql
        assert "user_id" in sql
        assert "REFERENCES users" in sql
        assert "CASCADE" in sql
        assert "RESTRICT" in sql


def test_migration_manager_operation_to_sql_drop_foreign_key():
    """Test DROP_FOREIGN_KEY SQL generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        operation = MigrationOperation(
            operation_type=OperationType.DROP_FOREIGN_KEY,
            table_name="posts",
            object_name="fk_posts_user_id",
        )

        sql = manager.generate_sql([operation], metadata)

        assert "ALTER TABLE posts DROP CONSTRAINT fk_posts_user_id" in sql


def test_migration_manager_operation_to_sql_drop_foreign_key_no_name():
    """Test DROP_FOREIGN_KEY SQL generation without constraint name."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        operation = MigrationOperation(
            operation_type=OperationType.DROP_FOREIGN_KEY,
            table_name="posts",
            object_name=None,
        )

        sql = manager.generate_sql([operation], metadata)

        assert "DROP FOREIGN KEY on posts" in sql
        assert "no constraint name" in sql


def test_migration_manager_operation_to_sql_drop_index():
    """Test DROP_INDEX SQL generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        operation = MigrationOperation(
            operation_type=OperationType.DROP_INDEX,
            table_name="users",
            object_name="idx_users_email",
        )

        sql = manager.generate_sql([operation], metadata)

        assert "DROP INDEX idx_users_email" in sql


def test_migration_manager_operation_to_sql_unsupported():
    """Test unsupported operation type."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        # Mock unknown operation type
        operation = Mock()
        operation.operation_type = Mock()
        operation.operation_type.value = "UNKNOWN_OPERATION"
        operation.table_name = "test_table"
        operation.object_name = None

        sql = manager._operation_to_sql(operation, metadata, None)

        assert "Unsupported operation" in sql


def test_migration_namer_generate_name_empty():
    """Test generate_name with empty operations."""
    namer = MigrationNamer()

    name = namer.generate_name([])
    assert name == "empty_migration"


def test_migration_namer_is_initial_migration_false():
    """Test _is_initial_migration returns False for mixed operations."""
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
    ]

    context = namer._analyze_operations(operations)
    is_initial = namer._is_initial_migration(context)

    assert is_initial is False


def test_migration_namer_generate_single_table_name_drop_columns():
    """Test _generate_single_table_name for drop columns."""
    namer = MigrationNamer()

    operations = [
        MigrationOperation(
            operation_type=OperationType.DROP_COLUMN,
            table_name="users",
            object_name="old_field",
        ),
        MigrationOperation(
            operation_type=OperationType.DROP_COLUMN,
            table_name="users",
            object_name="legacy_field",
        ),
    ]

    context = namer._analyze_operations(operations)
    name = namer._generate_single_table_name(context, "users")

    assert "remove_columns_from_users" in name.lower()


def test_migration_namer_generate_multi_table_name_variations():
    """Test _generate_multi_table_name for different operation types."""
    namer = MigrationNamer()

    # Test DROP_TABLE dominant
    operations = [
        MigrationOperation(operation_type=OperationType.DROP_TABLE, table_name="old1"),
        MigrationOperation(operation_type=OperationType.DROP_TABLE, table_name="old2"),
        MigrationOperation(operation_type=OperationType.DROP_TABLE, table_name="old3"),
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
    ]

    context = namer._analyze_operations(operations)
    name = namer._generate_multi_table_name(context)

    assert "delete_tables" in name.lower()


def test_migration_namer_generate_multi_table_name_add_columns():
    """Test _generate_multi_table_name for ADD_COLUMN dominant."""
    namer = MigrationNamer()

    # Test ADD_COLUMN dominant
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="posts",
            object_name="title",
        ),
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="comments",
            object_name="body",
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="temp"
        ),
    ]

    context = namer._analyze_operations(operations)
    name = namer._generate_multi_table_name(context)

    assert "add_columns" in name.lower()


def test_migration_namer_generate_multi_table_name_remove_columns():
    """Test _generate_multi_table_name for DROP_COLUMN dominant."""
    namer = MigrationNamer()

    # Test DROP_COLUMN dominant
    operations = [
        MigrationOperation(
            operation_type=OperationType.DROP_COLUMN,
            table_name="users",
            object_name="old1",
        ),
        MigrationOperation(
            operation_type=OperationType.DROP_COLUMN,
            table_name="posts",
            object_name="old2",
        ),
        MigrationOperation(
            operation_type=OperationType.DROP_COLUMN,
            table_name="comments",
            object_name="old3",
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="temp"
        ),
    ]

    context = namer._analyze_operations(operations)
    name = namer._generate_multi_table_name(context)

    assert "remove_columns" in name.lower()


def test_migration_namer_sanitize_name_empty():
    """Test _sanitize_name with empty input."""
    namer = MigrationNamer()

    assert namer._sanitize_name("") == "unnamed"
    assert namer._sanitize_name("   ") == "unnamed"
    assert namer._sanitize_name("!!!") == "unnamed"


def test_migration_manager_create_migration_name_length_limit():
    """Test migration name length limiting."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Very long description
        long_desc = "a" * 100
        name = manager.create_migration_name(long_desc)

        assert len(name) <= 50
        assert not name.endswith("_")


def test_migration_manager_file_operations_error_handling():
    """Test file operation error handling."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create invalid migration file
        invalid_file = manager.migrations_path / "invalid.sql"
        invalid_file.write_text("CREATE TABLE test;")

        # Create file with invalid number
        invalid_number_file = manager.migrations_path / "abc_test.sql"
        invalid_number_file.write_text("CREATE TABLE test;")

        migrations = manager.get_all_migrations()

        # Should skip invalid files
        assert len(migrations) == 0
