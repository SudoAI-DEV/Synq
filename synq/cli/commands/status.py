"""Status command implementation."""

from pathlib import Path
from typing import Optional

import click

from synq.core.config import SynqConfig
from synq.core.database import DatabaseManager
from synq.core.migration import MigrationManager


def status_command(config_path: Optional[Path]) -> None:
    """Show the current state of the database and pending migrations."""

    try:
        # Load configuration
        config = SynqConfig.from_file(config_path)

        # Initialize managers
        migration_manager = MigrationManager(config)

        # Get all migrations
        all_migrations = migration_manager.get_all_migrations()

        if not all_migrations:
            click.echo("📭 No migrations found.")
            click.echo(
                "Run 'synq generate \"Initial migration\"' to create your first migration."
            )
            return

        click.echo(f"📋 Total migrations: {len(all_migrations)}")

        # If no database URI, just show local migrations
        if not config.db_uri:
            click.echo("⚠️  No database URI configured - showing local migrations only:")
            for migration in all_migrations:
                click.echo(f"  📄 {migration.filename}")
            click.echo("\nAdd 'db_uri' to synq.toml to check database status.")
            return

        # Check database status
        try:
            db_manager = DatabaseManager(config.db_uri)
            applied_migrations = db_manager.get_applied_migrations()
            pending_migrations = migration_manager.get_pending_migrations(db_manager)

            click.echo(f"🗄️  Database: {config.db_uri}")
            click.echo(f"✅ Applied migrations: {len(applied_migrations)}")
            click.echo(f"⏳ Pending migrations: {len(pending_migrations)}")

            if applied_migrations:
                click.echo("\n✅ Applied migrations:")
                for migration_name in applied_migrations:
                    click.echo(f"  • {migration_name}")

            if pending_migrations:
                click.echo("\n⏳ Pending migrations:")
                for pending_migration in pending_migrations:
                    click.echo(f"  • {pending_migration.filename}")
                click.echo("\nRun 'synq migrate' to apply pending migrations.")
            else:
                click.echo("\n🎉 Database is up to date!")

        except Exception as e:
            click.echo(f"⚠️  Could not connect to database: {e}")
            click.echo("Showing local migrations only:")
            for migration_file in all_migrations:
                click.echo(f"  📄 {migration_file.filename}")

    except Exception as e:
        click.echo(f"❌ Error checking status: {e}", err=True)
        raise click.Abort() from e
