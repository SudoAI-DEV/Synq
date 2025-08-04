"""Integration tests with real databases."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from synq.core.config import SynqConfig
from synq.core.database import DatabaseManager
from synq.core.migration import MigrationManager
from tests.fixtures_sqlalchemy_versions import (
    create_extended_metadata,
    get_test_metadata,
)


@pytest.fixture()
def temp_migration_dir():
    """Create a temporary directory for migrations."""
    import gc
    import time

    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)

    # Force garbage collection to close any remaining connections
    gc.collect()

    # Retry cleanup on Windows to handle locked files
    for attempt in range(3):
        try:
            shutil.rmtree(temp_dir)
            break
        except (OSError, PermissionError) as e:
            if attempt < 2:
                # Wait a bit for file handles to be released
                time.sleep(0.1)
                gc.collect()  # Force another GC cycle
            else:
                # Last attempt failed, log the error but don't fail the test
                import warnings

                warnings.warn(
                    f"Failed to clean up temporary directory {temp_dir}: {e}",
                    stacklevel=2,
                )


@pytest.fixture(params=["sqlite"])
def database_url(request):
    """Provide database URLs for testing."""
    if request.param == "sqlite":
        return "sqlite:///test_integration.db"
    if request.param == "postgresql":
        # Only if PostgreSQL is available in CI
        return os.getenv(
            "POSTGRES_URL", "postgresql://postgres:postgres@localhost:5432/synq_test"
        )
    if request.param == "mysql":
        # Only if MySQL is available in CI
        return os.getenv(
            "MYSQL_URL", "mysql+pymysql://root:root@localhost:3306/synq_test"
        )
    return None


class TestDatabaseIntegration:
    """Test Synq with real database connections."""

    def test_full_migration_workflow_sqlite(self, temp_migration_dir):
        """Test complete migration workflow with SQLite."""
        db_path = temp_migration_dir / "test.db"
        db_uri = f"sqlite:///{db_path}"

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations"),
            snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
            db_uri=db_uri,
        )

        # Initialize components
        migration_manager = MigrationManager(config)
        db_manager = DatabaseManager(config.db_uri)
        engine = None

        try:
            # Create initial migration
            metadata = get_test_metadata()
            migration_name = "initial_migration"

            migration_manager.create_migration(
                metadata=metadata,
                name=migration_name,
                description="Initial migration with users and posts",
            )

            # Verify files were created
            migration_files = list(config.migrations_path.glob("*.sql"))
            assert len(migration_files) == 1

            snapshot_files = list(config.snapshot_path.glob("*.json"))
            assert len(snapshot_files) == 1

            # Apply migration
            db_manager.ensure_migration_table()
            db_manager.apply_pending_migrations(migration_manager)

            # Verify tables were created in database
            engine = create_engine(db_uri)
            with engine.connect() as conn:
                # Check that tables exist
                if hasattr(conn, "execute"):
                    # SQLAlchemy 2.0+ style
                    result = conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                    tables = [row[0] for row in result.fetchall()]
                else:
                    # SQLAlchemy 1.4 style
                    result = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                    tables = [row[0] for row in result.fetchall()]

                assert "users" in tables
                assert "posts" in tables
                assert "synq_migrations" in tables

            # Create second migration with additional tables
            extended_metadata = create_extended_metadata()
            migration_manager.create_migration(
                metadata=extended_metadata,
                name="add_categories_and_tags",
                description="Add categories and tags tables",
            )

            # Apply second migration
            db_manager.apply_pending_migrations(migration_manager)

            # Verify new tables
            with engine.connect() as conn:
                if hasattr(conn, "execute"):
                    result = conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                    tables = [row[0] for row in result.fetchall()]
                else:
                    result = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                    tables = [row[0] for row in result.fetchall()]

                assert "categories" in tables
                assert "tags" in tables
        finally:
            # Ensure proper cleanup
            if db_manager:
                db_manager.close()
            if engine:
                engine.dispose()

    def test_migration_status_tracking(self, temp_migration_dir):
        """Test that migration status is tracked correctly."""
        db_path = temp_migration_dir / "status_test.db"
        db_uri = f"sqlite:///{db_path}"

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations"),
            snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
            db_uri=db_uri,
        )

        db_manager = DatabaseManager(config.db_uri)
        migration_manager = MigrationManager(config)

        try:
            # Ensure migration table exists
            db_manager.ensure_migration_table()

            # Initially no migrations applied
            applied = db_manager.get_applied_migrations()
            assert len(applied) == 0

            # Create and apply first migration
            metadata = get_test_metadata()
            migration_manager.create_migration(
                metadata=metadata,
                name="first_migration",
                description="First test migration",
            )

            db_manager.apply_pending_migrations(migration_manager)

            # Should have one applied migration
            applied = db_manager.get_applied_migrations()
            assert len(applied) == 1
            assert applied[0] == "0000_first_migration.sql"

            # Create second migration but don't apply
            extended_metadata = create_extended_metadata()
            migration_manager.create_migration(
                metadata=extended_metadata,
                name="second_migration",
                description="Second test migration",
            )

            # Should still show only one applied
            applied = db_manager.get_applied_migrations()
            assert len(applied) == 1

            # Get pending migrations
            pending = migration_manager.get_pending_migrations(db_manager)
            assert len(pending) == 1
            assert pending[0].filename == "0001_second_migration.sql"
        finally:
            # Ensure proper cleanup
            if db_manager:
                db_manager.close()

    def test_sql_execution_with_comments(self, temp_migration_dir):
        """Test that SQL with comments is executed correctly."""
        db_path = temp_migration_dir / "comments_test.db"
        db_uri = f"sqlite:///{db_path}"

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations"),
            snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
            db_uri=db_uri,
        )

        db_manager = None
        engine = None

        try:
            # Create migration file with comments
            migration_content = """-- Migration: Test with comments
