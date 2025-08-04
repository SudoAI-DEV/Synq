"""Comprehensive test suite for Synq functionality."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table

from synq.cli.commands import generate, init
from synq.core.config import SynqConfig
from synq.core.database import DatabaseManager
from synq.core.diff import MigrationOperation, OperationType, SchemaDiffer
from synq.core.migration import MigrationManager
from synq.core.naming import MigrationNamer
from synq.core.snapshot import SnapshotManager


class TestComprehensiveWorkflow:
    """Test complete Synq workflows end-to-end."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_complete_project_initialization(self, temp_project_dir):
        """Test complete project setup from scratch."""
        # Change to temp directory
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(temp_project_dir)

            # Test init command
            init.init_command(
                metadata_path="test.models:metadata_obj",
                db_uri="sqlite:///test.db",
                migrations_dir="migrations",
            )

            # Verify files were created
            assert (temp_project_dir / "synq.toml").exists()
            assert (temp_project_dir / "migrations").exists()
            assert (temp_project_dir / "migrations" / "meta").exists()

            # Verify config content
            config_content = (temp_project_dir / "synq.toml").read_text()
            assert 'metadata_path = "test.models:metadata_obj"' in config_content
            assert "sqlite:///test.db" in config_content

        finally:
            os.chdir(original_cwd)

    def test_multiple_migration_generations(self, temp_project_dir):
        """Test generating multiple migrations in sequence."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_project_dir / "migrations"),
            snapshot_dir=str(temp_project_dir / "migrations" / "meta"),
            db_uri="sqlite:///test.db",
        )

        migration_manager = MigrationManager(config)

        # Create mock metadata for different migration stages
        from sqlalchemy import String

        # Stage 1: Initial tables
        metadata_v1 = MetaData()
        users_table = Table(
            "users",
            metadata_v1,
            Column("id", Integer, primary_key=True),
            Column("username", String(50), unique=True),
        )

        # Stage 2: Add email column
        metadata_v2 = MetaData()
        users_table_v2 = Table(
            "users",
            metadata_v2,
            Column("id", Integer, primary_key=True),
            Column("username", String(50), unique=True),
            Column("email", String(100), unique=True),
        )

        # Stage 3: Add posts table
        metadata_v3 = MetaData()
        users_table_v3 = Table(
            "users",
            metadata_v3,
            Column("id", Integer, primary_key=True),
            Column("username", String(50), unique=True),
            Column("email", String(100), unique=True),
        )
        posts_table = Table(
            "posts",
            metadata_v3,
            Column("id", Integer, primary_key=True),
            Column("title", String(200)),
            Column("user_id", Integer),
        )

        # Generate migrations for each stage
        migration_manager.create_migration(
            metadata_v1, "initial_tables", "Create initial tables"
        )
        migration_manager.create_migration(
            metadata_v2, "add_email", "Add email to users"
        )
        migration_manager.create_migration(metadata_v3, "add_posts", "Add posts table")

        # Verify migration files
        migration_files = sorted(config.migrations_path.glob("*.sql"))
        assert len(migration_files) == 3

        assert migration_files[0].name == "0000_initial_tables.sql"
        assert migration_files[1].name == "0001_add_email.sql"
        assert migration_files[2].name == "0002_add_posts.sql"

        # Verify snapshot files
        snapshot_files = sorted(config.snapshot_path.glob("*.json"))
        assert len(snapshot_files) == 3

    @pytest.mark.skip(reason="Test design issue - DatabaseManager connects immediately")
    def test_error_handling_and_recovery(self, temp_project_dir):
        """Test error handling in various scenarios."""
        config = SynqConfig(
            metadata_path="nonexistent.module:metadata",
            migrations_dir=str(temp_project_dir / "migrations"),
            snapshot_dir=str(temp_project_dir / "migrations" / "meta"),
            db_uri="sqlite:///nonexistent_directory/test.db",
        )

        # Test invalid metadata path
        migration_manager = MigrationManager(config)

        with pytest.raises(Exception):
            # Should fail to import nonexistent module
            from synq.utils.import_utils import import_from_string

            import_from_string("nonexistent.module:metadata")

        # Test invalid database URI
        db_manager = DatabaseManager(config)

        with pytest.raises(Exception):
            # Should fail to connect to invalid database
            db_manager.ensure_migration_table()

    def test_naming_system_comprehensive(self):
        """Test comprehensive naming scenarios."""
        namer = MigrationNamer()

        # Test various operation combinations
        test_cases = [
            # Single operations
            (
                [MigrationOperation(OperationType.CREATE_TABLE, "users", None, None)],
                "create_users_table",
            ),
            (
                [MigrationOperation(OperationType.DROP_TABLE, "old_table", None, None)],
                "delete_old_table_table",
            ),
            (
                [MigrationOperation(OperationType.ADD_COLUMN, "users", "email", None)],
                "add_email_to_users",
            ),
            (
                [
                    MigrationOperation(
                        OperationType.DROP_COLUMN, "users", "old_col", None
                    )
                ],
                "remove_old_col_from_users",
            ),
            # Multiple table creation (initial migration)
            (
                [
                    MigrationOperation(OperationType.CREATE_TABLE, "users", None, None),
                    MigrationOperation(OperationType.CREATE_TABLE, "posts", None, None),
                    MigrationOperation(
                        OperationType.CREATE_TABLE, "comments", None, None
                    ),
                ],
                "initial_migration",
            ),
            # Multiple operations on same table
            (
                [
                    MigrationOperation(
                        OperationType.ADD_COLUMN, "users", "email", None
                    ),
                    MigrationOperation(
                        OperationType.ADD_COLUMN, "users", "phone", None
                    ),
                ],
                "add_columns_to_users",
            ),
            # Mixed operations
            (
                [
                    MigrationOperation(
                        OperationType.CREATE_TABLE, "categories", None, None
                    ),
                    MigrationOperation(
                        OperationType.ADD_COLUMN, "users", "category_id", None
                    ),
                ],
                "update_schema",
            ),
        ]

        for operations, expected_name in test_cases:
            result = namer.generate_name(operations)
            assert result == expected_name, f"Expected {expected_name}, got {result}"

    def test_cli_integration(self, temp_project_dir):
        """Test CLI commands integration."""
        original_cwd = Path.cwd()
        try:
            import os

            os.chdir(temp_project_dir)

            # Create a simple metadata module
            models_file = temp_project_dir / "models.py"
            models_file.write_text("""
