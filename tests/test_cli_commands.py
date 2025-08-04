"""Comprehensive tests for CLI command implementations."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import click
import pytest
from click.testing import CliRunner
from sqlalchemy import Column, Integer, MetaData, Table

from synq.cli.commands.generate import generate_command
from synq.cli.commands.init import init_command
from synq.cli.commands.migrate import migrate_command
from synq.cli.commands.status import status_command
from synq.core.config import SynqConfig


def test_init_command_success():
    """Test successful initialization."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        init_command(
            metadata_path="test.models:metadata",
            db_uri="sqlite:///test.db",
            migrations_dir="migrations",
        )

        # Check that files were created
        assert Path("synq.toml").exists()
        assert Path("migrations").exists()
        assert Path("migrations/meta").exists()

        # Verify config content
        config = SynqConfig.from_file()
        assert config.metadata_path == "test.models:metadata"
        assert config.db_uri == "sqlite:///test.db"


def test_init_command_overwrite_existing():
    """Test initialization with existing config file."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create existing config
        Path("synq.toml").write_text('[synq]\nmetadata_path = "old:path"')

        # Mock click.confirm to return True (overwrite)
        with patch("click.confirm", return_value=True):
            init_command(
                metadata_path="new.models:metadata",
                db_uri="sqlite:///new.db",
                migrations_dir="migrations",
            )

        # Verify config was overwritten
        config = SynqConfig.from_file()
        assert config.metadata_path == "new.models:metadata"


def test_init_command_cancel_overwrite():
    """Test initialization cancelled when overwrite declined."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create existing config
        Path("synq.toml").write_text('[synq]\nmetadata_path = "old:path"')

        # Mock click.confirm to return False (don't overwrite)
        with patch("click.confirm", return_value=False):
            with patch("click.echo") as mock_echo:
                init_command(
                    metadata_path="new.models:metadata",
                    db_uri="sqlite:///new.db",
                    migrations_dir="migrations",
                )

                mock_echo.assert_any_call("Initialization cancelled.")


def test_init_command_error_handling():
    """Test error handling during initialization."""
    with patch(
        "synq.cli.commands.init.SynqConfig"
    ) as mock_config:  # Patch in the correct namespace
        mock_config.side_effect = Exception("Config creation failed")

        with patch("click.confirm", return_value=True):  # Mock confirm to return True
            with patch("click.echo") as mock_echo:
                with pytest.raises(click.Abort):  # click.Abort is the correct exception
                    init_command(
                        metadata_path="test:metadata",
                        db_uri="sqlite:///test.db",
                        migrations_dir="migrations",
                    )

                mock_echo.assert_any_call(
                    "❌ Error initializing Synq: Config creation failed", err=True
                )


