"""Comprehensive tests for schema diff functionality."""

from synq.core.diff import MigrationOperation, OperationType, SchemaDiffer
from synq.core.snapshot import (
    ColumnSnapshot,
    ForeignKeySnapshot,
    IndexSnapshot,
    SchemaSnapshot,
    TableSnapshot,
)


def test_operation_type_enum():
    """Test OperationType enum values."""
    assert OperationType.CREATE_TABLE.value == "create_table"
    assert OperationType.DROP_TABLE.value == "drop_table"
    assert OperationType.ADD_COLUMN.value == "add_column"
    assert OperationType.DROP_COLUMN.value == "drop_column"
    assert OperationType.ALTER_COLUMN.value == "alter_column"
    assert OperationType.CREATE_INDEX.value == "create_index"
    assert OperationType.DROP_INDEX.value == "drop_index"
    assert OperationType.ADD_FOREIGN_KEY.value == "add_foreign_key"
    assert OperationType.DROP_FOREIGN_KEY.value == "drop_foreign_key"


def test_migration_operation_string_representation():
    """Test string representation of MigrationOperation."""
    # CREATE TABLE
    op = MigrationOperation(
        operation_type=OperationType.CREATE_TABLE, table_name="users"
    )
    assert str(op) == "CREATE TABLE users"

    # DROP TABLE
    op = MigrationOperation(operation_type=OperationType.DROP_TABLE, table_name="users")
    assert str(op) == "DROP TABLE users"

    # ADD COLUMN
    op = MigrationOperation(
        operation_type=OperationType.ADD_COLUMN, table_name="users", object_name="email"
    )
    assert str(op) == "ADD COLUMN users.email"

    # DROP COLUMN
    op = MigrationOperation(
        operation_type=OperationType.DROP_COLUMN,
        table_name="users",
        object_name="email",
    )
    assert str(op) == "DROP COLUMN users.email"

    # ALTER COLUMN
    op = MigrationOperation(
        operation_type=OperationType.ALTER_COLUMN,
        table_name="users",
        object_name="email",
    )
    assert str(op) == "ALTER COLUMN users.email"

    # CREATE INDEX
    op = MigrationOperation(
        operation_type=OperationType.CREATE_INDEX,
        table_name="users",
        object_name="idx_email",
    )
    assert str(op) == "CREATE INDEX idx_email ON users"

    # DROP INDEX
    op = MigrationOperation(
        operation_type=OperationType.DROP_INDEX,
        table_name="users",
        object_name="idx_email",
    )
    assert str(op) == "DROP INDEX idx_email"

    # ADD FOREIGN KEY
    op = MigrationOperation(
        operation_type=OperationType.ADD_FOREIGN_KEY,
        table_name="posts",
        object_name="fk_user_id",
    )
    assert str(op) == "ADD FOREIGN KEY posts.fk_user_id"

    # DROP FOREIGN KEY
    op = MigrationOperation(
        operation_type=OperationType.DROP_FOREIGN_KEY,
        table_name="posts",
        object_name="fk_user_id",
    )
    assert str(op) == "DROP FOREIGN KEY posts.fk_user_id"


def test_schema_differ_init():
    """Test SchemaDiffer initialization."""
    differ = SchemaDiffer()
    assert differ is not None


def test_schema_differ_detect_changes_no_previous():
    """Test detecting changes when no previous snapshot exists."""
    differ = SchemaDiffer()

    # Current snapshot with one table
    current_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="name", type="VARCHAR(100)", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    current_snapshot = SchemaSnapshot(tables=current_tables)

    operations = differ.detect_changes(None, current_snapshot)

    # Should create the table
    assert len(operations) == 1
    assert operations[0].operation_type == OperationType.CREATE_TABLE
    assert operations[0].table_name == "users"


def test_schema_differ_detect_changes_no_changes():
    """Test detecting changes when there are no changes."""
    differ = SchemaDiffer()

    # Same snapshot for both old and new
    tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="name", type="VARCHAR(100)", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    old_snapshot = SchemaSnapshot(tables=tables)
    new_snapshot = SchemaSnapshot(tables=tables)

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    # Should be no operations
    assert len(operations) == 0