from sqlalchemy import MetaData, Table, Column, Integer, String

metadata_obj = MetaData()

users_table = Table(
    "users", metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("name", String(50)),
)
""")

            # Test init command
            with patch("builtins.input", return_value="models:metadata_obj"):
                init.init_command(
                    metadata_path="models:metadata_obj",
                    db_uri="sqlite:///test.db",
                    migrations_dir="migrations",
                )

            # Test generate command
            with patch("synq.utils.import_utils.import_from_string") as mock_import:
                from sqlalchemy import Column, Integer, MetaData, Table

                metadata = MetaData()
                Table("users", metadata, Column("id", Integer, primary_key=True))
                mock_import.return_value = metadata

                generate.generate_command(
                    description="Create users table", config_path=None, custom_name=None
                )

            # Verify migration was created
            migration_files = list((temp_project_dir / "migrations").glob("*.sql"))
            assert len(migration_files) >= 1

        finally:
            os.chdir(original_cwd)

    def test_concurrent_migration_detection(self, temp_project_dir):
        """Test detection of concurrent migrations."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_project_dir / "migrations"),
            snapshot_dir=str(temp_project_dir / "migrations" / "meta"),
            db_uri="sqlite:///test.db",
        )

        # Create migrations directory
        config.migrations_path.mkdir(parents=True, exist_ok=True)
        config.snapshot_path.mkdir(parents=True, exist_ok=True)

        # Simulate concurrent migrations (same number)
        migration1 = config.migrations_path / "0001_feature_a.sql"
        migration2 = config.migrations_path / "0001_feature_b.sql"

        migration1.write_text("CREATE TABLE feature_a (id INTEGER);")
        migration2.write_text("CREATE TABLE feature_b (id INTEGER);")

        db_manager = DatabaseManager(config)
        migration_manager = MigrationManager(config)

        # Should detect conflicting migration numbers
        migrations = migration_manager.get_pending_migrations(db_manager)
        migration_numbers = [m.filename.split("_")[0] for m in migrations]

        # Should have duplicate numbers
        assert migration_numbers.count("0001") == 2

    def test_schema_validation(self, temp_project_dir):
        """Test schema validation and consistency checks."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_project_dir / "migrations"),
            snapshot_dir=str(temp_project_dir / "migrations" / "meta"),
            db_uri="sqlite:///test.db",
        )

        snapshot_manager = SnapshotManager(config)

        # Create a complex metadata with constraints
        from sqlalchemy import (
            ForeignKey,
            Index,
            String,
            UniqueConstraint,
        )

        metadata = MetaData()

        users_table = Table(
            "users",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("username", String(50), nullable=False),
            Column("email", String(100), nullable=False),
            UniqueConstraint("username", "email", name="uq_user_credentials"),
        )

        posts_table = Table(
            "posts",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("title", String(200), nullable=False),
            Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
            Index("idx_posts_user_id", "user_id"),
        )

        # Create snapshot
        snapshot = snapshot_manager.create_snapshot(metadata)

        # Verify constraint capture
        users_table = None
        posts_table = None
        for table in snapshot.tables:
            if table.name == "users":
                users_table = table
            elif table.name == "posts":
                posts_table = table

        assert users_table is not None
        assert posts_table is not None

        # Check foreign keys are captured
        assert len(posts_table.foreign_keys) > 0
        fk = posts_table.foreign_keys[0]
        assert fk.referred_table == "users"
        assert "id" in fk.referred_columns

        # Check indexes are captured
        assert len(posts_table.indexes) > 0
        idx = posts_table.indexes[0]
        assert idx.name == "idx_posts_user_id"

    def test_migration_dependencies(self, temp_project_dir):
        """Test migration dependency handling."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_project_dir / "migrations"),
            snapshot_dir=str(temp_project_dir / "migrations" / "meta"),
            db_uri="sqlite:///test.db",
        )

        config.migrations_path.mkdir(parents=True, exist_ok=True)

        # Create migrations with dependencies
        migrations = [
            ("0001_create_users.sql", "CREATE TABLE users (id INTEGER PRIMARY KEY);"),
            (
                "0002_create_posts.sql",
                "CREATE TABLE posts (id INTEGER, user_id INTEGER, FOREIGN KEY(user_id) REFERENCES users(id));",
            ),
            (
                "0003_add_user_email.sql",
                "ALTER TABLE users ADD COLUMN email VARCHAR(100);",
            ),
        ]

        for filename, content in migrations:
            (config.migrations_path / filename).write_text(content)

        db_manager = DatabaseManager(config)
        migration_manager = MigrationManager(config)
        pending = migration_manager.get_pending_migrations(db_manager)

        # Should be ordered correctly
        assert len(pending) == 3
        assert pending[0].filename == "0001_create_users.sql"
        assert pending[1].filename == "0002_create_posts.sql"
        assert pending[2].filename == "0003_add_user_email.sql"

    def test_performance_with_large_schema(self, temp_project_dir):
        """Test performance with large schema definitions."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_project_dir / "migrations"),
            snapshot_dir=str(temp_project_dir / "migrations" / "meta"),
            db_uri="sqlite:///test.db",
        )

        # Create large metadata (50 tables, 10 columns each)
        from sqlalchemy import String

        metadata = MetaData()

        for table_idx in range(50):
            columns = [Column("id", Integer, primary_key=True)]
            for col_idx in range(9):  # 9 more columns
                columns.append(Column(f"col_{col_idx}", String(100)))

            Table(f"table_{table_idx}", metadata, *columns)

        # Test snapshot creation performance
        import time

        snapshot_manager = SnapshotManager(config)

        start_time = time.time()
        snapshot = snapshot_manager.create_snapshot(metadata)
        end_time = time.time()

        # Should complete quickly (adjust threshold as needed)
        assert end_time - start_time < 5.0  # 5 seconds max

        # Verify all tables captured
        assert len(snapshot["tables"]) == 50

        # Test diff generation performance
        diff_generator = SchemaDiffer()

        start_time = time.time()
        operations = diff_generator.detect_changes(None, snapshot)
        end_time = time.time()

        # Should complete quickly
        assert end_time - start_time < 2.0  # 2 seconds max

        # Should detect all table creations
        create_ops = [
            op for op in operations if op.operation_type == OperationType.CREATE_TABLE
        ]
        assert len(create_ops) == 50


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_metadata(self, temp_dir):
        """Test handling of empty metadata."""

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_dir / "migrations"),
            snapshot_dir=str(temp_dir / "migrations" / "meta"),
        )

        snapshot_manager = SnapshotManager(config)
        empty_metadata = MetaData()

        # Should handle empty metadata gracefully
        snapshot = snapshot_manager.create_snapshot(empty_metadata)
        assert snapshot["tables"] == {}

    def test_duplicate_table_names(self):
        """Test handling of duplicate table names."""

        metadata1 = MetaData()
        metadata2 = MetaData()

        # Same table name in different metadata objects
        Table("users", metadata1, Column("id", Integer, primary_key=True))
        Table(
            "users",
            metadata2,
            Column("id", Integer, primary_key=True),
            Column("name", String(50)),
        )

        diff_generator = SchemaDiffer()

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(Path("migrations")),
            snapshot_dir=str(Path("migrations/meta")),
        )

        snapshot_manager = SnapshotManager(config)

        snapshot1 = snapshot_manager.create_snapshot(metadata1)
        snapshot2 = snapshot_manager.create_snapshot(metadata2)

        operations = diff_generator.generate_diff(snapshot1, snapshot2)

        # Should detect column addition
        add_column_ops = [
            op for op in operations if op.operation_type == OperationType.ADD_COLUMN
        ]
        assert len(add_column_ops) >= 1

    def test_special_characters_in_names(self):
        """Test handling of special characters in table/column names."""
        namer = MigrationNamer()

        # Test name sanitization
        test_cases = [
            ("user-profiles", "user_profiles"),
            ("user profiles", "user_profiles"),
            ("user@profiles", "user_profiles"),
            ("user__profiles", "user_profiles"),
            ("__user_profiles__", "user_profiles"),
            ("123users", "123users"),  # Numbers are allowed
            ("", "unnamed"),
            ("   ", "unnamed"),
        ]

        for input_name, expected in test_cases:
            result = namer._sanitize_name(input_name)
            assert result == expected, (
                f"Input: {input_name}, Expected: {expected}, Got: {result}"
            )

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