def test_generate_command_successful_generation():
    """Test successful migration generation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_path = temp_path / "synq.toml"
        config = SynqConfig(
            metadata_path="test.models:metadata",
            migrations_dir=str(temp_path / "migrations"),
            snapshot_dir=str(temp_path / "migrations/meta"),
        )
        config.save_to_file(config_path)

        # Create test metadata
        metadata = MetaData()
        Table("users", metadata, Column("id", Integer, primary_key=True))

        with patch(
            "synq.cli.commands.generate.import_metadata_from_path",
            return_value=metadata,
        ):
            with patch("synq.cli.commands.generate.validate_metadata_object"):
                with patch(
                    "synq.cli.commands.generate.MigrationManager"
                ) as mock_manager:
                    with patch(
                        "synq.cli.commands.generate.SnapshotManager"
                    ) as mock_snapshot:
                        with patch(
                            "synq.core.naming.generate_migration_name",
                            return_value="create_users_table",
                        ):
                            # Mock the managers
                            mock_mgr_instance = Mock()
                            mock_snap_instance = Mock()
                            mock_manager.return_value = mock_mgr_instance
                            mock_snapshot.return_value = mock_snap_instance

                            # Mock method returns
                            mock_snap_instance.create_snapshot.return_value = Mock()
                            mock_snap_instance.get_latest_snapshot.return_value = None
                            mock_mgr_instance.detect_changes.return_value = [
                                Mock()
                            ]  # Non-empty operations
                            mock_mgr_instance.create_migration_name.return_value = (
                                "create_users_table"
                            )
                            mock_snap_instance.get_next_migration_number.return_value = 1
                            mock_mgr_instance.generate_sql.return_value = (
                                "CREATE TABLE users (id INTEGER);"
                            )
                            mock_mgr_instance.save_migration.return_value = Path(
                                "0001_create_users_table.sql"
                            )
                            mock_snap_instance.save_snapshot.return_value = Path(
                                "0001_snapshot.json"
                            )

                            with patch("click.echo") as mock_echo:
                                generate_command(
                                    description="Create users table",
                                    config_path=config_path,
                                    custom_name=None,
                                )

                                # Verify success messages were printed
                                mock_echo.assert_any_call(
                                    "📦 Loading SQLAlchemy metadata..."
                                )


def test_generate_command_no_changes():
    """Test generation when no schema changes are detected."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_path = temp_path / "synq.toml"
        config = SynqConfig(
            metadata_path="test.models:metadata",
            migrations_dir=str(temp_path / "migrations"),
            snapshot_dir=str(temp_path / "migrations/meta"),
        )
        config.save_to_file(config_path)

        # Create test metadata
        metadata = MetaData()
        Table("users", metadata, Column("id", Integer, primary_key=True))

        with patch(
            "synq.cli.commands.generate.import_metadata_from_path",
            return_value=metadata,
        ):
            with patch("synq.cli.commands.generate.validate_metadata_object"):
                with patch(
                    "synq.cli.commands.generate.MigrationManager"
                ) as mock_manager:
                    with patch(
                        "synq.cli.commands.generate.SnapshotManager"
                    ) as mock_snapshot:
                        # Mock the managers
                        mock_mgr_instance = Mock()
                        mock_snap_instance = Mock()
                        mock_manager.return_value = mock_mgr_instance
                        mock_snapshot.return_value = mock_snap_instance

                        # Mock no changes detected
                        mock_snap_instance.create_snapshot.return_value = Mock()
                        mock_snap_instance.get_latest_snapshot.return_value = Mock()
                        mock_mgr_instance.detect_changes.return_value = []  # Empty operations

                        with patch("click.echo") as mock_echo:
                            generate_command(
                                description=None,
                                config_path=config_path,
                                custom_name=None,
                            )

                            mock_echo.assert_any_call(
                                "✅ No schema changes detected. Nothing to migrate!"
                            )


def test_generate_command_with_custom_name():
    """Test generation with custom migration name."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_path = temp_path / "synq.toml"
        config = SynqConfig(
            metadata_path="test.models:metadata",
            migrations_dir=str(temp_path / "migrations"),
            snapshot_dir=str(temp_path / "migrations/meta"),
        )
        config.save_to_file(config_path)

        metadata = MetaData()
        Table("users", metadata, Column("id", Integer, primary_key=True))

        with patch(
            "synq.cli.commands.generate.import_metadata_from_path",
            return_value=metadata,
        ):
            with patch("synq.cli.commands.generate.validate_metadata_object"):
                with patch(
                    "synq.cli.commands.generate.MigrationManager"
                ) as mock_manager:
                    with patch(
                        "synq.cli.commands.generate.SnapshotManager"
                    ) as mock_snapshot:
                        # Mock the managers
                        mock_mgr_instance = Mock()
                        mock_snap_instance = Mock()
                        mock_manager.return_value = mock_mgr_instance
                        mock_snapshot.return_value = mock_snap_instance

                        # Mock with changes
                        mock_snap_instance.create_snapshot.return_value = Mock()
                        mock_snap_instance.get_latest_snapshot.return_value = None
                        mock_mgr_instance.detect_changes.return_value = [Mock()]
                        mock_mgr_instance.create_migration_name.return_value = (
                            "custom_migration"
                        )
                        mock_snap_instance.get_next_migration_number.return_value = 1
                        mock_mgr_instance.generate_sql.return_value = (
                            "CREATE TABLE users (id INTEGER);"
                        )
                        mock_mgr_instance.save_migration.return_value = Path(
                            "0001_custom_migration.sql"
                        )
                        mock_snap_instance.save_snapshot.return_value = Path(
                            "0001_snapshot.json"
                        )

                        with patch("click.echo") as mock_echo:
                            generate_command(
                                description=None,
                                config_path=config_path,
                                custom_name="custom_migration",
                            )

                            mock_echo.assert_any_call(
                                "🏷️  Using custom migration name: custom_migration"
                            )


def test_migrate_command_successful():
    """Test successful migration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_path = temp_path / "synq.toml"
        config = SynqConfig(
            metadata_path="test.models:metadata",
            db_uri="sqlite:///test.db",
            migrations_dir=str(temp_path / "migrations"),
            snapshot_dir=str(temp_path / "migrations/meta"),
        )
        config.save_to_file(config_path)

        with patch("synq.core.database.DatabaseManager") as mock_db:
            with patch("synq.cli.commands.generate.MigrationManager") as mock_migration:
                # Mock database manager
                mock_db_instance = Mock()
                mock_db.return_value = mock_db_instance
                mock_db_instance.get_applied_migrations.return_value = []

                # Mock migration manager
                mock_mgr_instance = Mock()
                mock_migration.return_value = mock_mgr_instance
                mock_mgr_instance.get_pending_migrations.return_value = [
                    Mock(
                        filename="0001_test.sql",
                        sql_content="CREATE TABLE test (id INTEGER);",
                    )
                ]

                with patch("click.echo") as mock_echo:
                    with patch("click.confirm", return_value=True):
                        migrate_command(
                            config_path=config_path, dry_run=False, auto_confirm=False
                        )

                        mock_echo.assert_any_call(
                            "🔍 Checking for pending migrations..."
                        )


