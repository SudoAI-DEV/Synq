"""Tests for snapshot system."""

from synq.core.snapshot import (
    ColumnSnapshot,
    SchemaSnapshot,
    SnapshotManager,
    TableSnapshot,
)


def test_create_snapshot(test_config, test_metadata):
    """Test creating a snapshot from metadata."""
    manager = SnapshotManager(test_config)
    snapshot = manager.create_snapshot(test_metadata)

    assert isinstance(snapshot, SchemaSnapshot)
    assert len(snapshot.tables) == 1

    table = snapshot.tables[0]
    assert table.name == "users"
    assert len(table.columns) == 3

    # Check columns
    column_names = [col.name for col in table.columns]
    assert "id" in column_names
    assert "name" in column_names
    assert "email" in column_names


def test_save_and_load_snapshot(test_config, test_metadata):
    """Test saving and loading snapshots."""
    manager = SnapshotManager(test_config)
    snapshot = manager.create_snapshot(test_metadata)

    # Save snapshot
    filepath = manager.save_snapshot(0, snapshot)
    assert filepath.exists()

    # Load snapshot back
    loaded_snapshot = manager.load_snapshot(0)
    assert loaded_snapshot is not None
    assert len(loaded_snapshot.tables) == len(snapshot.tables)
    assert loaded_snapshot.tables[0].name == snapshot.tables[0].name


def test_get_latest_snapshot(test_config, test_metadata):
    """Test getting the latest snapshot."""
    manager = SnapshotManager(test_config)

    # No snapshots initially
    assert manager.get_latest_snapshot() is None

    # Create some snapshots
    snapshot1 = manager.create_snapshot(test_metadata)
    manager.save_snapshot(0, snapshot1)

    snapshot2 = manager.create_snapshot(test_metadata)
    manager.save_snapshot(1, snapshot2)

    # Get latest
    latest = manager.get_latest_snapshot()
    assert latest is not None
    assert len(latest.tables) == 1


def test_get_next_migration_number(test_config, test_metadata):
    """Test getting next migration number."""
    manager = SnapshotManager(test_config)

    # Should start at 0
    assert manager.get_next_migration_number() == 0

    # After creating snapshots
    snapshot = manager.create_snapshot(test_metadata)
    manager.save_snapshot(0, snapshot)
    assert manager.get_next_migration_number() == 1

    manager.save_snapshot(2, snapshot)  # Skip 1
    assert manager.get_next_migration_number() == 3


def test_column_snapshot():
    """Test ColumnSnapshot creation."""
    col = ColumnSnapshot(
        name="test_col",
        type="VARCHAR(50)",
        nullable=False,
        primary_key=True,
        unique=True,
    )

    assert col.name == "test_col"
    assert col.type == "VARCHAR(50)"
    assert not col.nullable
    assert col.primary_key
    assert col.unique


def test_schema_snapshot_serialization():
    """Test schema snapshot JSON serialization."""
    column = ColumnSnapshot(name="id", type="INTEGER", nullable=False, primary_key=True)
    table = TableSnapshot(name="test", columns=[column], indexes=[], foreign_keys=[])
    snapshot = SchemaSnapshot(tables=[table])

    # Convert to dict and back
    data = snapshot.to_dict()
    restored = SchemaSnapshot.from_dict(data)

    assert len(restored.tables) == 1
    assert restored.tables[0].name == "test"
    assert len(restored.tables[0].columns) == 1
    assert restored.tables[0].columns[0].name == "id"
