"""Main CLI entry point for Synq."""

from pathlib import Path
from typing import Optional

import click

from synq.cli.commands import generate as generate_cmd
from synq.cli.commands import init as init_cmd
from synq.cli.commands import migrate as migrate_cmd
from synq.cli.commands import status as status_cmd


@click.group()
@click.version_option()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    Synq - A modern, snapshot-based database migration tool for SQLAlchemy.

    Synq brings the fast, offline-first workflow of tools like Drizzle ORM
    to the Python and SQLAlchemy ecosystem.
    """
    ctx.ensure_object(dict)


@cli.command()
@click.option(
    "--metadata-path",
    prompt="Path to your SQLAlchemy MetaData object (e.g., 'myapp.models:metadata_obj')",
    help="Path to your SQLAlchemy MetaData instance",
)
@click.option(
    "--db-uri",
    help="Database connection string (optional, for migrations only)",
)
@click.option(
    "--migrations-dir",
    default="migrations",
    help="Directory to store migration files",
)
def init(
    metadata_path: str,
    db_uri: Optional[str],
    migrations_dir: str,
) -> None:
    """Initialize Synq in the current directory."""
    init_cmd.init_command(metadata_path, db_uri, migrations_dir)


@cli.command()
@click.argument("description", required=False)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to synq.toml configuration file",
)
@click.option(
    "--name",
    "-n",
    help="Custom migration name (overrides auto-generation)",
)
def generate(
    description: Optional[str], config: Optional[Path], name: Optional[str]
) -> None:
    """Generate a new migration by comparing code to the latest snapshot.

    If no description is provided, Synq will automatically generate a name
    based on the detected schema changes (similar to Django migrations).

    Examples:
      synq generate                          # Auto-generate name
      synq generate "Add user authentication" # Use description
      synq generate --name "custom_migration" # Use custom name
    """
    generate_cmd.generate_command(description, config, name)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to synq.toml configuration file",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be migrated without applying changes",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Automatically confirm migration application",
)
def migrate(config: Optional[Path], dry_run: bool, yes: bool) -> None:
    """Apply all pending migrations to the database."""
    migrate_cmd.migrate_command(config, dry_run, yes)


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to synq.toml configuration file",
)
def status(config: Optional[Path]) -> None:
    """Show the current state of the database and pending migrations."""
    status_cmd.status_command(config)


if __name__ == "__main__":
    cli()
