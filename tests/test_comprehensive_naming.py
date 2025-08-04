"""Comprehensive tests for migration naming functionality."""

from synq.core.diff import MigrationOperation, OperationType
from synq.core.naming import MigrationNamer, NamingContext, generate_migration_name


def test_naming_context_creation():
    """Test creating a NamingContext."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="users"
        )
    ]

    context = NamingContext(
        operations=operations,
        table_names={"users"},
        operation_counts={OperationType.CREATE_TABLE: 1},
    )

    assert len(context.operations) == 1
    assert "users" in context.table_names
    assert context.operation_counts[OperationType.CREATE_TABLE] == 1


def test_migration_namer_init():
    """Test MigrationNamer initialization."""
    namer = MigrationNamer()
    assert namer.OPERATION_PREFIXES is not None
    assert len(namer.OPERATION_PREFIXES) > 0


def test_migration_namer_empty_operations():
    """Test generating name for empty operations list."""
    namer = MigrationNamer()
    name = namer.generate_name([])
    assert name == "empty_migration"


def test_migration_namer_single_table_creation():
    """Test generating name for single table creation."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="users"
        )
    ]

    name = namer.generate_name(operations)
    assert "create" in name.lower()
    assert "users" in name.lower()
    assert "table" in name.lower()


def test_migration_namer_multiple_table_creation():
    """Test generating name for multiple table creation."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="users"
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="posts"
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="comments"
        ),
    ]

    name = namer.generate_name(operations)
    assert "initial" in name.lower() or "migration" in name.lower()


def test_migration_namer_single_column_addition():
    """Test generating name for single column addition."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        )
    ]

    name = namer.generate_name(operations)
    assert "add" in name.lower()
    assert "email" in name.lower()
    assert "users" in name.lower()


def test_migration_namer_single_column_removal():
    """Test generating name for single column removal."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.DROP_COLUMN,
            table_name="users",
            object_name="email",
        )
    ]

    name = namer.generate_name(operations)
    assert any(prefix in name.lower() for prefix in ["remove", "delete"])
    assert "email" in name.lower()
    assert "users" in name.lower()


def test_migration_namer_table_deletion():
    """Test generating name for table deletion."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.DROP_TABLE, table_name="old_table"
        )
    ]

    name = namer.generate_name(operations)
    assert any(prefix in name.lower() for prefix in ["delete", "remove"])
    assert "old_table" in name.lower()
    assert "table" in name.lower()


def test_migration_namer_index_creation():
    """Test generating name for index creation."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_INDEX,
            table_name="users",
            object_name="idx_email",
        )
    ]

    name = namer.generate_name(operations)
    assert "add" in name.lower()
    assert "idx_email" in name.lower() or "index" in name.lower()
    assert "users" in name.lower()


def test_migration_namer_index_removal():
    """Test generating name for index removal."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.DROP_INDEX,
            table_name="users",
            object_name="idx_email",
        )
    ]

    name = namer.generate_name(operations)
    assert any(prefix in name.lower() for prefix in ["remove", "delete"])
    assert "idx_email" in name.lower() or "index" in name.lower()


def test_migration_namer_foreign_key_addition():
    """Test generating name for foreign key addition."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_FOREIGN_KEY,
            table_name="posts",
            object_name="fk_user_id",
        )
    ]

    name = namer.generate_name(operations)
    assert "add" in name.lower()
    assert "fk_user_id" in name.lower() or "foreign" in name.lower()
    assert "posts" in name.lower()


def test_migration_namer_foreign_key_removal():
    """Test generating name for foreign key removal."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.DROP_FOREIGN_KEY,
            table_name="posts",
            object_name="fk_user_id",
        )
    ]

    name = namer.generate_name(operations)
    assert any(prefix in name.lower() for prefix in ["remove", "delete"])
    assert "fk_user_id" in name.lower() or "foreign" in name.lower()


def test_migration_namer_column_alteration():
    """Test generating name for column alteration."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.ALTER_COLUMN,
            table_name="users",
            object_name="email",
        )
    ]

    name = namer.generate_name(operations)
    assert any(prefix in name.lower() for prefix in ["alter", "change"])
    assert "email" in name.lower()
    assert "users" in name.lower()


def test_migration_namer_mixed_operations_single_table():
    """Test generating name for mixed operations on single table."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_INDEX,
            table_name="users",
            object_name="idx_email",
        ),
        MigrationOperation(
            operation_type=OperationType.ALTER_COLUMN,
            table_name="users",
            object_name="name",
        ),
    ]

    name = namer.generate_name(operations)
    assert "update" in name.lower()
    assert "users" in name.lower()
    assert "schema" in name.lower()


