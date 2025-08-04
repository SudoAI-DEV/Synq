"""Database connection and migration state management."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    pass

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
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from synq.core.migration import PendingMigration


class DatabaseManager:
    """Manages database connections and migration state."""

    def __init__(self, db_uri_or_config: Union[str, Any]) -> None:
        # Handle both string URI and config object for backward compatibility
        if hasattr(db_uri_or_config, "db_uri"):
            # It's a config object
            self.db_uri = db_uri_or_config.db_uri
            self.config = db_uri_or_config
        else:
            # It's a string URI
            self.db_uri = db_uri_or_config
            self.config = None

        if not self.db_uri:
            raise ValueError("Database URI is required")

        self.engine: Engine = create_engine(self.db_uri)
        self.SessionClass = sessionmaker(bind=self.engine)

        # Define migrations table using SQLAlchemy ORM
        self.metadata: MetaData = MetaData()
        self.migrations_table: Table = Table(
            "synq_migrations",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("filename", String(255), nullable=False, unique=True),
            Column("applied_at", DateTime, default=lambda: datetime.now(timezone.utc)),
        )

        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        """Ensure the migrations tracking table exists."""
        try:
            # Create the table if it doesn't exist
            self.metadata.create_all(self.engine, tables=[self.migrations_table])
        except SQLAlchemyError:
            # If creation fails, the table might already exist
            # Try to verify by querying it
            try:
                with self.engine.connect() as conn:
                    conn.execute(self.migrations_table.select().limit(1))
            except SQLAlchemyError as exc:
                raise RuntimeError(
                    f"Failed to create or access migrations table: {exc}"
                ) from exc

    def ensure_migrations_table(self) -> None:
        """Public method to ensure the migrations tracking table exists."""
        self._ensure_migrations_table()

    def ensure_migration_table(self) -> None:
        """Alias for ensure_migrations_table for backwards compatibility."""
        self._ensure_migrations_table()

    def get_applied_migrations(self) -> list[str]:
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
            raise RuntimeError(f"Failed to query applied migrations: {e}") from e

    def apply_migration(self, migration: PendingMigration) -> None:
        """Apply a single migration to the database."""
        with self.engine.connect() as conn, conn.begin() as trans:
            try:
                # Execute migration SQL statements
                statements = [stmt.strip() for stmt in migration.sql_content.split(";")]

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
                    conn.execute(text(clean_statement))

                # Record migration as applied
                conn.execute(
                    self.migrations_table.insert().values(
                        filename=migration.filename,
                        applied_at=datetime.now(timezone.utc),
                    )
                )

                # Explicitly commit the transaction
                trans.commit()

            except Exception as e:
                # Explicitly rollback the transaction
                trans.rollback()
                raise RuntimeError(
                    f"Failed to apply migration {migration.filename}: {e}"
                ) from e

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

    def get_database_info(self) -> dict[str, Any]:
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

    def apply_pending_migrations(self, migration_manager: Optional[Any] = None) -> None:
        """Apply all pending migrations (for backward compatibility)."""
        if migration_manager is None:
            if self.config is not None and hasattr(self.config, "migrations_dir"):
                # Create a migration manager if we have config
                from synq.core.config import SynqConfig
                from synq.core.migration import MigrationManager

                # Type guard to ensure config is SynqConfig
                if isinstance(self.config, SynqConfig):
                    migration_manager = MigrationManager(self.config)
                else:
                    return
            else:
                # This method is expected to work without explicit migration_manager
                # but we can't create one without knowing where migrations are
                # This is a limitation of the API design - for now, do nothing
                return

        # Get pending migrations
        pending_migrations = migration_manager.get_pending_migrations(self)

        # Apply each migration
        for migration in pending_migrations:
            self.apply_migration(migration)

    def close(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
