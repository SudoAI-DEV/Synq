"""Tests for configuration management."""

from pathlib import Path

import pytest
import toml

from synq.core.config import SynqConfig


def test_config_creation():
    """Test creating a configuration object."""
    config = SynqConfig(
        metadata_path="myapp.models:metadata",
        db_uri="postgresql://user:pass@localhost/db",
        migrations_dir="migrations",
        snapshot_dir="migrations/meta",
    )

    assert config.metadata_path == "myapp.models:metadata"
    assert config.db_uri == "postgresql://user:pass@localhost/db"
    assert config.migrations_dir == "migrations"
    assert config.snapshot_dir == "migrations/meta"


def test_config_to_dict():
    """Test converting configuration to dictionary."""
    config = SynqConfig(
        metadata_path="myapp.models:metadata",
        db_uri="postgresql://user:pass@localhost/db",
    )

    result = config.to_dict()
    expected = {
        "synq": {
            "metadata_path": "myapp.models:metadata",
            "db_uri": "postgresql://user:pass@localhost/db",
        }
    }

    assert result == expected


def test_config_save_and_load(temp_dir):
    """Test saving and loading configuration."""
    config_path = temp_dir / "synq.toml"

    # Create and save config
    config = SynqConfig(
        metadata_path="myapp.models:metadata",
        db_uri="postgresql://user:pass@localhost/db",
    )
    config.save_to_file(config_path)

    # Verify file exists and has correct content
    assert config_path.exists()

    # Load config back
    loaded_config = SynqConfig.from_file(config_path)
    assert loaded_config.metadata_path == config.metadata_path
    assert loaded_config.db_uri == config.db_uri


def test_config_missing_file():
    """Test loading configuration from missing file."""
    with pytest.raises(FileNotFoundError):
        SynqConfig.from_file(Path("nonexistent.toml"))


def test_config_missing_required_key(temp_dir):
    """Test loading configuration with missing required key."""
    config_path = temp_dir / "bad_config.toml"

    # Create config without required metadata_path
    with open(config_path, "w") as f:
        toml.dump({"synq": {"db_uri": "sqlite:///test.db"}}, f)

    with pytest.raises(ValueError, match="Missing required configuration key"):
        SynqConfig.from_file(config_path)


def test_config_invalid_toml_file(temp_dir):
    """Test loading configuration from invalid TOML file."""
    config_path = temp_dir / "invalid.toml"

    # Create invalid TOML content
    with open(config_path, "w") as f:
        f.write("invalid toml content [[[")

    with pytest.raises(ValueError, match="Error parsing configuration file"):
        SynqConfig.from_file(config_path)


def test_config_properties():
    """Test configuration properties."""
    config = SynqConfig(
        metadata_path="test:metadata",
        migrations_dir="custom_migrations",
        snapshot_dir="custom_snapshots",
    )

    assert config.migrations_path == Path("custom_migrations")
    assert config.snapshot_path == Path("custom_snapshots")


def test_config_to_dict_with_custom_paths():
    """Test converting config to dict with custom paths."""
    config = SynqConfig(
        metadata_path="test:metadata",
        db_uri="sqlite:///test.db",
        migrations_dir="custom_migrations",
        snapshot_dir="custom_snapshots",
    )

    result = config.to_dict()
    expected = {
        "synq": {
            "metadata_path": "test:metadata",
            "db_uri": "sqlite:///test.db",
            "migrations_dir": "custom_migrations",
            "snapshot_dir": "custom_snapshots",
        }
    }

    assert result == expected


def test_config_to_dict_minimal():
    """Test converting minimal config to dict."""
    config = SynqConfig(metadata_path="test:metadata")

    result = config.to_dict()
    expected = {"synq": {"metadata_path": "test:metadata"}}

    assert result == expected


def test_config_save_to_file_default_path(temp_dir):
    """Test saving config to default file path."""
    import os

    original_cwd = os.getcwd()

    try:
        # Change to temp directory
        os.chdir(temp_dir)

        config = SynqConfig(metadata_path="test:metadata", db_uri="sqlite:///test.db")

        # Save without specifying path (should use default)
        config.save_to_file()

        # Check that synq.toml was created in current directory
        default_path = Path.cwd() / "synq.toml"
        assert default_path.exists()

        # Verify content
        loaded_config = SynqConfig.from_file()
        assert loaded_config.metadata_path == config.metadata_path
        assert loaded_config.db_uri == config.db_uri

    finally:
        os.chdir(original_cwd)


def test_config_from_file_default_path(temp_dir):
    """Test loading config from default file path."""
    import os

    original_cwd = os.getcwd()

    try:
        # Change to temp directory
        os.chdir(temp_dir)

        # Create config file in current directory
        config_data = {
            "synq": {"metadata_path": "test:metadata", "db_uri": "sqlite:///test.db"}
        }

        with open("synq.toml", "w") as f:
            toml.dump(config_data, f)

        # Load without specifying path (should use default)
        config = SynqConfig.from_file()

        assert config.metadata_path == "test:metadata"
        assert config.db_uri == "sqlite:///test.db"

    finally:
        os.chdir(original_cwd)
