"""Generate command implementation."""

from pathlib import Path
from typing import Optional

import click

from synq.core.config import SynqConfig
from synq.core.migration import MigrationManager
from synq.core.naming import generate_migration_name
from synq.core.snapshot import SnapshotManager
from synq.utils.import_utils import import_metadata_from_path, validate_metadata_object
from synq.utils.output import format_error, format_success, safe_echo


def generate_command(
    description: Optional[str], config_path: Optional[Path], custom_name: Optional[str]
) -> None:
    """Generate a new migration by comparing code to the latest snapshot."""

    try:
        # Load configuration
        config = SynqConfig.from_file(config_path)

        # Import metadata
        click.echo(safe_echo("📦 Loading SQLAlchemy metadata..."))
        metadata = import_metadata_from_path(config.metadata_path)
        validate_metadata_object(metadata)

        # Initialize managers
        snapshot_manager = SnapshotManager(config)
        migration_manager = MigrationManager(config)

        # Get current and previous snapshots
        click.echo(safe_echo("📸 Creating current schema snapshot..."))
        current_snapshot = snapshot_manager.create_snapshot(metadata)

        previous_snapshot = snapshot_manager.get_latest_snapshot()

        # Generate migration
        click.echo(safe_echo("🔍 Detecting schema changes..."))
        migration_ops = migration_manager.detect_changes(
            previous_snapshot, current_snapshot
        )

        if not migration_ops:
            click.echo(
                format_success("No schema changes detected. Nothing to migrate!")
            )
            return

        # Generate migration name
        if custom_name:
            migration_name = migration_manager.create_migration_name(custom_name)
            click.echo(safe_echo(f"🏷️  Using custom migration name: {custom_name}"))
        elif description:
            migration_name = migration_manager.create_migration_name(description)
            click.echo(safe_echo(f"🏷️  Using provided description: {description}"))
        else:
            # Auto-generate name based on operations
            auto_name = generate_migration_name(migration_ops)
            migration_name = migration_manager.create_migration_name(auto_name)
            click.echo(safe_echo(f"🤖 Auto-generated migration name: {auto_name}"))

        # Create migration files
        migration_number = snapshot_manager.get_next_migration_number()

        click.echo(
            safe_echo(
                f"📝 Generating migration {migration_number:04d}_{migration_name}..."
            )
        )

        # Generate SQL
        sql_content = migration_manager.generate_sql(migration_ops, metadata)

        # Save migration and snapshot
        migration_file = migration_manager.save_migration(
            migration_number, migration_name, sql_content
        )
        snapshot_file = snapshot_manager.save_snapshot(
            migration_number, current_snapshot
        )

        click.echo(format_success(f"Created migration: {migration_file}"))
        click.echo(format_success(f"Created snapshot: {snapshot_file}"))
        click.echo("")
        click.echo("Next steps:")
        click.echo("1. Review the generated SQL migration file")
        click.echo("2. Run 'synq migrate' to apply the migration to your database")

    except Exception as e:
        click.echo(format_error(f"Error generating migration: {e}"), err=True)
        raise click.Abort() from e
