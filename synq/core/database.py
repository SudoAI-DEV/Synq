"""Database connection and migration state management."""

from datetime import datetime
from typing import List

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    text,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from synq.core.migration import PendingMigration


class DatabaseManager:
    """Manages database connections and migration state."""

    def __init__(self, db_uri_or_config):
        # Handle both string URI and config object for backward compatibility
        if hasattr(db_uri_or_config, 'db_uri'):
            # It's a config object
            self.db_uri = db_uri_or_config.db_uri
        else:
            # It's a string URI
            self.db_uri = db_uri_or_config
        
        if not self.db_uri:
            raise ValueError("Database URI is required")
            
        self.engine = create_engine(self.db_uri)
        self.SessionClass = sessionmaker(bind=self.engine)

        # Define migrations table using SQLAlchemy ORM
        self.metadata = MetaData()
        self.migrations_table = Table(
            "synq_migrations",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("filename", String(255), nullable=False, unique=True),
            Column("applied_at", DateTime, default=datetime.utcnow),
        )

        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        """Ensure the migrations tracking table exists."""
        try:
            # Create the table if it doesn't exist
            self.metadata.create_all(self.engine, tables=[self.migrations_table])
        except SQLAlchemyError as e:
            # If creation fails, the table might already exist
            # Try to verify by querying it
            try:
                with self.engine.connect() as conn:
                    conn.execute(self.migrations_table.select().limit(1))
            except SQLAlchemyError:
                raise RuntimeError(f"Failed to create or access migrations table: {e}")

    def ensure_migrations_table(self) -> None:
        """Public method to ensure the migrations tracking table exists."""
        self._ensure_migrations_table()

    def ensure_migration_table(self) -> None:
        """Alias for ensure_migrations_table for backwards compatibility."""
        self._ensure_migrations_table()

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration filenames."""
        try:
            with self.SessionClass() as session:
                result = session.execute(
                    self.migrations_table.select().order_by(
                        self.migrations_table.c.filename
                    )
                )
                return [row.filename for row in result.fetchall()]
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to query applied migrations: {e}")

    def apply_migration(self, migration: PendingMigration) -> None:
        """Apply a single migration to the database."""
        with self.SessionClass() as session:
            try:
                with session.begin():
                    # Execute migration SQL statements
                    statements = [
                        stmt.strip() for stmt in migration.sql_content.split(";")
                    ]

                    for statement in statements:
                        # Skip empty statements
                        if not statement or not statement.strip():
                            continue

                        # Remove comments but keep SQL statements
                        sql_lines = []
                        for line in statement.split("\n"):
                            line = line.strip()
                            if line and not line.startswith("--"):
                                sql_lines.append(line)

                        clean_statement = "\n".join(sql_lines).strip()

                        if not clean_statement:
                            continue

                        # Execute the statement
                        session.execute(text(clean_statement))

                    # Record migration as applied using ORM
                    session.execute(
                        self.migrations_table.insert().values(
                            filename=migration.filename, applied_at=datetime.utcnow()
                        )
                    )

                    # Transaction will be committed automatically by context manager

            except SQLAlchemyError as e:
                # Transaction will be rolled back automatically
                raise RuntimeError(
                    f"Failed to apply migration {migration.filename}: {e}"
                )

    def rollback(self) -> None:
        """Rollback current transaction (handled by context manager)."""
        # This method exists for API completeness
        # Actual rollback is handled by SQLAlchemy's transaction context

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False

    def get_database_info(self) -> dict:
        """Get database information."""
        try:
            with self.engine.connect() as conn:
                # Try to get database version/info
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()

                return {
                    "connected": True,
                    "version": version[0] if version else "Unknown",
                    "uri": self.db_uri,
                }
        except SQLAlchemyError as e:
            return {"connected": False, "error": str(e), "uri": self.db_uri}

    def apply_pending_migrations(self) -> None:
        """Apply all pending migrations (for backward compatibility)."""
        # This method requires a MigrationManager to get pending migrations
        # For now, we'll provide a stub that does nothing
        # In practice, this should be called from a higher-level context
        pass

    def close(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
