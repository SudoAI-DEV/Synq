"""Initialize command implementation."""

from pathlib import Path
from typing import Optional

import click

from synq.core.config import SynqConfig
from synq.utils.output import format_error, format_success, safe_echo


def init_command(
    metadata_path: str,
    db_uri: Optional[str],
    migrations_dir: str,
) -> None:
    """Initialize Synq in the current directory."""

    # Check if already initialized
    config_path = Path.cwd() / "synq.toml"
    if config_path.exists() and not click.confirm(
        f"Configuration file {config_path} already exists. Overwrite?"
    ):
        click.echo("Initialization cancelled.")
        return

    # Create configuration
    try:
        config = SynqConfig(
            metadata_path=metadata_path,
            db_uri=db_uri,
            migrations_dir=migrations_dir,
            snapshot_dir=f"{migrations_dir}/meta",
        )

        # Create directories
        migrations_path = Path(migrations_dir)
        snapshot_path = Path(f"{migrations_dir}/meta")

        migrations_path.mkdir(exist_ok=True)
        snapshot_path.mkdir(exist_ok=True)

        # Save configuration
        config.save_to_file(config_path)

        click.echo(format_success(f"Initialized Synq in {Path.cwd()}"))
        click.echo(safe_echo(f"📁 Created migrations directory: {migrations_path}"))
        click.echo(safe_echo(f"📁 Created snapshots directory: {snapshot_path}"))
        click.echo(safe_echo(f"⚙️  Created configuration file: {config_path}"))
        click.echo("")
        click.echo("Next steps:")
        click.echo("1. Define your SQLAlchemy models")
        click.echo(
            "2. Run 'synq generate \"Initial migration\"' to create your first migration"
        )

    except Exception as e:
        click.echo(format_error(f"Error initializing Synq: {e}"), err=True)
        raise click.Abort() from e
