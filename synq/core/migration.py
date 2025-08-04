"""Migration management and SQL generation."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, NamedTuple, Optional

from sqlalchemy import MetaData, create_engine
from sqlalchemy.schema import CreateTable

from synq.core.diff import MigrationOperation, OperationType, SchemaDiffer

# from sqlalchemy.sql.ddl import DDLElement
from synq.core.snapshot import SchemaSnapshot


class MigrationFile(NamedTuple):
    """Represents a migration file."""

    number: int
    name: str
    filename: str
    filepath: Path
    sql_content: str


@dataclass
class PendingMigration:
    """Represents a pending migration to be applied."""

    filename: str
    sql_content: str


class MigrationManager:
    """Manages migration generation and application."""

    def __init__(self, config):
        self.config = config
        self.migrations_path = config.migrations_path
        self.migrations_path.mkdir(exist_ok=True)
        self.differ = SchemaDiffer()

    def detect_changes(
        self, old_snapshot: Optional[SchemaSnapshot], new_snapshot: SchemaSnapshot
    ) -> List[MigrationOperation]:
        """Detect changes between snapshots."""
        return self.differ.detect_changes(old_snapshot, new_snapshot)

    def generate_sql(
        self, operations: List[MigrationOperation], metadata: MetaData
    ) -> str:
        """Generate SQL from migration operations."""
        if not operations:
            return ""

        # Create a temporary engine for SQL compilation
        # Using SQLite for cross-platform DDL generation
        engine = create_engine("sqlite:///:memory:")

        sql_statements = []

        for operation in operations:
            try:
                sql = self._operation_to_sql(operation, metadata, engine)
                if sql:
                    sql_statements.append(f"-- {operation}")
                    sql_statements.append(sql)
                    sql_statements.append("")
            except Exception as e:
                # Add comment about failed operation
                sql_statements.append(
                    f"-- WARNING: Could not generate SQL for {operation}: {e}"
                )
                sql_statements.append("")

        return "\n".join(sql_statements)

    def _operation_to_sql(
        self, operation: MigrationOperation, metadata: MetaData, engine
    ) -> str:
        """Convert a single operation to SQL."""

        if operation.operation_type == OperationType.CREATE_TABLE:
            table_def = operation.new_definition
            # Reconstruct SQLAlchemy table for DDL generation
            table = self._build_sqlalchemy_table(table_def, metadata)
            create_table = CreateTable(table)
            return str(create_table.compile(engine)).strip() + ";"

        if operation.operation_type == OperationType.DROP_TABLE:
            return f"DROP TABLE {operation.table_name};"

        if operation.operation_type == OperationType.ADD_COLUMN:
            col_def = operation.new_definition
            sql_type = col_def.type

            # Build column definition parts
            parts = [f"ADD COLUMN {col_def.name} {sql_type}"]

            if not col_def.nullable:
                parts.append("NOT NULL")

            if col_def.default:
                parts.append(f"DEFAULT {col_def.default}")

            if col_def.unique:
                parts.append("UNIQUE")

            return f"ALTER TABLE {operation.table_name} {' '.join(parts)};"

        if operation.operation_type == OperationType.DROP_COLUMN:
            return f"ALTER TABLE {operation.table_name} DROP COLUMN {operation.object_name};"

        if operation.operation_type == OperationType.ALTER_COLUMN:
            old_col = operation.old_definition
            new_col = operation.new_definition

            # For SQLite compatibility, we'll generate a comment
            # Real implementations would need database-specific syntax
            return (
                f"-- ALTER COLUMN {operation.table_name}.{operation.object_name}\n"
                f"-- Note: Column alteration may require database-specific syntax\n"
                f"-- Old: {old_col.name} {old_col.type} {'NULL' if old_col.nullable else 'NOT NULL'}\n"
                f"-- New: {new_col.name} {new_col.type} {'NULL' if new_col.nullable else 'NOT NULL'}"
            )

        if operation.operation_type == OperationType.CREATE_INDEX:
            idx_def = operation.new_definition
            unique_clause = "UNIQUE " if idx_def.unique else ""
            columns = ", ".join(idx_def.columns)
            return f"CREATE {unique_clause}INDEX {idx_def.name} ON {operation.table_name} ({columns});"

        if operation.operation_type == OperationType.DROP_INDEX:
            return f"DROP INDEX {operation.object_name};"

        if operation.operation_type == OperationType.ADD_FOREIGN_KEY:
            fk_def = operation.new_definition
            columns = ", ".join(fk_def.columns)
            ref_columns = ", ".join(fk_def.referred_columns)

            constraint_name = f"CONSTRAINT {fk_def.name} " if fk_def.name else ""

            fk_clause = f"{constraint_name}FOREIGN KEY ({columns}) REFERENCES {fk_def.referred_table} ({ref_columns})"

            if fk_def.ondelete:
                fk_clause += f" ON DELETE {fk_def.ondelete}"
            if fk_def.onupdate:
                fk_clause += f" ON UPDATE {fk_def.onupdate}"

            return f"ALTER TABLE {operation.table_name} ADD {fk_clause};"

        if operation.operation_type == OperationType.DROP_FOREIGN_KEY:
            if operation.object_name:
                return f"ALTER TABLE {operation.table_name} DROP CONSTRAINT {operation.object_name};"
            return f"-- DROP FOREIGN KEY on {operation.table_name} (no constraint name available)"

        return f"-- Unsupported operation: {operation.operation_type}"

    def _build_sqlalchemy_table(self, table_def, metadata):
        """Build SQLAlchemy Table from TableSnapshot for DDL generation."""
        from sqlalchemy import Boolean, Column, DateTime, Integer, String, Table, Text

        # Create a new metadata instance to avoid conflicts
        temp_metadata = MetaData()

        # Simple type mapping - would need to be more comprehensive
        type_mapping = {
            "INTEGER": Integer,
            "VARCHAR": String,
            "TEXT": Text,
            "BOOLEAN": Boolean,
            "DATETIME": DateTime,
        }

        columns = []
        for col_def in table_def.columns:
            # Parse type from string representation
            col_type_str = col_def.type.upper()

            # Handle VARCHAR with length
            if col_type_str.startswith("VARCHAR"):
                if "(" in col_type_str:
                    length = int(col_type_str.split("(")[1].split(")")[0])
                    col_type = String(length)
                else:
                    col_type = String
            else:
                col_type = type_mapping.get(col_type_str, String)

            column = Column(
                col_def.name,
                col_type,
                nullable=col_def.nullable,
                primary_key=col_def.primary_key,
                unique=col_def.unique,
                autoincrement=col_def.autoincrement,
            )
            columns.append(column)

        return Table(table_def.name, temp_metadata, *columns)

    def create_migration_name(self, description: str) -> str:
        """Create a valid migration name from description."""
        # Already cleaned name from naming.py should be used as-is
        # This method just validates and ensures it's safe for filenames
        name = description.lower().strip()

        # Replace any remaining problematic characters
        name = re.sub(r"[^a-z0-9_]", "_", name)

        # Remove multiple consecutive underscores
        name = re.sub(r"_+", "_", name)

        # Remove leading/trailing underscores
        name = name.strip("_")

        # Limit length
        if len(name) > 50:
            name = name[:50].rstrip("_")

        # Ensure it's not empty
        if not name:
            name = "migration"

        return name

    def save_migration(
        self, migration_number: int, migration_name: str, sql_content: str
    ) -> Path:
        """Save migration SQL to file."""
        filename = f"{migration_number:04d}_{migration_name}.sql"
        filepath = self.migrations_path / filename

        with open(filepath, "w") as f:
            f.write(sql_content)

        return filepath

    def get_all_migrations(self) -> List[MigrationFile]:
        """Get all migration files."""
        migration_files = []

        for filepath in sorted(self.migrations_path.glob("*.sql")):
            try:
                # Parse migration number and name from filename
                filename = filepath.stem
                parts = filename.split("_", 1)

                if len(parts) != 2:
                    continue

                number = int(parts[0])
                name = parts[1]

                # Read SQL content
                with open(filepath) as f:
                    sql_content = f.read()

                migration_files.append(
                    MigrationFile(
                        number=number,
                        name=name,
                        filename=filepath.name,
                        filepath=filepath,
                        sql_content=sql_content,
                    )
                )

            except (OSError, ValueError):
                # Skip invalid files
                continue

        return migration_files

    def get_pending_migrations(self, db_manager) -> List[PendingMigration]:
        """Get migrations that haven't been applied to the database."""
        all_migrations = self.get_all_migrations()
        applied_migrations = set(db_manager.get_applied_migrations())

        pending = []
        for migration in all_migrations:
            if migration.filename not in applied_migrations:
                pending.append(
                    PendingMigration(
                        filename=migration.filename, sql_content=migration.sql_content
                    )
                )

        return pending