def test_migrate_command_dry_run():
    """Test migrate command with dry run."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_path = temp_path / "synq.toml"
        config = SynqConfig(
            metadata_path="test.models:metadata",
            db_uri="sqlite:///test.db",
            migrations_dir=str(temp_path / "migrations"),
            snapshot_dir=str(temp_path / "migrations/meta"),
        )
        config.save_to_file(config_path)

        with patch("synq.cli.commands.migrate.DatabaseManager") as mock_db:
            with patch("synq.cli.commands.migrate.MigrationManager") as mock_migration:
                # Mock managers
                mock_db_instance = Mock()
                mock_db.return_value = mock_db_instance

                mock_mgr_instance = Mock()
                mock_migration.return_value = mock_mgr_instance
                mock_mgr_instance.get_pending_migrations.return_value = [
                    Mock(
                        filename="0001_test.sql",
                        sql_content="CREATE TABLE test (id INTEGER);",
                    )
                ]

                with patch("click.echo") as mock_echo:
                    migrate_command(
                        config_path=config_path, dry_run=True, auto_confirm=False
                    )

                    mock_echo.assert_any_call(
                        "🔍 Dry run mode - no changes will be applied"
                    )


def test_status_command_successful():
    """Test successful status command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_path = temp_path / "synq.toml"
        config = SynqConfig(
            metadata_path="test.models:metadata",
            db_uri="sqlite:///test.db",
            migrations_dir=str(temp_path / "migrations"),
            snapshot_dir=str(temp_path / "migrations/meta"),
        )
        config.save_to_file(config_path)

        # Create test metadata
        metadata = MetaData()
        Table("users", metadata, Column("id", Integer, primary_key=True))

        with patch(
            "synq.cli.commands.generate.import_metadata_from_path",
            return_value=metadata,
        ):
            with patch("synq.cli.commands.generate.validate_metadata_object"):
                with patch("synq.core.database.DatabaseManager") as mock_db:
                    with patch(
                        "synq.cli.commands.generate.MigrationManager"
                    ) as mock_migration:
                        with patch(
                            "synq.cli.commands.generate.SnapshotManager"
                        ) as mock_snapshot:
                            # Mock database manager
                            mock_db_instance = Mock()
                            mock_db.return_value = mock_db_instance
                            mock_db_instance.test_connection.return_value = True
                            mock_db_instance.get_applied_migrations.return_value = [
                                "0001_initial.sql"
                            ]

                            # Mock migration manager
                            mock_mgr_instance = Mock()
                            mock_migration.return_value = mock_mgr_instance
                            mock_mgr_instance.get_all_migrations.return_value = [
                                Mock(filename="0001_initial.sql"),
                                Mock(filename="0002_add_users.sql"),
                            ]
                            mock_mgr_instance.get_pending_migrations.return_value = [
                                Mock(filename="0002_add_users.sql")
                            ]

                            # Mock snapshot manager
                            mock_snap_instance = Mock()
                            mock_snapshot.return_value = mock_snap_instance
                            mock_snap_instance.create_snapshot.return_value = Mock()
                            mock_snap_instance.get_latest_snapshot.return_value = Mock()
                            mock_mgr_instance.detect_changes.return_value = []  # No pending changes

                            with patch("click.echo") as mock_echo:
                                status_command(config_path=config_path)

                                # Just verify the command ran without error
                                mock_echo.assert_called()


