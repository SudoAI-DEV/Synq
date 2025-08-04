"""Basic workflow tests for Synq core functionality."""

import tempfile
from pathlib import Path

from sqlalchemy import Column, Integer, MetaData, String, Table

from synq.core.config import SynqConfig
from synq.core.diff import SchemaDiffer
from synq.core.migration import MigrationManager
from synq.core.snapshot import SnapshotManager


def test_basic_snapshot_workflow():
    """Test basic snapshot creation and diff generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create config
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(tmp_path / "migrations"),
            snapshot_dir=str(tmp_path / "migrations" / "meta"),
        )

        # Create test metadata
        metadata = MetaData()
        users_table = Table(
            "users",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("username", String(50), unique=True),
        )

        # Create snapshot
        snapshot_manager = SnapshotManager(config)
        snapshot = snapshot_manager.create_snapshot(metadata)

        # Verify snapshot
        assert len(snapshot.tables) == 1
        assert snapshot.tables[0].name == "users"
        assert len(snapshot.tables[0].columns) == 2

        # Test diff generation with empty initial state
        differ = SchemaDiffer()
        operations = differ.detect_changes(None, snapshot)

        # Should detect table creation
        assert len(operations) == 1
        assert operations[0].table_name == "users"


def test_migration_manager_sql_generation():
    """Test SQL generation from metadata."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(tmp_path / "migrations"),
            snapshot_dir=str(tmp_path / "migrations" / "meta"),
        )

        # Create test metadata
        metadata = MetaData()
        users_table = Table(
            "users",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("username", String(50), unique=True),
        )

        # Create migration manager
        migration_manager = MigrationManager(config)

        # Create snapshot and operations
        snapshot_manager = SnapshotManager(config)
        snapshot = snapshot_manager.create_snapshot(metadata)
        operations = migration_manager.detect_changes(None, snapshot)

        # Generate SQL
        sql_content = migration_manager.generate_sql(operations, metadata)

        # Verify SQL content
        assert "CREATE TABLE users" in sql_content
        assert "id" in sql_content
        assert "username" in sql_content


def test_migration_file_operations():
    """Test migration file saving and loading."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(tmp_path / "migrations"),
            snapshot_dir=str(tmp_path / "migrations" / "meta"),
        )

        migration_manager = MigrationManager(config)

        # Save a migration
        sql_content = "CREATE TABLE test (id INTEGER PRIMARY KEY);"
        migration_path = migration_manager.save_migration(
            migration_number=1,
            migration_name="create_test_table",
            sql_content=sql_content,
        )

        # Verify file was created
        assert migration_path.exists()
        assert migration_path.name == "0001_create_test_table.sql"

        # Verify content
        with open(migration_path) as f:
            saved_content = f.read()
        assert saved_content == sql_content

        # Test migration listing
        migrations = migration_manager.get_all_migrations()
        assert len(migrations) == 1
        assert migrations[0].name == "create_test_table"
        assert migrations[0].number == 1


def test_config_operations():
    """Test configuration loading and saving."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config_file = tmp_path / "synq.toml"

        # Create and save config
        config = SynqConfig(
            metadata_path="myapp.models:metadata_obj",
            db_uri="sqlite:///test.db",
            migrations_dir="migrations",
            snapshot_dir="migrations/meta",
        )

        config.save_to_file(config_file)

        # Verify file was created
        assert config_file.exists()

        # Load config back
        loaded_config = SynqConfig.from_file(config_file)

        # Verify loaded config
        assert loaded_config.metadata_path == "myapp.models:metadata_obj"
        assert loaded_config.db_uri == "sqlite:///test.db"
        assert loaded_config.migrations_dir == "migrations"
        assert loaded_config.snapshot_dir == "migrations/meta"


if __name__ == "__main__":
    test_basic_snapshot_workflow()
    test_migration_manager_sql_generation()
    test_migration_file_operations()
    test_config_operations()
    print("All basic workflow tests passed!")