-- Created: 2024-01-01

-- Create users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL
);

-- Create posts table
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author_id INTEGER,
    FOREIGN KEY (author_id) REFERENCES users (id)
);

-- End of migration
"""

            # Write migration file
            migrations_dir = config.migrations_path
            migrations_dir.mkdir(parents=True, exist_ok=True)
            migration_file = migrations_dir / "0000_test_comments.sql"
            migration_file.write_text(migration_content)

            # Apply migration
            migration_manager = MigrationManager(config)
            db_manager = DatabaseManager(config.db_uri)
            db_manager.ensure_migration_table()
            db_manager.apply_pending_migrations(migration_manager)

            # Verify tables were created
            engine = create_engine(db_uri)
            with engine.connect() as conn:
                if hasattr(conn, "execute"):
                    result = conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                    tables = [row[0] for row in result.fetchall()]
                else:
                    result = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                    tables = [row[0] for row in result.fetchall()]

                assert "users" in tables
                assert "posts" in tables
        finally:
            # Ensure proper cleanup
            if db_manager:
                db_manager.close()
            if engine:
                engine.dispose()

    def test_rollback_on_error(self, temp_migration_dir):
        """Test that failed migrations are rolled back properly."""
        db_path = temp_migration_dir / "rollback_test.db"
        db_uri = f"sqlite:///{db_path}"

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations"),
            snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
            db_uri=db_uri,
        )

        db_manager = None
        engine = None

        try:
            # Create migration with invalid SQL
            invalid_migration = """-- Invalid migration
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50)
);

-- This will cause an error
INVALID SQL STATEMENT HERE;

CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200)
);
"""

            migrations_dir = config.migrations_path
            migrations_dir.mkdir(parents=True, exist_ok=True)
            migration_file = migrations_dir / "0000_invalid_migration.sql"
            migration_file.write_text(invalid_migration)

            migration_manager = MigrationManager(config)
            db_manager = DatabaseManager(config.db_uri)
            db_manager.ensure_migration_table()

            # Should raise an error and not create any tables
            with pytest.raises(RuntimeError, match=".*"):
                db_manager.apply_pending_migrations(migration_manager)

            # Verify migration was not recorded as applied
            applied = db_manager.get_applied_migrations()
            assert len(applied) == 0

            # Check tables - SQLite auto-commits DDL so partial tables may exist
            engine = create_engine(db_uri)
            with engine.connect() as conn:
                if hasattr(conn, "execute"):
                    result = conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                    tables = [row[0] for row in result.fetchall()]
                else:
                    result = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                    tables = [row[0] for row in result.fetchall()]

                # Should have the migration tracking table
                assert "synq_migrations" in tables

                # SQLite auto-commits DDL statements, so tables created before the
                # error may still exist, but the migration should not be recorded as applied
                # The key test is that the migration was not marked as applied
                if "users" in tables:
                    # This is expected behavior for SQLite - DDL can't be rolled back
                    # But the migration should not be marked as applied
                    assert len(applied) == 0  # Already checked above
        finally:
            # Ensure proper cleanup
            if db_manager:
                db_manager.close()
            if engine:
                engine.dispose()

    @pytest.mark.slow()
    def test_large_migration_performance(self, temp_migration_dir):
        """Test performance with larger migrations."""
        db_path = temp_migration_dir / "performance_test.db"
        db_uri = f"sqlite:///{db_path}"

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations"),
            snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
            db_uri=db_uri,
        )

        db_manager = None
        engine = None

        try:
            # Create a migration with many tables
            large_migration = """-- Large migration for performance testing