def test_schema_differ_detect_table_creation():
    """Test detecting table creation."""
    differ = SchemaDiffer()

    # Old snapshot empty
    old_snapshot = SchemaSnapshot(tables=[])

    # New snapshot with table
    new_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    new_snapshot = SchemaSnapshot(tables=new_tables)

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    assert len(operations) == 1
    assert operations[0].operation_type == OperationType.CREATE_TABLE
    assert operations[0].table_name == "users"


def test_schema_differ_detect_table_deletion():
    """Test detecting table deletion."""
    differ = SchemaDiffer()

    # Old snapshot with table
    old_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    old_snapshot = SchemaSnapshot(tables=old_tables)

    # New snapshot empty
    new_snapshot = SchemaSnapshot(tables=[])

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    assert len(operations) == 1
    assert operations[0].operation_type == OperationType.DROP_TABLE
    assert operations[0].table_name == "users"


def test_schema_differ_detect_column_addition():
    """Test detecting column addition."""
    differ = SchemaDiffer()

    # Old snapshot with basic table
    old_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    old_snapshot = SchemaSnapshot(tables=old_tables)

    # New snapshot with additional column
    new_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="email", type="VARCHAR(255)", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    new_snapshot = SchemaSnapshot(tables=new_tables)

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    assert len(operations) == 1
    assert operations[0].operation_type == OperationType.ADD_COLUMN
    assert operations[0].table_name == "users"
    assert operations[0].object_name == "email"


def test_schema_differ_detect_column_removal():
    """Test detecting column removal."""
    differ = SchemaDiffer()

    # Old snapshot with two columns
    old_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="email", type="VARCHAR(255)", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    old_snapshot = SchemaSnapshot(tables=old_tables)

    # New snapshot with one column
    new_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    new_snapshot = SchemaSnapshot(tables=new_tables)

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    assert len(operations) == 1
    assert operations[0].operation_type == OperationType.DROP_COLUMN
    assert operations[0].table_name == "users"
    assert operations[0].object_name == "email"


def test_schema_differ_detect_column_alteration():
    """Test detecting column alteration."""
    differ = SchemaDiffer()

    # Old snapshot
    old_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="email", type="VARCHAR(100)", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    old_snapshot = SchemaSnapshot(tables=old_tables)

    # New snapshot with modified column
    new_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(
                    name="email", type="VARCHAR(255)", nullable=False
                ),  # Changed type and nullable
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    new_snapshot = SchemaSnapshot(tables=new_tables)

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    assert len(operations) == 1
    assert operations[0].operation_type == OperationType.ALTER_COLUMN
    assert operations[0].table_name == "users"
    assert operations[0].object_name == "email"


def test_schema_differ_detect_index_addition():
    """Test detecting index addition."""
    differ = SchemaDiffer()

    # Old snapshot without indexes
    old_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="email", type="VARCHAR(255)", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    old_snapshot = SchemaSnapshot(tables=old_tables)

    # New snapshot with index
    new_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="email", type="VARCHAR(255)", nullable=True),
            ],
            indexes=[
                IndexSnapshot(name="idx_email", columns=["email"], unique=True),
            ],
            foreign_keys=[],
        )
    ]
    new_snapshot = SchemaSnapshot(tables=new_tables)

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    assert len(operations) == 1
    assert operations[0].operation_type == OperationType.CREATE_INDEX
    assert operations[0].table_name == "users"
    assert operations[0].object_name == "idx_email"


def test_schema_differ_detect_index_removal():
    """Test detecting index removal."""
    differ = SchemaDiffer()

    # Old snapshot with index
    old_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="email", type="VARCHAR(255)", nullable=True),
            ],
            indexes=[
                IndexSnapshot(name="idx_email", columns=["email"], unique=True),
            ],
            foreign_keys=[],
        )
    ]
    old_snapshot = SchemaSnapshot(tables=old_tables)

    # New snapshot without index
    new_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="email", type="VARCHAR(255)", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    new_snapshot = SchemaSnapshot(tables=new_tables)

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    assert len(operations) == 1
    assert operations[0].operation_type == OperationType.DROP_INDEX
    assert operations[0].table_name == "users"
    assert operations[0].object_name == "idx_email"


