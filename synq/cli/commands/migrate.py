"""Migrate command implementation."""

from pathlib import Path
from typing import Optional

import click

from synq.core.config import SynqConfig
from synq.core.database import DatabaseManager
from synq.core.migration import MigrationManager


def migrate_command(
    config_path: Optional[Path], dry_run: bool, auto_confirm: bool = False
) -> None:
    """Apply all pending migrations to the database."""

    try:
        # Load configuration
        config = SynqConfig.from_file(config_path)

        if not config.db_uri:
            click.echo(
                "❌ No database URI configured. Please add 'db_uri' to your synq.toml file.",
                err=True,
            )
            raise click.Abort()

        # Initialize managers
        migration_manager = MigrationManager(config)
        db_manager = DatabaseManager(config.db_uri)

        # Get pending migrations
        click.echo("🔍 Checking for pending migrations...")
        pending_migrations = migration_manager.get_pending_migrations(db_manager)

        if not pending_migrations:
            click.echo("✅ No pending migrations. Database is up to date!")
            return

        click.echo(f"📋 Found {len(pending_migrations)} pending migration(s):")
        for migration in pending_migrations:
            click.echo(f"  • {migration.filename}")

        if dry_run:
            click.echo("🔍 Dry run mode - no changes will be applied")
            for migration in pending_migrations:
                click.echo(f"\n--- Migration: {migration.filename} ---")
                click.echo(migration.sql_content)
            return

        if not auto_confirm and not click.confirm(
            f"Apply {len(pending_migrations)} migration(s)?", default=True
        ):
            click.echo("Migration cancelled.")
            return

        # Apply migrations
        click.echo("🚀 Applying migrations...")

        for migration in pending_migrations:
            click.echo(f"⏳ Applying {migration.filename}...")

            try:
                db_manager.apply_migration(migration)
                click.echo(f"✅ Applied {migration.filename}")
            except Exception as e:
                click.echo(f"❌ Failed to apply {migration.filename}: {e}", err=True)
                click.echo("🔄 Rolling back transaction...")
                db_manager.rollback()
                raise click.Abort() from e

        click.echo(f"🎉 Successfully applied {len(pending_migrations)} migration(s)!")

    except Exception as e:
        click.echo(f"❌ Error during migration: {e}", err=True)
        raise click.Abort() from e
