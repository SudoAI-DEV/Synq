"""Comprehensive tests for snapshot functionality."""

import tempfile
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

from synq.core.config import SynqConfig
from synq.core.snapshot import (
    ColumnSnapshot,
    ForeignKeySnapshot,
    IndexSnapshot,
    SchemaSnapshot,
    SnapshotManager,
    TableSnapshot,
)


def test_column_snapshot_creation():
    """Test creating a column snapshot."""
    column = ColumnSnapshot(
        name="test_col",
        type="VARCHAR(50)",
        nullable=False,
        default="'default_value'",
        primary_key=True,
        autoincrement=True,
        unique=True,
    )

    assert column.name == "test_col"
    assert column.type == "VARCHAR(50)"
    assert column.nullable is False
    assert column.default == "'default_value'"
    assert column.primary_key is True
    assert column.autoincrement is True
    assert column.unique is True


def test_index_snapshot_creation():
    """Test creating an index snapshot."""
    index = IndexSnapshot(
        name="idx_test",
        columns=["col1", "col2"],
        unique=True,
    )

    assert index.name == "idx_test"
    assert index.columns == ["col1", "col2"]
    assert index.unique is True


def test_foreign_key_snapshot_creation():
    """Test creating a foreign key snapshot."""
    fk = ForeignKeySnapshot(
        name="fk_test",
        columns=["user_id"],
        referred_table="users",
        referred_columns=["id"],
        ondelete="CASCADE",
        onupdate="RESTRICT",
    )

    assert fk.name == "fk_test"
    assert fk.columns == ["user_id"]
    assert fk.referred_table == "users"
    assert fk.referred_columns == ["id"]
    assert fk.ondelete == "CASCADE"
    assert fk.onupdate == "RESTRICT"


def test_table_snapshot_creation():
    """Test creating a table snapshot."""
    columns = [
        ColumnSnapshot(name="id", type="INTEGER", nullable=False, primary_key=True),
        ColumnSnapshot(name="name", type="VARCHAR(100)", nullable=True),
    ]
    indexes = [IndexSnapshot(name="idx_name", columns=["name"], unique=False)]
    foreign_keys = [
        ForeignKeySnapshot(
            name="fk_user",
            columns=["user_id"],
            referred_table="users",
            referred_columns=["id"],
        )
    ]

    table = TableSnapshot(
        name="test_table",
        columns=columns,
        indexes=indexes,
        foreign_keys=foreign_keys,
        schema="public",
    )

    assert table.name == "test_table"
    assert len(table.columns) == 2
    assert len(table.indexes) == 1
    assert len(table.foreign_keys) == 1
    assert table.schema == "public"


