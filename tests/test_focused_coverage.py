"""Focused tests to improve specific module coverage."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

from sqlalchemy import MetaData

from synq.core.config import SynqConfig
from synq.core.diff import MigrationOperation, OperationType
from synq.core.migration import MigrationManager
from synq.core.naming import MigrationNamer, generate_migration_name


def test_migration_manager_create_migration_name_basic():
    """Test basic migration name creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Test basic name creation
        name = manager.create_migration_name("Create Users")
        assert name == "create_users"

        # Test empty name
        name = manager.create_migration_name("")
        assert isinstance(name, str)

        # Test with special characters
        name = manager.create_migration_name("Add User-Profile & Settings!")
        assert name == "add_user_profile_settings"


def test_migration_manager_save_migration_basic():
    """Test basic migration file saving."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Save a migration
        sql_content = "CREATE TABLE test (id INTEGER);"
        filepath = manager.save_migration(1, "test_migration", sql_content)

        assert filepath.exists()
        assert filepath.name == "0001_test_migration.sql"
        assert filepath.read_text() == sql_content


def test_migration_manager_get_all_migrations_basic():
    """Test getting all migration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Initially empty
        migrations = manager.get_all_migrations()
        assert len(migrations) == 0

        # Create migration files
        (manager.migrations_path / "0001_first.sql").write_text("CREATE TABLE first;")
        (manager.migrations_path / "0002_second.sql").write_text("CREATE TABLE second;")

        migrations = manager.get_all_migrations()
        assert len(migrations) == 2
        assert migrations[0].filename == "0001_first.sql"
        assert migrations[1].filename == "0002_second.sql"


def test_migration_manager_get_all_migrations_parsing():
    """Test migration file parsing in get_all_migrations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create valid migration files
        (manager.migrations_path / "0001_create_users.sql").write_text(
            "CREATE TABLE users;"
        )
        (manager.migrations_path / "invalid_name.sql").write_text("Invalid file")

        migrations = manager.get_all_migrations()

        # Should only include valid migrations
        assert len(migrations) == 1
        assert migrations[0].number == 1
        assert migrations[0].name == "create_users"


def test_migration_manager_get_pending_migrations_basic():
    """Test getting pending migrations with mock db_manager."""

    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create migration files
        (manager.migrations_path / "0001_first.sql").write_text("CREATE TABLE first;")
        (manager.migrations_path / "0002_second.sql").write_text("CREATE TABLE second;")
        (manager.migrations_path / "0003_third.sql").write_text("CREATE TABLE third;")

        # Mock database manager
        mock_db_manager = Mock()
        mock_db_manager.get_applied_migrations.return_value = [
            "0001_first.sql",
            "0002_second.sql",
        ]

        pending = manager.get_pending_migrations(mock_db_manager)
        assert len(pending) == 1
        assert pending[0].filename == "0003_third.sql"


def test_migration_manager_get_migration_by_number():
    """Test getting migration by number through get_all_migrations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Create migration files
        (manager.migrations_path / "0001_first.sql").write_text("CREATE TABLE first;")
        (manager.migrations_path / "0005_fifth.sql").write_text("CREATE TABLE fifth;")

        # Get all migrations
        migrations = manager.get_all_migrations()
        migration_dict = {m.number: m for m in migrations}

        # Get existing migration
        migration = migration_dict.get(1)
        assert migration is not None
        assert migration.filename == "0001_first.sql"

        # Get existing migration with gap
        migration = migration_dict.get(5)
        assert migration is not None
        assert migration.filename == "0005_fifth.sql"

        # Check non-existent migration
        migration = migration_dict.get(3)
        assert migration is None