def test_migration_namer_mixed_operations_multiple_tables():
    """Test generating name for mixed operations on multiple tables."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_INDEX,
            table_name="posts",
            object_name="idx_title",
        ),
        MigrationOperation(
            operation_type=OperationType.ALTER_COLUMN,
            table_name="comments",
            object_name="content",
        ),
    ]

    name = namer.generate_name(operations)
    assert "update" in name.lower()
    assert "schema" in name.lower()


def test_migration_namer_multiple_columns_single_table():
    """Test generating name for multiple column operations on single table."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="phone",
        ),
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="address",
        ),
    ]

    name = namer.generate_name(operations)
    assert "add" in name.lower()
    assert "columns" in name.lower()
    assert "users" in name.lower()


def test_migration_namer_sanitize_name():
    """Test name sanitization for tables/columns with special characters."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="user-profile_data"
        )
    ]

    name = namer.generate_name(operations)
    # Should sanitize special characters
    assert "-" not in name
    assert name.replace("_", "").isalnum()


def test_migration_namer_long_table_names():
    """Test handling of very long table names."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE,
            table_name="extremely_long_table_name_that_exceeds_normal_limits",
        )
    ]

    name = namer.generate_name(operations)
    # Should generate a reasonable name
    assert len(name) < 100  # Reasonable limit
    assert "create" in name.lower()
    assert "table" in name.lower()


def test_generate_migration_name_function():
    """Test the standalone generate_migration_name function."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="users"
        )
    ]

    name = generate_migration_name(operations)
    assert isinstance(name, str)
    assert len(name) > 0
    assert "create" in name.lower()
    assert "users" in name.lower()


def test_migration_namer_edge_cases():
    """Test edge cases for migration naming."""
    namer = MigrationNamer()

    # Test with None object_name
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE,
            table_name="users",
            object_name=None,
        )
    ]

    name = namer.generate_name(operations)
    assert isinstance(name, str)
    assert len(name) > 0


def test_migration_namer_case_insensitive():
    """Test that naming works with different case table names."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="UserProfiles"
        )
    ]

    name = namer.generate_name(operations)
    assert "create" in name.lower()
    # Should handle mixed case table names
    assert "userprofiles" in name.lower() or "user_profiles" in name.lower()


def test_migration_namer_numeric_names():
    """Test handling of table/column names with numbers."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="table2",
            object_name="field123",
        )
    ]

    name = namer.generate_name(operations)
    assert "add" in name.lower()
    assert "field123" in name.lower()
    assert "table2" in name.lower()


def test_migration_namer_single_character_names():
    """Test handling of single character table/column names."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(operation_type=OperationType.CREATE_TABLE, table_name="x")
    ]

    name = namer.generate_name(operations)
    assert "create" in name.lower()
    assert "x" in name.lower()
    assert "table" in name.lower()


def test_migration_namer_operation_priority():
    """Test that mixed operations generate schema update names."""
    namer = MigrationNamer()

    # Mixed operations should generate "update_schema" type names
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="existing_table",
            object_name="new_column",
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE, table_name="new_table"
        ),
    ]

    name = namer.generate_name(operations)
    # Mixed operations typically generate update_schema names
    assert "update" in name.lower() and "schema" in name.lower()


def test_migration_namer_multiple_same_operations():
    """Test naming when multiple operations of same type occur."""
    namer = MigrationNamer()
    operations = [
        MigrationOperation(
            operation_type=OperationType.DROP_TABLE, table_name="old_table1"
        ),
        MigrationOperation(
            operation_type=OperationType.DROP_TABLE, table_name="old_table2"
        ),
    ]

    name = namer.generate_name(operations)
    assert any(prefix in name.lower() for prefix in ["delete", "remove"])
    assert "table" in name.lower()


def test_migration_namer_name_uniqueness():
    """Test that similar operations generate distinguishable names."""
    namer = MigrationNamer()

    operations1 = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        )
    ]

    operations2 = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="phone",
        )
    ]

    name1 = namer.generate_name(operations1)
    name2 = namer.generate_name(operations2)

    # Names should be different because object names are different
    assert name1 != name2
    assert "email" in name1.lower()
    assert "phone" in name2.lower()
