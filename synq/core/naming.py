"""Automatic migration naming system."""

import re
from dataclasses import dataclass
from typing import Optional

from synq.core.diff import MigrationOperation, OperationType


@dataclass
class NamingContext:
    """Context information for migration naming."""

    operations: list[MigrationOperation]
    table_names: set[str]
    operation_counts: dict[OperationType, int]


class MigrationNamer:
    """Generates intelligent migration names based on operations."""

    # Django-style operation prefixes
    OPERATION_PREFIXES = {
        OperationType.CREATE_TABLE: ["create", "add"],
        OperationType.DROP_TABLE: ["delete", "remove"],
        OperationType.ADD_COLUMN: ["add"],
        OperationType.DROP_COLUMN: ["remove", "delete"],
        OperationType.ALTER_COLUMN: ["alter", "change"],
        OperationType.CREATE_INDEX: ["add"],
        OperationType.DROP_INDEX: ["remove", "delete"],
        OperationType.ADD_FOREIGN_KEY: ["add"],
        OperationType.DROP_FOREIGN_KEY: ["remove", "delete"],
    }

    def __init__(self) -> None:
        pass

    def generate_name(self, operations: list[MigrationOperation]) -> str:
        """
        Generate an intelligent migration name based on operations.

        Examples:
        - Single table creation: "create_user_table"
        - Multiple table creation: "initial_migration"
        - Column addition: "add_email_to_user"
        - Index creation: "add_user_email_index"
        - Mixed operations: "update_user_schema"
        """
        if not operations:
            return "empty_migration"

        context = self._analyze_operations(operations)

        # Special case: Initial migration (multiple table creations)
        if self._is_initial_migration(context):
            return "initial_migration"

        # Single operation patterns
        if len(operations) == 1:
            return self._generate_single_operation_name(operations[0])

        # Multiple operations on same table
        if len(context.table_names) == 1:
            table_name = list(context.table_names)[0]
            return self._generate_single_table_name(context, table_name)

        # Multiple operations on multiple tables
        return self._generate_multi_table_name(context)

    def _analyze_operations(
        self, operations: list[MigrationOperation]
    ) -> NamingContext:
        """Analyze operations to extract naming context."""
        table_names = set()
        operation_counts: dict[OperationType, int] = {}

        for op in operations:
            table_names.add(op.table_name)
            op_type = op.operation_type
            operation_counts[op_type] = operation_counts.get(op_type, 0) + 1

        return NamingContext(
            operations=operations,
            table_names=table_names,
            operation_counts=operation_counts,
        )

    def _is_initial_migration(self, context: NamingContext) -> bool:
        """Check if this looks like an initial migration."""
        # Multiple table creations with no other operations
        table_creates = context.operation_counts.get(OperationType.CREATE_TABLE, 0)
        total_ops = sum(context.operation_counts.values())

        return table_creates >= 2 and table_creates == total_ops

    def _generate_single_operation_name(self, operation: MigrationOperation) -> str:
        """Generate name for a single operation."""
        op_type = operation.operation_type
        table_name = self._sanitize_name(operation.table_name)

        if op_type == OperationType.CREATE_TABLE:
            return f"create_{table_name}_table"

        if op_type == OperationType.DROP_TABLE:
            return f"delete_{table_name}_table"

        if op_type == OperationType.ADD_COLUMN:
            column_name = self._sanitize_name(operation.object_name or "column")
            return f"add_{column_name}_to_{table_name}"

        if op_type == OperationType.DROP_COLUMN:
            column_name = self._sanitize_name(operation.object_name or "column")
            return f"remove_{column_name}_from_{table_name}"

        if op_type == OperationType.ALTER_COLUMN:
            column_name = self._sanitize_name(operation.object_name or "column")
            return f"alter_{column_name}_in_{table_name}"

        if op_type == OperationType.CREATE_INDEX:
            index_name = self._sanitize_name(operation.object_name or "index")
            return f"add_{index_name}_to_{table_name}"

        if op_type == OperationType.DROP_INDEX:
            index_name = self._sanitize_name(operation.object_name or "index")
            return f"remove_{index_name}_from_{table_name}"

        if op_type == OperationType.ADD_FOREIGN_KEY:
            return f"add_foreign_key_to_{table_name}"

        if op_type == OperationType.DROP_FOREIGN_KEY:
            return f"remove_foreign_key_from_{table_name}"

        return f"update_{table_name}"

    def _generate_single_table_name(
        self, context: NamingContext, table_name: str
    ) -> str:
        """Generate name for multiple operations on a single table."""
        table_name = self._sanitize_name(table_name)
        counts = context.operation_counts

        # Check for common patterns
        if counts.get(OperationType.ADD_COLUMN, 0) > 0 and len(
            context.operations
        ) == counts.get(OperationType.ADD_COLUMN, 0):
            # Only column additions
            if counts[OperationType.ADD_COLUMN] == 1:
                op = next(
                    op
                    for op in context.operations
                    if op.operation_type == OperationType.ADD_COLUMN
                )
                column_name = self._sanitize_name(op.object_name or "column")
                return f"add_{column_name}_to_{table_name}"
            return f"add_columns_to_{table_name}"

        if counts.get(OperationType.DROP_COLUMN, 0) > 0 and len(
            context.operations
        ) == counts.get(OperationType.DROP_COLUMN, 0):
            # Only column removals
            if counts[OperationType.DROP_COLUMN] == 1:
                op = next(
                    op
                    for op in context.operations
                    if op.operation_type == OperationType.DROP_COLUMN
                )
                column_name = self._sanitize_name(op.object_name or "column")
                return f"remove_{column_name}_from_{table_name}"
            return f"remove_columns_from_{table_name}"

        # Mixed operations
        return f"update_{table_name}_schema"

    def _generate_multi_table_name(self, context: NamingContext) -> str:
        """Generate name for operations across multiple tables."""
        counts = context.operation_counts

        # Check for dominant operation types
        total_ops = sum(counts.values())

        if counts.get(OperationType.CREATE_TABLE, 0) > total_ops * 0.6:
            return "create_tables"

        if counts.get(OperationType.DROP_TABLE, 0) > total_ops * 0.6:
            return "delete_tables"

        if counts.get(OperationType.ADD_COLUMN, 0) > total_ops * 0.6:
            return "add_columns"

        if counts.get(OperationType.DROP_COLUMN, 0) > total_ops * 0.6:
            return "remove_columns"

        # Mixed operations across tables
        return "update_schema"

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use in migration filename."""
        if not name:
            return "unnamed"

        # Convert to lowercase
        name = name.lower()

        # Replace spaces and non-alphanumeric characters with underscores
        name = re.sub(r"[^a-z0-9_]", "_", name)

        # Remove multiple consecutive underscores
        name = re.sub(r"_+", "_", name)

        # Remove leading/trailing underscores
        name = name.strip("_")

        # Ensure it's not empty
        if not name:
            return "unnamed"

        return name


def generate_migration_name(
    operations: list[MigrationOperation], user_description: Optional[str] = None
) -> str:
    """
    Generate a migration name based on operations and optional user description.

    Args:
        operations: List of migration operations
        user_description: Optional user-provided description

    Returns:
        Generated migration name
    """
    namer = MigrationNamer()

    if user_description:
        # User provided description - clean it up
        return namer._sanitize_name(user_description)
    # Auto-generate based on operations
    return namer.generate_name(operations)
