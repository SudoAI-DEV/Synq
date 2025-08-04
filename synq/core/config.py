"""Configuration management for Synq."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import toml


@dataclass
class SynqConfig:
    """Synq configuration container."""

    metadata_path: str
    db_uri: Optional[str] = None
    migrations_dir: str = "migrations"
    snapshot_dir: str = "migrations/meta"

    @classmethod
    def from_file(cls, config_path: Optional[Path] = None) -> "SynqConfig":
        """Load configuration from synq.toml file."""
        if config_path is None:
            config_path = Path.cwd() / "synq.toml"

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                "Run 'synq init' to create a new configuration file."
            )

        try:
            config_data = toml.load(config_path)
            synq_config = config_data.get("synq", {})

            return cls(
                metadata_path=synq_config["metadata_path"],
                db_uri=synq_config.get("db_uri"),
                migrations_dir=synq_config.get("migrations_dir", "migrations"),
                snapshot_dir=synq_config.get("snapshot_dir", "migrations/meta"),
            )
        except KeyError as e:
            raise ValueError(f"Missing required configuration key: {e}") from e
        except Exception as e:
            raise ValueError(f"Error parsing configuration file: {e}") from e

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary for TOML serialization."""
        result = {"metadata_path": self.metadata_path}

        if self.db_uri:
            result["db_uri"] = self.db_uri
        if self.migrations_dir != "migrations":
            result["migrations_dir"] = self.migrations_dir
        if self.snapshot_dir != "migrations/meta":
            result["snapshot_dir"] = self.snapshot_dir

        return {"synq": result}

    def save_to_file(self, config_path: Optional[Path] = None) -> None:
        """Save configuration to synq.toml file."""
        if config_path is None:
            config_path = Path.cwd() / "synq.toml"

        with open(config_path, "w") as f:
            toml.dump(self.to_dict(), f)

    @property
    def migrations_path(self) -> Path:
        """Get the migrations directory path."""
        return Path(self.migrations_dir)

    @property
    def snapshot_path(self) -> Path:
        """Get the snapshot directory path."""
        return Path(self.snapshot_dir)
