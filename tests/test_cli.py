"""Tests for CLI commands."""

from pathlib import Path

from click.testing import CliRunner

from synq.cli.main import cli


def test_cli_help():
    """Test CLI help command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Synq" in result.output
    assert "snapshot-based database migration tool" in result.output


def test_init_command(temp_dir):
    """Test synq init command."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "init",
                "--metadata-path",
                "myapp.models:metadata",
                "--db-uri",
                "sqlite:///test.db",
                "--migrations-dir",
                "migrations",
            ],
        )

        assert result.exit_code == 0
        assert "Initialized Synq" in result.output

        # Check created files and directories
        assert Path("synq.toml").exists()
        assert Path("migrations").exists()
        assert Path("migrations/meta").exists()


def test_init_command_interactive(temp_dir):
    """Test synq init command with interactive input."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["init"], input="myapp.models:metadata\n")

        assert result.exit_code == 0
        assert "Initialized Synq" in result.output


def test_generate_command_no_config():
    """Test generate command without config file."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["generate", "Test migration"])

        assert result.exit_code == 1
        assert "Configuration file not found" in result.output


def test_migrate_command_no_config():
    """Test migrate command without config file."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["migrate"])

        assert result.exit_code == 1
        assert "Configuration file not found" in result.output


def test_status_command_no_config():
    """Test status command without config file."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 1
        assert "Configuration file not found" in result.output


def test_init_overwrite_existing(temp_dir):
    """Test init command with existing config file."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create initial config
        result = runner.invoke(
            cli,
            [
                "init",
                "--metadata-path",
                "myapp.models:metadata",
            ],
        )
        assert result.exit_code == 0

        # Try to init again, decline overwrite
        result = runner.invoke(
            cli,
            [
                "init",
                "--metadata-path",
                "other.models:metadata",
            ],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

        # Try to init again, accept overwrite
        result = runner.invoke(
            cli,
            [
                "init",
                "--metadata-path",
                "other.models:metadata",
            ],
            input="y\n",
        )

        assert result.exit_code == 0
        assert "Initialized Synq" in result.output


def test_generate_command_with_config(temp_dir):
    """Test generate command with valid config but import error."""
    from pathlib import Path

    import toml

    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create config file
        config_data = {
            "synq": {
                "metadata_path": "nonexistent.module:metadata",
                "db_uri": "sqlite:///test.db",
            }
        }
        with open("synq.toml", "w") as f:
            toml.dump(config_data, f)

        # Create migrations directory
        Path("migrations/meta").mkdir(parents=True)

        result = runner.invoke(cli, ["generate", "Test migration"])

        assert result.exit_code == 1  # Should fail due to import error
        assert "Error generating migration" in result.output


def test_migrate_command_with_config(temp_dir):
    """Test migrate command with valid config but no migrations."""
    import toml

    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create config file
        config_data = {
            "synq": {
                "metadata_path": "test.module:metadata",
                "db_uri": "sqlite:///nonexistent.db",
            }
        }
        with open("synq.toml", "w") as f:
            toml.dump(config_data, f)

        result = runner.invoke(cli, ["migrate"])

        assert result.exit_code == 0  # Should succeed when no migrations
        assert "No pending migrations" in result.output


def test_status_command_with_config(temp_dir):
    """Test status command with valid config but no migrations."""
    import toml

    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create config file
        config_data = {
            "synq": {
                "metadata_path": "nonexistent.module:metadata",
                "db_uri": "sqlite:///test.db",
            }
        }
        with open("synq.toml", "w") as f:
            toml.dump(config_data, f)

        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0  # Should succeed when no migrations
        assert "No migrations found" in result.output


def test_generate_command_custom_config_path():
    """Test generate command with custom config path."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["generate", "-c", "custom.toml", "Test"])

        assert result.exit_code == 2  # Click uses exit code 2 for argument errors
        assert "does not exist" in result.output


def test_migrate_command_dry_run():
    """Test migrate command with dry run flag."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["migrate", "--dry-run"])

        assert result.exit_code == 1
        assert "Configuration file not found" in result.output


def test_migrate_command_auto_yes():
    """Test migrate command with auto-yes flag."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["migrate", "-y"])

        assert result.exit_code == 1
        assert "Configuration file not found" in result.output


def test_generate_command_with_name_option():
    """Test generate command with custom name option."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["generate", "--name", "custom_migration"])

        assert result.exit_code == 1
        assert "Configuration file not found" in result.output
