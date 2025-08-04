"""Snapshot system for schema state management."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import MetaData, Table


@dataclass
class ColumnSnapshot:
    """Snapshot of a column definition."""

    name: str
    type: str
    nullable: bool
    default: Optional[str] = None
    primary_key: bool = False
    autoincrement: bool = False
    unique: bool = False


@dataclass
class IndexSnapshot:
    """Snapshot of an index definition."""

    name: str
    columns: list[str]
    unique: bool = False


@dataclass
class ForeignKeySnapshot:
    """Snapshot of a foreign key constraint."""

    name: Optional[str]
    columns: list[str]
    referred_table: str
    referred_columns: list[str]
    ondelete: Optional[str] = None
    onupdate: Optional[str] = None


@dataclass
class TableSnapshot:
    """Snapshot of a table definition."""

    name: str
    columns: list[ColumnSnapshot]
    indexes: list[IndexSnapshot]
    foreign_keys: list[ForeignKeySnapshot]
    schema: Optional[str] = None


@dataclass
class SchemaSnapshot:
    """Complete schema snapshot."""

    tables: list[TableSnapshot]
    version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert snapshot to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SchemaSnapshot":
        """Create snapshot from dictionary."""
        tables = []
        for table_data in data["tables"]:
            columns = [ColumnSnapshot(**col) for col in table_data["columns"]]
            indexes = [IndexSnapshot(**idx) for idx in table_data["indexes"]]
            foreign_keys = [
                ForeignKeySnapshot(**fk) for fk in table_data["foreign_keys"]
            ]

            tables.append(
                TableSnapshot(
                    name=table_data["name"],
                    columns=columns,
                    indexes=indexes,
                    foreign_keys=foreign_keys,
                    schema=table_data.get("schema"),
                )
            )

        return cls(tables=tables, version=data.get("version", "1.0"))

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access for backward compatibility."""
        if key == "tables":
            # Return a dictionary with table names as keys
            return {table.name: self._table_to_dict(table) for table in self.tables}
        if key == "version":
            return self.version
        raise KeyError(f"Key '{key}' not found in SchemaSnapshot")

    def _table_to_dict(self, table: TableSnapshot) -> dict[str, Any]:
        """Convert a table to dictionary format for backward compatibility."""
        return {
            "name": table.name,
            "columns": {col.name: asdict(col) for col in table.columns},
            "indexes": [asdict(idx) for idx in table.indexes],
            "foreign_keys": [asdict(fk) for fk in table.foreign_keys],
            "schema": table.schema,
        }


class SnapshotManager:
    """Manages schema snapshots."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self.snapshot_path = config.snapshot_path
        self.snapshot_path.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, metadata: MetaData) -> SchemaSnapshot:
        """Create a snapshot from SQLAlchemy MetaData."""
        tables = []

        for table in metadata.tables.values():
            table_snapshot = self._create_table_snapshot(table)
            tables.append(table_snapshot)

        return SchemaSnapshot(tables=tables)

    def _create_table_snapshot(self, table: Table) -> TableSnapshot:
        """Create a snapshot of a single table."""
        # Extract columns
        columns = []
        for column in table.columns:
            col_snapshot = ColumnSnapshot(
                name=column.name,
                type=str(column.type),
                nullable=bool(column.nullable),
                default=str(column.default) if column.default else None,
                primary_key=column.primary_key,
                autoincrement=bool(column.autoincrement)
                if isinstance(column.autoincrement, bool)
                else False,
                unique=bool(column.unique) if column.unique is not None else False,
            )
            columns.append(col_snapshot)

        # Extract indexes
        indexes = []
        for index in table.indexes:
            idx_snapshot = IndexSnapshot(
                name=str(index.name) if index.name is not None else "",
                columns=[col.name for col in index.columns],
                unique=index.unique,
            )
            indexes.append(idx_snapshot)

        # Extract foreign keys
        foreign_keys = []
        for fk in table.foreign_keys:
            fk_snapshot = ForeignKeySnapshot(
                name=str(fk.constraint.name)
                if fk.constraint and fk.constraint.name
                else None,
                columns=[fk.parent.name],
                referred_table=fk.column.table.name,
                referred_columns=[fk.column.name],
                ondelete=fk.ondelete,
                onupdate=fk.onupdate,
            )
            foreign_keys.append(fk_snapshot)

        return TableSnapshot(
            name=table.name,
            columns=columns,
            indexes=indexes,
            foreign_keys=foreign_keys,
            schema=table.schema,
        )

    def save_snapshot(self, migration_number: int, snapshot: SchemaSnapshot) -> Path:
        """Save a snapshot to file."""
        filename = f"{migration_number:04d}_snapshot.json"
        filepath = self.snapshot_path / filename

        with open(filepath, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

        return Path(filepath)

    def load_snapshot(self, migration_number: int) -> Optional[SchemaSnapshot]:
        """Load a snapshot from file."""
        filename = f"{migration_number:04d}_snapshot.json"
        filepath = self.snapshot_path / filename

        if not filepath.exists():
            return None

        try:
            with open(filepath) as f:
                data = json.load(f)
            return SchemaSnapshot.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            # Return None for malformed or invalid snapshot files
            return None

    def get_latest_snapshot(self) -> Optional[SchemaSnapshot]:
        """Get the most recent snapshot."""
        snapshot_files = list(self.snapshot_path.glob("*_snapshot.json"))

        if not snapshot_files:
            return None

        # Sort by migration number (filename prefix)
        latest_file = sorted(snapshot_files)[-1]
        migration_number = int(latest_file.stem.split("_")[0])

        return self.load_snapshot(migration_number)

    def get_next_migration_number(self) -> int:
        """Get the next migration number."""
        snapshot_files = list(self.snapshot_path.glob("*_snapshot.json"))

        if not snapshot_files:
            return 0

        # Get highest migration number
        max_number = 0
        for file in snapshot_files:
            try:
                number = int(file.stem.split("_")[0])
                max_number = max(max_number, number)
            except ValueError:
                continue

        return max_number + 1

    def get_all_snapshots(self) -> list[int]:
        """Get all available snapshot numbers."""
        snapshot_files = list(self.snapshot_path.glob("*_snapshot.json"))
        numbers = []

        for file in snapshot_files:
            try:
                number = int(file.stem.split("_")[0])
                numbers.append(number)
            except ValueError:
                continue

        return sorted(numbers)
