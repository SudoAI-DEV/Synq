"""Schema difference detection."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

from synq.core.snapshot import (
    ColumnSnapshot,
    ForeignKeySnapshot,
    IndexSnapshot,
    SchemaSnapshot,
    TableSnapshot,
)


class OperationType(Enum):
    """Types of migration operations."""

    CREATE_TABLE = "create_table"
    DROP_TABLE = "drop_table"
    ADD_COLUMN = "add_column"
    DROP_COLUMN = "drop_column"
    ALTER_COLUMN = "alter_column"
    CREATE_INDEX = "create_index"
    DROP_INDEX = "drop_index"
    ADD_FOREIGN_KEY = "add_foreign_key"
    DROP_FOREIGN_KEY = "drop_foreign_key"


@dataclass
class MigrationOperation:
    """Represents a single migration operation."""

    operation_type: OperationType
    table_name: str
    object_name: Optional[str] = None  # column, index, or constraint name
    old_definition: Optional[
        Union[ColumnSnapshot, IndexSnapshot, ForeignKeySnapshot, TableSnapshot]
    ] = None
    new_definition: Optional[
        Union[ColumnSnapshot, IndexSnapshot, ForeignKeySnapshot, TableSnapshot]
    ] = None

    def __str__(self) -> str:
        """String representation of the operation."""
        if self.operation_type == OperationType.CREATE_TABLE:
            return f"CREATE TABLE {self.table_name}"
        if self.operation_type == OperationType.DROP_TABLE:
            return f"DROP TABLE {self.table_name}"
        if self.operation_type == OperationType.ADD_COLUMN:
            return f"ADD COLUMN {self.table_name}.{self.object_name}"
        if self.operation_type == OperationType.DROP_COLUMN:
            return f"DROP COLUMN {self.table_name}.{self.object_name}"
        if self.operation_type == OperationType.ALTER_COLUMN:
            return f"ALTER COLUMN {self.table_name}.{self.object_name}"
        if self.operation_type == OperationType.CREATE_INDEX:
            return f"CREATE INDEX {self.object_name} ON {self.table_name}"
        if self.operation_type == OperationType.DROP_INDEX:
            return f"DROP INDEX {self.object_name}"
        if self.operation_type == OperationType.ADD_FOREIGN_KEY:
            return f"ADD FOREIGN KEY {self.table_name}.{self.object_name}"
        if self.operation_type == OperationType.DROP_FOREIGN_KEY:
            return f"DROP FOREIGN KEY {self.table_name}.{self.object_name}"
        return f"{self.operation_type.value} {self.table_name}"


class SchemaDiffer:
    """Detects differences between schema snapshots."""

    def detect_changes(
        self, old_snapshot: Optional[SchemaSnapshot], new_snapshot: SchemaSnapshot
    ) -> list[MigrationOperation]:
        """Detect changes between two snapshots."""
        if old_snapshot is None:
            # First migration - create all tables
            return self._create_initial_operations(new_snapshot)

        operations = []

        # Create table name sets for comparison
        old_tables = {table.name: table for table in old_snapshot.tables}
        new_tables = {table.name: table for table in new_snapshot.tables}

        old_table_names = set(old_tables.keys())
        new_table_names = set(new_tables.keys())

        # Find dropped tables
        for table_name in old_table_names - new_table_names:
            operations.append(
                MigrationOperation(
                    operation_type=OperationType.DROP_TABLE,
                    table_name=table_name,
                    old_definition=old_tables[table_name],
                )
            )

        # Find new tables
        for table_name in new_table_names - old_table_names:
            operations.append(
                MigrationOperation(
                    operation_type=OperationType.CREATE_TABLE,
                    table_name=table_name,
                    new_definition=new_tables[table_name],
                )
            )

        # Find modified tables
        for table_name in old_table_names & new_table_names:
            table_operations = self._detect_table_changes(
                old_tables[table_name], new_tables[table_name]
            )
            operations.extend(table_operations)

        return operations

    def _create_initial_operations(
        self, snapshot: SchemaSnapshot
    ) -> list[MigrationOperation]:
        """Create operations for initial migration."""
        operations = []

        for table in snapshot.tables:
            operations.append(
                MigrationOperation(
                    operation_type=OperationType.CREATE_TABLE,
                    table_name=table.name,
                    new_definition=table,
                )
            )

        return operations

    def _detect_table_changes(
        self, old_table: TableSnapshot, new_table: TableSnapshot
    ) -> list[MigrationOperation]:
        """Detect changes within a single table."""
        operations = []

        # Detect column changes
        operations.extend(self._detect_column_changes(old_table, new_table))

        # Detect index changes
        operations.extend(self._detect_index_changes(old_table, new_table))

        # Detect foreign key changes
        operations.extend(self._detect_foreign_key_changes(old_table, new_table))

        return operations

    def _detect_column_changes(
        self, old_table: TableSnapshot, new_table: TableSnapshot
    ) -> list[MigrationOperation]:
        """Detect column changes."""
        operations = []

        old_columns = {col.name: col for col in old_table.columns}
        new_columns = {col.name: col for col in new_table.columns}

        old_column_names = set(old_columns.keys())
        new_column_names = set(new_columns.keys())

        # Dropped columns
        for col_name in old_column_names - new_column_names:
            operations.append(
                MigrationOperation(
                    operation_type=OperationType.DROP_COLUMN,
                    table_name=old_table.name,
                    object_name=col_name,
                    old_definition=old_columns[col_name],
                )
            )

        # New columns
        for col_name in new_column_names - old_column_names:
            operations.append(
                MigrationOperation(
                    operation_type=OperationType.ADD_COLUMN,
                    table_name=new_table.name,
                    object_name=col_name,
                    new_definition=new_columns[col_name],
                )
            )

        # Modified columns
        for col_name in old_column_names & new_column_names:
            old_col = old_columns[col_name]
            new_col = new_columns[col_name]

            if self._columns_differ(old_col, new_col):
                operations.append(
                    MigrationOperation(
                        operation_type=OperationType.ALTER_COLUMN,
                        table_name=new_table.name,
                        object_name=col_name,
                        old_definition=old_col,
                        new_definition=new_col,
                    )
                )

        return operations

    def _detect_index_changes(
        self, old_table: TableSnapshot, new_table: TableSnapshot
    ) -> list[MigrationOperation]:
        """Detect index changes."""
        operations = []

        old_indexes = {idx.name: idx for idx in old_table.indexes if idx.name}
        new_indexes = {idx.name: idx for idx in new_table.indexes if idx.name}

        old_index_names = set(old_indexes.keys())
        new_index_names = set(new_indexes.keys())

        # Dropped indexes
        for idx_name in old_index_names - new_index_names:
            operations.append(
                MigrationOperation(
                    operation_type=OperationType.DROP_INDEX,
                    table_name=old_table.name,
                    object_name=idx_name,
                    old_definition=old_indexes[idx_name],
                )
            )

        # New indexes
        for idx_name in new_index_names - old_index_names:
            operations.append(
                MigrationOperation(
                    operation_type=OperationType.CREATE_INDEX,
                    table_name=new_table.name,
                    object_name=idx_name,
                    new_definition=new_indexes[idx_name],
                )
            )

        return operations

    def _detect_foreign_key_changes(
        self, old_table: TableSnapshot, new_table: TableSnapshot
    ) -> list[MigrationOperation]:
        """Detect foreign key changes."""
        operations = []

        # Create comparable keys for foreign keys
        def fk_key(fk: ForeignKeySnapshot) -> str:
            return f"{fk.columns}→{fk.referred_table}.{fk.referred_columns}"

        old_fks = {fk_key(fk): fk for fk in old_table.foreign_keys}
        new_fks = {fk_key(fk): fk for fk in new_table.foreign_keys}

        old_fk_keys = set(old_fks.keys())
        new_fk_keys = set(new_fks.keys())

        # Dropped foreign keys
        for fk_key_str in old_fk_keys - new_fk_keys:
            fk = old_fks[fk_key_str]
            operations.append(
                MigrationOperation(
                    operation_type=OperationType.DROP_FOREIGN_KEY,
                    table_name=old_table.name,
                    object_name=fk.name,
                    old_definition=fk,
                )
            )

        # New foreign keys
        for fk_key_str in new_fk_keys - old_fk_keys:
            fk = new_fks[fk_key_str]
            operations.append(
                MigrationOperation(
                    operation_type=OperationType.ADD_FOREIGN_KEY,
                    table_name=new_table.name,
                    object_name=fk.name,
                    new_definition=fk,
                )
            )

        return operations

    def _columns_differ(self, old_col: ColumnSnapshot, new_col: ColumnSnapshot) -> bool:
        """Check if two columns are different."""
        return (
            old_col.type != new_col.type
            or old_col.nullable != new_col.nullable
            or old_col.default != new_col.default
            or old_col.primary_key != new_col.primary_key
            or old_col.autoincrement != new_col.autoincrement
            or old_col.unique != new_col.unique
        )

    def generate_diff(
        self, old_snapshot: Optional[SchemaSnapshot], new_snapshot: SchemaSnapshot
    ) -> list[MigrationOperation]:
        """Generate diff between snapshots (alias for detect_changes)."""
        return self.detect_changes(old_snapshot, new_snapshot)