def test_schema_snapshot_creation():
    """Test creating a schema snapshot."""
    tables = [
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

    snapshot = SchemaSnapshot(tables=tables, version="1.0")

    assert len(snapshot.tables) == 1
    assert snapshot.version == "1.0"


def test_schema_snapshot_to_dict():
    """Test converting schema snapshot to dictionary."""
    tables = [
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

    snapshot = SchemaSnapshot(tables=tables, version="1.0")
    result = snapshot.to_dict()

    assert isinstance(result, dict)
    assert "tables" in result
    assert "version" in result
    assert result["version"] == "1.0"
    assert len(result["tables"]) == 1


def test_schema_snapshot_from_dict():
    """Test creating schema snapshot from dictionary."""
    data = {
        "version": "1.0",
        "tables": [
            {
                "name": "users",
                "schema": None,
                "columns": [
                    {
                        "name": "id",
                        "type": "INTEGER",
                        "nullable": False,
                        "default": None,
                        "primary_key": True,
                        "autoincrement": False,
                        "unique": False,
                    }
                ],
                "indexes": [],
                "foreign_keys": [],
            }
        ],
    }

    snapshot = SchemaSnapshot.from_dict(data)

    assert snapshot.version == "1.0"
    assert len(snapshot.tables) == 1
    assert snapshot.tables[0].name == "users"
    assert len(snapshot.tables[0].columns) == 1
    assert snapshot.tables[0].columns[0].name == "id"


def test_snapshot_manager_init():
    """Test SnapshotManager initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        assert manager.config == config
        assert manager.snapshot_path.exists()


def test_snapshot_manager_create_snapshot_simple():
    """Test creating a snapshot from simple metadata."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        # Create simple metadata
        metadata = MetaData()
        users_table = Table(
            "users",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(100), nullable=False),
        )

        snapshot = manager.create_snapshot(metadata)

        assert len(snapshot.tables) == 1
        assert snapshot.tables[0].name == "users"
        assert len(snapshot.tables[0].columns) == 2


def test_snapshot_manager_create_snapshot_complex():
    """Test creating a snapshot from complex metadata with indexes and foreign keys."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        # Create complex metadata
        metadata = MetaData()

        users_table = Table(
            "users",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("email", String(255), nullable=False, unique=True),
            Column("name", String(100)),
            Column("active", Boolean, default=True),
        )

        posts_table = Table(
            "posts",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("title", String(200), nullable=False),
            Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE")),
            Column("created_at", DateTime),
        )

        # Add indexes
        Index("idx_posts_user_id", posts_table.c.user_id)
        Index("idx_posts_title", posts_table.c.title)
        Index("idx_users_email", users_table.c.email, unique=True)

        snapshot = manager.create_snapshot(metadata)

        assert len(snapshot.tables) == 2

        # Find users table
        users_snapshot = next(t for t in snapshot.tables if t.name == "users")
        assert len(users_snapshot.columns) == 4
        assert len(users_snapshot.indexes) >= 1  # At least the email index

        # Find posts table
        posts_snapshot = next(t for t in snapshot.tables if t.name == "posts")
        assert len(posts_snapshot.columns) == 4
        assert len(posts_snapshot.foreign_keys) == 1
        assert len(posts_snapshot.indexes) >= 2  # title and user_id indexes

        # Check foreign key details
        fk = posts_snapshot.foreign_keys[0]
        assert fk.referred_table == "users"
        assert fk.ondelete == "CASCADE"


def test_snapshot_manager_save_and_load_snapshot():
    """Test saving and loading snapshots."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        # Create a snapshot
        tables = [
            TableSnapshot(
                name="test_table",
                columns=[
                    ColumnSnapshot(
                        name="id", type="INTEGER", nullable=False, primary_key=True
                    )
                ],
                indexes=[],
                foreign_keys=[],
            )
        ]
        snapshot = SchemaSnapshot(tables=tables)

        # Save the snapshot
        filepath = manager.save_snapshot(1, snapshot)
        assert filepath.exists()
        assert filepath.name == "0001_snapshot.json"

        # Load the snapshot back
        loaded_snapshot = manager.load_snapshot(1)
        assert loaded_snapshot is not None
        assert len(loaded_snapshot.tables) == 1
        assert loaded_snapshot.tables[0].name == "test_table"


def test_snapshot_manager_load_nonexistent_snapshot():
    """Test loading a non-existent snapshot."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        # Try to load non-existent snapshot
        snapshot = manager.load_snapshot(999)
        assert snapshot is None


def test_snapshot_manager_get_latest_snapshot():
    """Test getting the latest snapshot."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        # Initially should return None
        latest = manager.get_latest_snapshot()
        assert latest is None

        # Create some snapshots
        snapshot1 = SchemaSnapshot(tables=[])
        snapshot2 = SchemaSnapshot(tables=[])
        snapshot3 = SchemaSnapshot(tables=[])

        manager.save_snapshot(1, snapshot1)
        manager.save_snapshot(3, snapshot3)  # Save out of order
        manager.save_snapshot(2, snapshot2)

        # Should get the highest numbered snapshot
        latest = manager.get_latest_snapshot()
        assert latest is not None


def test_snapshot_manager_get_next_migration_number():
    """Test getting the next migration number."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        # Initially should return 0
        next_num = manager.get_next_migration_number()
        assert next_num == 0

        # Create a snapshot
        snapshot = SchemaSnapshot(tables=[])
        manager.save_snapshot(5, snapshot)

        # Should return 6
        next_num = manager.get_next_migration_number()
        assert next_num == 6

        # Create another snapshot
        manager.save_snapshot(10, snapshot)

        # Should return 11
        next_num = manager.get_next_migration_number()
        assert next_num == 11


def test_snapshot_manager_get_all_snapshots():
    """Test getting all available snapshots."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        # Initially should return empty list
        all_snapshots = manager.get_all_snapshots()
        assert all_snapshots == []

        # Create some snapshots
        snapshot = SchemaSnapshot(tables=[])
        manager.save_snapshot(1, snapshot)
        manager.save_snapshot(5, snapshot)
        manager.save_snapshot(3, snapshot)

        # Should return sorted list
        all_snapshots = manager.get_all_snapshots()
        assert all_snapshots == [1, 3, 5]


def test_snapshot_manager_get_all_snapshots_with_invalid_files():
    """Test getting snapshots when there are invalid files in directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        # Create valid snapshot
        snapshot = SchemaSnapshot(tables=[])
        manager.save_snapshot(1, snapshot)

        # Create invalid files
        (manager.snapshot_path / "invalid_snapshot.json").write_text("{}")
        (manager.snapshot_path / "not_a_number_snapshot.json").write_text("{}")
        (manager.snapshot_path / "0002_valid_snapshot.json").write_text(
            '{"tables": [], "version": "1.0"}'
        )

        # Should only return valid numbered snapshots
        all_snapshots = manager.get_all_snapshots()
        assert set(all_snapshots) == {1, 2}


def test_create_table_snapshot_with_schema():
    """Test creating table snapshot with schema."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        # Create metadata with schema
        metadata = MetaData()
        table = Table(
            "test_table",
            metadata,
            Column("id", Integer, primary_key=True),
            schema="public",
        )

        table_snapshot = manager._create_table_snapshot(table)

        assert table_snapshot.name == "test_table"
        assert table_snapshot.schema == "public"


def test_snapshot_with_constraints():
    """Test snapshot creation with various constraints."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path(temp_dir) / "migrations"),
            snapshot_dir=str(Path(temp_dir) / "migrations" / "meta"),
        )

        manager = SnapshotManager(config)

        # Create metadata with constraints
        metadata = MetaData()
        table = Table(
            "constrained_table",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("email", String(255), unique=True),
            Column("name", String(100), nullable=False),
            UniqueConstraint("name", "email", name="uq_name_email"),
        )

        snapshot = manager.create_snapshot(metadata)

        assert len(snapshot.tables) == 1
        table_snapshot = snapshot.tables[0]

        # Check unique column
        email_col = next(c for c in table_snapshot.columns if c.name == "email")
        assert email_col.unique is True

        # Check nullable column
        name_col = next(c for c in table_snapshot.columns if c.name == "name")
        assert name_col.nullable is False