def test_status_command_with_pending_changes():
    """Test status command with pending schema changes."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_path = temp_path / "synq.toml"
        config = SynqConfig(
            metadata_path="test.models:metadata",
            db_uri="sqlite:///test.db",
            migrations_dir=str(temp_path / "migrations"),
            snapshot_dir=str(temp_path / "migrations/meta"),
        )
        config.save_to_file(config_path)

        metadata = MetaData()
        Table("users", metadata, Column("id", Integer, primary_key=True))

        from synq.core.diff import MigrationOperation, OperationType

        with patch(
            "synq.cli.commands.generate.import_metadata_from_path",
            return_value=metadata,
        ):
            with patch("synq.cli.commands.generate.validate_metadata_object"):
                with patch("synq.core.database.DatabaseManager") as mock_db:
                    with patch(
                        "synq.cli.commands.generate.MigrationManager"
                    ) as mock_migration:
                        with patch(
                            "synq.cli.commands.generate.SnapshotManager"
                        ) as mock_snapshot:
                            # Mock database manager
                            mock_db_instance = Mock()
                            mock_db.return_value = mock_db_instance
                            mock_db_instance.test_connection.return_value = True
                            mock_db_instance.get_applied_migrations.return_value = []

                            # Mock migration manager
                            mock_mgr_instance = Mock()
                            mock_migration.return_value = mock_mgr_instance
                            mock_mgr_instance.get_all_migrations.return_value = []
                            mock_mgr_instance.get_pending_migrations.return_value = []

                            # Mock snapshot manager with pending changes
                            mock_snap_instance = Mock()
                            mock_snapshot.return_value = mock_snap_instance
                            mock_snap_instance.create_snapshot.return_value = Mock()
                            mock_snap_instance.get_latest_snapshot.return_value = Mock()

                            # Mock pending schema changes
                            pending_op = MigrationOperation(
                                operation_type=OperationType.CREATE_TABLE,
                                table_name="users",
                            )
                            mock_mgr_instance.detect_changes.return_value = [pending_op]

                            with patch("click.echo") as mock_echo:
                                status_command(config_path=config_path)

                                # Just verify the command ran without error
                                mock_echo.assert_called()


def test_status_command_database_connection_error():
    """Test status command when database connection fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_path = temp_path / "synq.toml"
        config = SynqConfig(
            metadata_path="test.models:metadata",
            db_uri="sqlite:///nonexistent.db",
            migrations_dir=str(temp_path / "migrations"),
            snapshot_dir=str(temp_path / "migrations/meta"),
        )
        config.save_to_file(config_path)

        metadata = MetaData()

        with patch(
            "synq.cli.commands.generate.import_metadata_from_path",
            return_value=metadata,
        ):
            with patch("synq.cli.commands.generate.validate_metadata_object"):
                with patch("synq.core.database.DatabaseManager") as mock_db:
                    # Mock database connection failure
                    mock_db_instance = Mock()
                    mock_db.return_value = mock_db_instance
                    mock_db_instance.test_connection.return_value = False

                    with patch("click.echo") as mock_echo:
                        status_command(config_path=config_path)

                        # Just verify the command ran without error
                        mock_echo.assert_called()


def test_command_error_handling():
    """Test error handling in commands."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_path = temp_path / "synq.toml"
        config = SynqConfig(
            metadata_path="nonexistent.module:metadata",
            migrations_dir=str(temp_path / "migrations"),
            snapshot_dir=str(temp_path / "migrations/meta"),
        )
        config.save_to_file(config_path)

        # Test generate command error handling
        with patch("click.echo") as mock_echo:
            with pytest.raises(click.Abort):  # click.Abort is the correct exception
                generate_command(
                    description="Test", config_path=config_path, custom_name=None
                )

            # Just verify the command raised an error
            mock_echo.assert_called()


def test_migrate_command_no_pending():
    """Test migrate command when no pending migrations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create config file
        config_path = temp_path / "synq.toml"
        config = SynqConfig(
            metadata_path="test.models:metadata",
            db_uri="sqlite:///test.db",
            migrations_dir=str(temp_path / "migrations"),
            snapshot_dir=str(temp_path / "migrations/meta"),
        )
        config.save_to_file(config_path)

        with patch("synq.core.database.DatabaseManager") as mock_db:
            with patch("synq.cli.commands.generate.MigrationManager") as mock_migration:
                # Mock no pending migrations
                mock_db_instance = Mock()
                mock_db.return_value = mock_db_instance

                mock_mgr_instance = Mock()
                mock_migration.return_value = mock_mgr_instance
                mock_mgr_instance.get_pending_migrations.return_value = []

                with patch("click.echo") as mock_echo:
                    migrate_command(
                        config_path=config_path, dry_run=False, auto_confirm=False
                    )

                    mock_echo.assert_any_call(
                        "✅ No pending migrations. Database is up to date!"
                    )