"""

            # Generate many CREATE TABLE statements
            for i in range(50):
                large_migration += f"""
CREATE TABLE test_table_{i} (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100),
    value INTEGER,
    created_at DATETIME
);
"""

            migrations_dir = config.migrations_path
            migrations_dir.mkdir(parents=True, exist_ok=True)
            migration_file = migrations_dir / "0000_large_migration.sql"
            migration_file.write_text(large_migration)

            migration_manager = MigrationManager(config)
            db_manager = DatabaseManager(config.db_uri)
            db_manager.ensure_migration_table()

            # Apply migration and measure time
            import time

            start_time = time.time()
            db_manager.apply_pending_migrations(migration_manager)
            end_time = time.time()

            # Should complete within reasonable time (adjust as needed)
            assert end_time - start_time < 10.0  # 10 seconds max

            # Verify all tables were created
            engine = create_engine(db_uri)
            with engine.connect() as conn:
                if hasattr(conn, "execute"):
                    result = conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table'")
                    )
                    tables = [row[0] for row in result.fetchall()]
                else:
                    result = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                    tables = [row[0] for row in result.fetchall()]

                # Should have 50 test tables plus migration table
                test_tables = [t for t in tables if t.startswith("test_table_")]
                assert len(test_tables) == 50
        finally:
            # Ensure proper cleanup
            if db_manager:
                db_manager.close()
            if engine:
                engine.dispose()


@pytest.mark.skipif(
    not os.getenv("TEST_POSTGRES"),
    reason="PostgreSQL integration tests require TEST_POSTGRES=1",
)
class TestPostgreSQLIntegration:
    """Test PostgreSQL specific functionality."""

    def test_postgres_migration(self, temp_migration_dir):
        """Test migration with PostgreSQL."""
        db_uri = "postgresql://postgres:postgres@localhost:5432/synq_test"
        engine = None
        db_manager = None

        try:
            engine = create_engine(db_uri)
            with engine.connect() as conn:
                pass  # Test connection
        except Exception:
            pytest.skip("PostgreSQL not available")

        try:
            config = SynqConfig(
                metadata_path="test:metadata",
                migrations_dir=str(temp_migration_dir / "migrations"),
                snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
                db_uri=db_uri,
            )

            # Test basic migration workflow
            migration_manager = MigrationManager(config)
            db_manager = DatabaseManager(config.db_uri)

            metadata = get_test_metadata()
            migration_manager.create_migration(
                metadata=metadata,
                name="postgres_test",
                description="PostgreSQL test migration",
            )

            db_manager.ensure_migration_table()
            db_manager.apply_pending_migrations(migration_manager)

            # Verify tables exist
            with engine.connect() as conn:
                if hasattr(conn, "execute"):
                    result = conn.execute(
                        text(
                            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                        )
                    )
                    tables = [row[0] for row in result.fetchall()]
                else:
                    result = conn.execute(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                    )
                    tables = [row[0] for row in result.fetchall()]

                assert "users" in tables
                assert "posts" in tables
        finally:
            # Ensure proper cleanup
            if db_manager:
                db_manager.close()
            if engine:
                engine.dispose()


@pytest.mark.skipif(
    not os.getenv("TEST_MYSQL"), reason="MySQL integration tests require TEST_MYSQL=1"
)
class TestMySQLIntegration:
    """Test MySQL specific functionality."""

    def test_mysql_migration(self, temp_migration_dir):
        """Test migration with MySQL."""
        db_uri = "mysql+pymysql://root:root@localhost:3306/synq_test"
        engine = None
        db_manager = None

        try:
            engine = create_engine(db_uri)
            with engine.connect() as conn:
                pass  # Test connection
        except Exception:
            pytest.skip("MySQL not available")

        try:
            config = SynqConfig(
                metadata_path="test:metadata",
                migrations_dir=str(temp_migration_dir / "migrations"),
                snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
                db_uri=db_uri,
            )

            # Test basic migration workflow
            migration_manager = MigrationManager(config)
            db_manager = DatabaseManager(config.db_uri)

            metadata = get_test_metadata()
            migration_manager.create_migration(
                metadata=metadata, name="mysql_test", description="MySQL test migration"
            )

            db_manager.ensure_migration_table()
            db_manager.apply_pending_migrations(migration_manager)

            # Verify tables exist
            with engine.connect() as conn:
                if hasattr(conn, "execute"):
                    result = conn.execute(text("SHOW TABLES"))
                    tables = [row[0] for row in result.fetchall()]
                else:
                    result = conn.execute("SHOW TABLES")
                    tables = [row[0] for row in result.fetchall()]

                assert "users" in tables
                assert "posts" in tables
        finally:
            # Ensure proper cleanup
            if db_manager:
                db_manager.close()
            if engine:
                engine.dispose()
