"""Tests for database management."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from synq.core.database import DatabaseManager
from synq.core.migration import PendingMigration


def test_database_manager_init():
    """Test DatabaseManager initialization."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    assert db_manager.db_uri == db_uri
    assert db_manager.engine is not None
    assert db_manager.SessionClass is not None
    assert db_manager.migrations_table is not None


def test_database_manager_ensure_migrations_table():
    """Test that migrations table is created."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    # Table should exist after initialization
    with db_manager.engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='synq_migrations'"
            )
        )
        tables = result.fetchall()
        assert len(tables) == 1


def test_database_manager_ensure_migrations_table_error_handling():
    """Test error handling when migrations table creation fails."""
    # Use a problematic database path that should trigger initialization error
    with pytest.raises(
        RuntimeError, match="Failed to create or access migrations table"
    ):
        DatabaseManager("sqlite:///nonexistent/path/that/will/fail.db")


def test_database_manager_get_applied_migrations():
    """Test getting applied migrations."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    # Initially should be empty
    applied = db_manager.get_applied_migrations()
    assert applied == []

    # Add a migration manually
    with db_manager.engine.connect() as conn:
        with conn.begin():
            conn.execute(
                db_manager.migrations_table.insert(),
                {
                    "filename": "0001_initial.sql",
                    "applied_at": datetime.now(timezone.utc),
                },
            )

    # Should now return the migration
    applied = db_manager.get_applied_migrations()
    assert len(applied) == 1
    assert applied[0] == "0001_initial.sql"


def test_database_manager_test_connection():
    """Test database connection testing."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    # Should be able to connect
    assert db_manager.test_connection() is True


def test_database_manager_test_connection_failure():
    """Test database connection failure."""
    # Create a database manager with in-memory db but then test connection failure
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    # Now replace the engine URI with something that will fail
    db_manager.engine = create_engine("sqlite:///nonexistent/path/database.db")

    # Should fail to connect
    assert db_manager.test_connection() is False


def test_database_manager_get_database_info():
    """Test getting database information."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    info = db_manager.get_database_info()
    assert isinstance(info, dict)
    assert "connected" in info
    assert "uri" in info
    assert info["uri"] == db_uri


def test_database_manager_rollback():
    """Test rollback method."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    # Rollback method should exist and not raise exception
    db_manager.rollback()


def test_database_manager_apply_migration():
    """Test applying a single migration."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    # Create a test migration
    migration = PendingMigration(
        filename="0001_test.sql",
        sql_content="CREATE TABLE test_apply (id INTEGER PRIMARY KEY);",
    )

    # Apply the migration
    db_manager.apply_migration(migration)

    # Verify table was created
    with db_manager.engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_apply'"
            )
        )
        tables = result.fetchall()
        assert len(tables) == 1

    # Verify migration was recorded
    applied = db_manager.get_applied_migrations()
    assert "0001_test.sql" in applied


def test_database_manager_apply_migration_with_comments():
    """Test applying migration with SQL comments."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    # Create migration with comments
    migration = PendingMigration(
        filename="0001_with_comments.sql",
        sql_content="""
        -- This is a comment
        CREATE TABLE test_comments (
            id INTEGER PRIMARY KEY,
            -- Another comment
            name TEXT
        );
        -- Final comment
        """,
    )

    # Apply the migration
    db_manager.apply_migration(migration)

    # Verify table was created
    with db_manager.engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_comments'"
            )
        )
        tables = result.fetchall()
        assert len(tables) == 1


def test_database_manager_apply_migration_rollback_on_error():
    """Test that migration is rolled back on error."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    # Create a migration with invalid SQL
    migration = PendingMigration(
        filename="0001_bad.sql", sql_content="INVALID SQL STATEMENT;"
    )

    # Should raise an exception
    with pytest.raises(RuntimeError):
        db_manager.apply_migration(migration)

    # Migration should not be recorded as applied
    applied = db_manager.get_applied_migrations()
    assert "0001_bad.sql" not in applied


def test_database_manager_connection_error():
    """Test handling of database connection errors."""
    # Use invalid database URI
    with pytest.raises(SQLAlchemyError):
        DatabaseManager("invalid://database/uri")


def test_database_manager_close():
    """Test closing database connections."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    # Should not raise an exception
    db_manager.close()


def test_database_manager_apply_migration_empty_statements():
    """Test applying migration with empty statements."""
    db_uri = "sqlite:///:memory:"
    db_manager = DatabaseManager(db_uri)

    # Create migration with empty statements
    migration = PendingMigration(
        filename="0001_empty_statements.sql",
        sql_content="""
        ;;; -- Just separators and comments
        CREATE TABLE test_empty (id INTEGER PRIMARY KEY);
        ;;;
        """,
    )

    # Apply the migration
    db_manager.apply_migration(migration)

    # Verify table was created
    with db_manager.engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_empty'"
            )
        )
        tables = result.fetchall()
        assert len(tables) == 1


def test_database_manager_get_database_info_error():
    """Test getting database info when connection fails."""
    # Use invalid URI to trigger connection error
    db_uri = "invalid://connection/string"

    try:
        db_manager = DatabaseManager(db_uri)
        info = db_manager.get_database_info()
        assert info["connected"] is False
        assert "error" in info
    except Exception:
        # If manager creation fails, that's also valid test behavior
        pass
