"""Test compatibility with both SQLAlchemy 1.4 and 2.0."""

import pytest

from synq.core.config import SynqConfig
from synq.core.diff import SchemaDiffer
from synq.core.migration import MigrationManager
from synq.core.snapshot import SnapshotManager
from tests.fixtures_sqlalchemy_versions import (
    IS_SQLALCHEMY_2,
    create_extended_metadata,
    get_sqlalchemy_version_info,
    get_test_metadata,
)


class TestSQLAlchemyCompatibility:
    """Test Synq compatibility with different SQLAlchemy versions."""

    def test_sqlalchemy_version_detection(self):
        """Test that we can detect SQLAlchemy version correctly."""
        version_info = get_sqlalchemy_version_info()

        assert "version" in version_info
        assert "version_tuple" in version_info
        assert "is_v2" in version_info
        assert "major" in version_info
        assert "minor" in version_info

        # Should be either 1.4+ or 2.0+
        major, minor = version_info["version_tuple"]
        assert (major == 1 and minor >= 4) or major >= 2

    def test_metadata_creation_both_versions(self):
        """Test metadata creation works with both SQLAlchemy versions."""
        metadata = get_test_metadata()

        # Should have users and posts tables
        assert "users" in metadata.tables
        assert "posts" in metadata.tables

        # Check basic table structure
        users_table = metadata.tables["users"]
        assert "id" in users_table.columns
        assert "username" in users_table.columns
        assert "email" in users_table.columns

        posts_table = metadata.tables["posts"]
        assert "id" in posts_table.columns
        assert "title" in posts_table.columns
        assert "author_id" in posts_table.columns

    def test_snapshot_creation_both_versions(self, tmp_path):
        """Test snapshot creation works with both SQLAlchemy versions."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(tmp_path / "migrations"),
            snapshot_dir=str(tmp_path / "migrations" / "meta"),
        )

        snapshot_manager = SnapshotManager(config)
        metadata = get_test_metadata()

        # Create snapshot
        snapshot = snapshot_manager.create_snapshot(metadata)

        # Verify snapshot structure
        assert hasattr(snapshot, "tables")
        table_names = [table.name for table in snapshot.tables]
        assert "users" in table_names
        assert "posts" in table_names

        # Check users table structure
        users_table = next(table for table in snapshot.tables if table.name == "users")
        assert hasattr(users_table, "columns")
        column_names = [col.name for col in users_table.columns]
        assert "id" in column_names
        assert "username" in column_names

        # Verify column types are serialized correctly
        id_column = next(col for col in users_table.columns if col.name == "id")
        assert id_column.type.upper() in ["INTEGER", "INT"]
        assert id_column.primary_key is True

    def test_diff_generation_both_versions(self, tmp_path):
        """Test diff generation works with both SQLAlchemy versions."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(tmp_path / "migrations"),
            snapshot_dir=str(tmp_path / "migrations" / "meta"),
        )

        snapshot_manager = SnapshotManager(config)
        diff_generator = SchemaDiffer()

        # Create initial metadata
        initial_metadata = get_test_metadata()
        initial_snapshot = snapshot_manager.create_snapshot(initial_metadata)

        # Create extended metadata (with more tables)
        extended_metadata = create_extended_metadata()
        new_snapshot = snapshot_manager.create_snapshot(extended_metadata)

        # Generate diff
        operations = diff_generator.detect_changes(initial_snapshot, new_snapshot)

        # Should detect new tables
        assert len(operations) >= 2  # At least categories and tags tables

        # Check that operations are valid
        for op in operations:
            assert hasattr(op, "operation_type")
            assert hasattr(op, "table_name")

    def test_migration_sql_generation_both_versions(self, tmp_path):
        """Test SQL generation works with both SQLAlchemy versions."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(tmp_path / "migrations"),
            snapshot_dir=str(tmp_path / "migrations" / "meta"),
            db_uri="sqlite:///:memory:",
        )

        migration_manager = MigrationManager(config)
        metadata = get_test_metadata()

        # Generate SQL for creating tables
        sql_statements = migration_manager._generate_sql_for_metadata(metadata)

        # Should have CREATE TABLE statements
        sql_text = "\n".join(sql_statements)
        assert "CREATE TABLE users" in sql_text
        assert "CREATE TABLE posts" in sql_text

        # Check for proper column definitions
        assert "username" in sql_text
        assert "email" in sql_text
        assert "title" in sql_text

    @pytest.mark.skipif(not IS_SQLALCHEMY_2, reason="SQLAlchemy 2.0+ specific test")
    def test_sqlalchemy_2_features(self):
        """Test SQLAlchemy 2.0+ specific features."""
        from tests.fixtures_sqlalchemy_versions import Post, User

        # Test that we can access the declarative models
        assert hasattr(User, "__tablename__")
        assert hasattr(Post, "__tablename__")

        # Test relationships are defined
        assert hasattr(User, "posts")
        assert hasattr(Post, "author")

        # Test mapped column annotations
        assert hasattr(User, "__annotations__")
        assert "id" in User.__annotations__
        assert "username" in User.__annotations__

    @pytest.mark.skipif(IS_SQLALCHEMY_2, reason="SQLAlchemy 1.4 specific test")
    def test_sqlalchemy_1_4_features(self):
        """Test SQLAlchemy 1.4 specific features."""
        from tests.fixtures_sqlalchemy_versions import (
            posts_table,
            users_table,
        )

        # Test that we can access the Table objects
        assert users_table.name == "users"
        assert posts_table.name == "posts"

        # Test foreign key relationships
        assert len(posts_table.foreign_keys) > 0

        # Test column access
        assert "id" in users_table.columns
        assert "username" in users_table.columns
        assert "author_id" in posts_table.columns

    def test_column_type_serialization_both_versions(self, tmp_path):
        """Test that column types are serialized consistently across versions."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(tmp_path / "migrations"),
            snapshot_dir=str(tmp_path / "migrations" / "meta"),
        )

        snapshot_manager = SnapshotManager(config)
        metadata = get_test_metadata()
        snapshot = snapshot_manager.create_snapshot(metadata)

        # Check users table column types
        users_columns = snapshot["tables"]["users"]["columns"]

        # ID column should be integer/primary key
        id_col = users_columns["id"]
        assert id_col["primary_key"] is True
        assert id_col["nullable"] is False

        # Username should be string with length
        username_col = users_columns["username"]
        assert (
            "VARCHAR" in username_col["type"].upper()
            or "STRING" in username_col["type"].upper()
        )

        # Email should have unique constraint
        email_col = users_columns["email"]
        assert email_col["unique"] is True

    def test_constraint_handling_both_versions(self, tmp_path):
        """Test that constraints are handled properly in both versions."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(tmp_path / "migrations"),
            snapshot_dir=str(tmp_path / "migrations" / "meta"),
        )

        snapshot_manager = SnapshotManager(config)
        metadata = get_test_metadata()
        snapshot = snapshot_manager.create_snapshot(metadata)

        # Check constraint serialization
        users_table = next(table for table in snapshot.tables if table.name == "users")

        # Should capture unique constraints
        username_col = next(
            col for col in users_table.columns if col.name == "username"
        )
        email_col = next(col for col in users_table.columns if col.name == "email")

        assert username_col.unique is True
        assert email_col.unique is True

        # Check foreign key constraints in posts table
        posts_table = next(table for table in snapshot.tables if table.name == "posts")

        # Foreign key information should be captured in table foreign_keys
        if posts_table.foreign_keys:
            fk_tables = [fk.referred_table for fk in posts_table.foreign_keys]
            assert "users" in fk_tables


class TestVersionSpecificBehavior:
    """Test behavior that differs between SQLAlchemy versions."""

    def test_metadata_reflection_compatibility(self):
        """Test that our metadata handling is compatible across versions."""
        metadata = get_test_metadata()

        # Basic metadata operations should work
        table_names = list(metadata.tables.keys())
        assert "users" in table_names
        assert "posts" in table_names

        # Table access should work
        users_table = metadata.tables["users"]
        posts_table = metadata.tables["posts"]

        assert users_table is not None
        assert posts_table is not None

    def test_sql_generation_dialect_compatibility(self, tmp_path):
        """Test SQL generation works with different dialects."""
        from sqlalchemy import create_engine

        # Test with SQLite (most compatible)
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(tmp_path / "migrations"),
            snapshot_dir=str(tmp_path / "migrations" / "meta"),
            db_uri="sqlite:///:memory:",
        )

        migration_manager = MigrationManager(config)
        metadata = get_test_metadata()

        # Should generate valid SQLite SQL
        sql_statements = migration_manager._generate_sql_for_metadata(metadata)
        assert len(sql_statements) >= 2  # At least 2 CREATE TABLE statements

        # Verify SQL is valid by creating engine
        engine = create_engine(config.db_uri)

        # Should be able to execute the SQL
        from sqlalchemy import text

        with engine.connect() as conn:
            if IS_SQLALCHEMY_2:
                for stmt in sql_statements:
                    conn.execute(text(stmt))
                conn.commit()
            else:
                for stmt in sql_statements:
                    conn.execute(stmt)

    def test_import_compatibility(self):
        """Test that imports work correctly for both versions."""
        # These imports should work regardless of SQLAlchemy version
        from synq.core.config import SynqConfig
        from synq.core.diff import SchemaDiffer
        from synq.core.migration import MigrationManager
        from synq.core.snapshot import SnapshotManager

        # Should be able to instantiate core classes
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir="migrations",
            snapshot_dir="migrations/meta",
        )

        snapshot_manager = SnapshotManager(config)
        diff_generator = SchemaDiffer()
        migration_manager = MigrationManager(config)

        assert snapshot_manager is not None
        assert diff_generator is not None
        assert migration_manager is not None