def test_schema_differ_detect_foreign_key_addition():
    """Test detecting foreign key addition."""
    differ = SchemaDiffer()

    # Old snapshot without foreign keys
    old_tables = [
        TableSnapshot(
            name="posts",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="user_id", type="INTEGER", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    old_snapshot = SchemaSnapshot(tables=old_tables)

    # New snapshot with foreign key
    new_tables = [
        TableSnapshot(
            name="posts",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="user_id", type="INTEGER", nullable=True),
            ],
            indexes=[],
            foreign_keys=[
                ForeignKeySnapshot(
                    name="fk_user_id",
                    columns=["user_id"],
                    referred_table="users",
                    referred_columns=["id"],
                ),
            ],
        )
    ]
    new_snapshot = SchemaSnapshot(tables=new_tables)

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    assert len(operations) == 1
    assert operations[0].operation_type == OperationType.ADD_FOREIGN_KEY
    assert operations[0].table_name == "posts"
    assert operations[0].object_name == "fk_user_id"


def test_schema_differ_detect_foreign_key_removal():
    """Test detecting foreign key removal."""
    differ = SchemaDiffer()

    # Old snapshot with foreign key
    old_tables = [
        TableSnapshot(
            name="posts",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="user_id", type="INTEGER", nullable=True),
            ],
            indexes=[],
            foreign_keys=[
                ForeignKeySnapshot(
                    name="fk_user_id",
                    columns=["user_id"],
                    referred_table="users",
                    referred_columns=["id"],
                ),
            ],
        )
    ]
    old_snapshot = SchemaSnapshot(tables=old_tables)

    # New snapshot without foreign key
    new_tables = [
        TableSnapshot(
            name="posts",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="user_id", type="INTEGER", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    new_snapshot = SchemaSnapshot(tables=new_tables)

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    assert len(operations) == 1
    assert operations[0].operation_type == OperationType.DROP_FOREIGN_KEY
    assert operations[0].table_name == "posts"
    assert operations[0].object_name == "fk_user_id"


def test_schema_differ_detect_multiple_changes():
    """Test detecting multiple changes across tables."""
    differ = SchemaDiffer()

    # Old snapshot
    old_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="name", type="VARCHAR(100)", nullable=True),
            ],
            indexes=[],
            foreign_keys=[],
        )
    ]
    old_snapshot = SchemaSnapshot(tables=old_tables)

    # New snapshot with multiple changes
    new_tables = [
        TableSnapshot(
            name="users",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="name", type="VARCHAR(100)", nullable=True),
                ColumnSnapshot(
                    name="email", type="VARCHAR(255)", nullable=True
                ),  # New column
            ],
            indexes=[
                IndexSnapshot(
                    name="idx_email", columns=["email"], unique=True
                ),  # New index
            ],
            foreign_keys=[],
        ),
        TableSnapshot(  # New table
            name="posts",
            columns=[
                ColumnSnapshot(
                    name="id", type="INTEGER", nullable=False, primary_key=True
                ),
                ColumnSnapshot(name="title", type="VARCHAR(200)", nullable=False),
                ColumnSnapshot(name="user_id", type="INTEGER", nullable=True),
            ],
            indexes=[],
            foreign_keys=[
                ForeignKeySnapshot(
                    name="fk_user_id",
                    columns=["user_id"],
                    referred_table="users",
                    referred_columns=["id"],
                ),
            ],
        ),
    ]
    new_snapshot = SchemaSnapshot(tables=new_tables)

    operations = differ.detect_changes(old_snapshot, new_snapshot)

    # Should detect: ADD_COLUMN, CREATE_INDEX, CREATE_TABLE
    assert len(operations) >= 3

    operation_types = [op.operation_type for op in operations]
    assert OperationType.ADD_COLUMN in operation_types
    assert OperationType.CREATE_INDEX in operation_types
    assert OperationType.CREATE_TABLE in operation_types


def test_migration_operation_with_definitions():
    """Test MigrationOperation with old and new definitions."""
    old_column = ColumnSnapshot(name="email", type="VARCHAR(100)", nullable=True)
    new_column = ColumnSnapshot(name="email", type="VARCHAR(255)", nullable=False)

    op = MigrationOperation(
        operation_type=OperationType.ALTER_COLUMN,
        table_name="users",
        object_name="email",
        old_definition=old_column,
        new_definition=new_column,
    )

    assert op.old_definition == old_column
    assert op.new_definition == new_column
    assert str(op) == "ALTER COLUMN users.email"
