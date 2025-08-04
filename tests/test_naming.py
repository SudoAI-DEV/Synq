"""Tests for migration naming system."""

from synq.core.diff import MigrationOperation, OperationType
from synq.core.naming import MigrationNamer, generate_migration_name


def test_single_table_creation():
    """Test naming for single table creation."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE,
            table_name="users",
        )
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "create_users_table"


def test_initial_migration():
    """Test naming for initial migration with multiple tables."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE,
            table_name="users",
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE,
            table_name="posts",
        ),
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE,
            table_name="comments",
        ),
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "initial_migration"


def test_single_column_addition():
    """Test naming for single column addition."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        )
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "add_email_to_users"


def test_single_column_removal():
    """Test naming for single column removal."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.DROP_COLUMN,
            table_name="users",
            object_name="phone",
        )
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "remove_phone_from_users"


def test_multiple_columns_same_table():
    """Test naming for multiple column operations on same table."""
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
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "add_columns_to_users"


def test_mixed_operations_same_table():
    """Test naming for mixed operations on same table."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
        MigrationOperation(
            operation_type=OperationType.DROP_COLUMN,
            table_name="users",
            object_name="phone",
        ),
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "update_users_schema"


def test_table_deletion():
    """Test naming for table deletion."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.DROP_TABLE,
            table_name="old_table",
        )
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "delete_old_table_table"


def test_index_creation():
    """Test naming for index creation."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_INDEX,
            table_name="users",
            object_name="user_email_idx",
        )
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "add_user_email_idx_to_users"


def test_multi_table_operations():
    """Test naming for operations across multiple tables."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="users",
            object_name="email",
        ),
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="posts",
            object_name="tags",
        ),
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "add_columns"


def test_name_sanitization():
    """Test name sanitization."""
    namer = MigrationNamer()

    # Test various problematic names
    assert namer._sanitize_name("User-Model") == "user_model"
    assert namer._sanitize_name("Email@Address") == "email_address"
    assert namer._sanitize_name("My Special Table!") == "my_special_table"
    assert namer._sanitize_name("__test__table__") == "test_table"
    assert namer._sanitize_name("123number") == "123number"
    assert namer._sanitize_name("") == "unnamed"
    assert namer._sanitize_name("   ") == "unnamed"


def test_generate_migration_name_with_description():
    """Test generate_migration_name with user description."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE,
            table_name="users",
        )
    ]

    # With user description
    name = generate_migration_name(operations, "Add user authentication")
    assert name == "add_user_authentication"

    # Without user description (auto-generate)
    name = generate_migration_name(operations)
    assert name == "create_users_table"


def test_empty_operations():
    """Test naming for empty operations list."""
    operations = []

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "empty_migration"


def test_alter_column():
    """Test naming for column alteration."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.ALTER_COLUMN,
            table_name="users",
            object_name="email",
        )
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "alter_email_in_users"


def test_foreign_key_operations():
    """Test naming for foreign key operations."""
    # Add foreign key
    operations = [
        MigrationOperation(
            operation_type=OperationType.ADD_FOREIGN_KEY,
            table_name="posts",
            object_name="fk_user_id",
        )
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "add_foreign_key_to_posts"

    # Remove foreign key
    operations = [
        MigrationOperation(
            operation_type=OperationType.DROP_FOREIGN_KEY,
            table_name="posts",
            object_name="fk_user_id",
        )
    ]

    name = namer.generate_name(operations)
    assert name == "remove_foreign_key_from_posts"


def test_complex_scenario():
    """Test naming for complex migration scenario."""
    operations = [
        MigrationOperation(
            operation_type=OperationType.CREATE_TABLE,
            table_name="categories",
        ),
        MigrationOperation(
            operation_type=OperationType.ADD_COLUMN,
            table_name="posts",
            object_name="category_id",
        ),
        MigrationOperation(
            operation_type=OperationType.ADD_FOREIGN_KEY,
            table_name="posts",
            object_name="fk_category",
        ),
    ]

    namer = MigrationNamer()
    name = namer.generate_name(operations)
    assert name == "update_schema"  # Mixed operations across tables