def test_migration_manager_basic_sql_operations():
    """Test basic SQL operations exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)

        # Test generate_sql with empty operations
        sql = manager.generate_sql([], None)
        assert sql == ""

        # Test that differ is initialized
        assert manager.differ is not None

        # Test migrations path exists
        assert manager.migrations_path.exists()


def test_naming_module_basic_functions():
    """Test basic naming module functions."""
    # Test generate_migration_name function
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="users"
        )
    ]

    name = generate_migration_name(operations)
    assert isinstance(name, str)
    assert len(name) > 0


def test_migration_namer_analyze_operations():
    """Test operation analysis."""
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

    analysis = namer._analyze_operations(operations)

    assert len(analysis.operations) == 2
    assert "users" in analysis.table_names
    assert analysis.operation_counts[OperationType.CREATE_TABLE] == 1
    assert analysis.operation_counts[OperationType.ADD_COLUMN] == 1


def test_migration_namer_single_operation_naming():
    """Test single operation naming."""
    namer = MigrationNamer()

    # Test CREATE_TABLE operation
    operation = MigrationOperation(
        operation_type=OperationType.CREATE_TABLE, table_name="users"
    )

    name = namer._generate_single_operation_name(operation)
    assert "create" in name.lower()
    assert "users" in name.lower()
    assert "table" in name.lower()


def test_migration_namer_sanitize_name():
    """Test name sanitization."""
    namer = MigrationNamer()

    # Test basic sanitization
    assert namer._sanitize_name("Create Users") == "create_users"
    assert namer._sanitize_name("add-user_profile") == "add_user_profile"
    assert namer._sanitize_name("Add User!!! Table") == "add_user_table"

    # Test edge cases
    assert namer._sanitize_name("123abc") == "123abc"  # Numbers are allowed
    assert (
        namer._sanitize_name("___test___") == "test"
    )  # Remove leading/trailing underscores


def test_migration_namer_single_table_name():
    """Test single table multiple operations naming."""
    namer = MigrationNamer()

    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="phone",
        ),
    ]

    context = namer._analyze_operations(operations)
    name = namer._generate_single_table_name(context, "users")

    assert "users" in name.lower()
    assert "add" in name.lower() or "columns" in name.lower()


def test_migration_namer_multi_table_name():
    """Test multiple table operations naming."""
    namer = MigrationNamer()

    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="users"
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="posts"
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="comments"
        ),
    ]

    context = namer._analyze_operations(operations)
    name = namer._generate_multi_table_name(context)

    assert (
        "create" in name.lower()
        or "tables" in name.lower()
        or "initial" in name.lower()
    )


def test_migration_namer_is_initial_migration():
    """Test initial migration detection."""
    namer = MigrationNamer()

    # Multiple table creation operations
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="users"
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="posts"
        ),
    ]

    context = namer._analyze_operations(operations)
    is_initial = namer._is_initial_migration(context)

    assert is_initial is True


def test_naming_context_basic():
    """Test NamingContext creation."""
    from synq.core.naming import NamingContext

    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="users"
        )
    ]

    context = NamingContext(
        operations=operations,
        table_names={"users"},
        operation_counts={OperationType.CREATE_TABLE: 1},
    )

    assert len(context.operations) == 1
    assert "users" in context.table_names
    assert context.operation_counts[OperationType.CREATE_TABLE] == 1


def test_migration_manager_operation_to_sql_drop_table():
    """Test DROP TABLE SQL generation."""
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


def test_migration_manager_operation_to_sql_add_column():
    """Test ADD COLUMN SQL generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        manager = MigrationManager(config)
        metadata = MetaData()

        from synq.core.snapshot import ColumnSnapshot

        new_column = ColumnSnapshot(name="email", type="VARCHAR(255)", nullable=True)

        operation = MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
            new_definition=new_column,
        )

        sql = manager.generate_sql([operation], metadata)

        assert "ALTER TABLE users ADD COLUMN email" in sql


def test_migration_manager_operation_to_sql_drop_column():
    """Test DROP COLUMN SQL generation."""
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


def test_snapshot_manager_load_nonexistent_file():
    """Test loading non-existent snapshot file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        from synq.core.snapshot import SnapshotManager

        manager = SnapshotManager(config)

        # Try to load non-existent snapshot
        snapshot = manager.load_snapshot(999)
        assert snapshot is None


def test_snapshot_manager_get_all_snapshots_invalid_files():
    """Test getting snapshots with invalid files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations/meta"),
        )

        from synq.core.snapshot import SnapshotManager

        manager = SnapshotManager(config)

        # Create invalid files
        (manager.snapshot_path / "not_a_snapshot.txt").write_text("invalid")
        (manager.snapshot_path / "invalid_name.json").write_text("{}")

        # Should return empty list
        snapshots = manager.get_all_snapshots()
        assert snapshots == []
