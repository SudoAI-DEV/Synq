# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Synq is a modern, snapshot-based database migration tool for SQLAlchemy that brings the fast, offline-first workflow of tools like Drizzle ORM to the Python ecosystem. Unlike traditional reflection-based tools (like Alembic), Synq generates migrations by comparing your current SQLAlchemy MetaData to stored schema snapshots rather than connecting to a live database.

## Common Commands

### Development Setup
```bash
# Install in development mode with all dependencies
make install-dev
# or: pip install -e ".[dev]"

# Set up pre-commit hooks
make dev-setup
```

### Testing
```bash
# Run all tests
make test
# or: pytest

# Run tests with coverage (generates htmlcov/ directory)
make test-cov  
# or: pytest --cov=synq --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_config.py

# Run integration tests (may require database setup)
pytest tests/integration/
```

### Code Quality
```bash
# Run all checks (format, lint, test with coverage)
make check-all

# Format code
make format
# or: ruff format synq/ tests/ examples/ && ruff check --fix synq/ tests/ examples/

# Run linting only  
make lint
# or: ruff check synq/ examples/ && mypy synq/
```

### Building and Packaging
```bash
# Clean build artifacts
make clean

# Build package
make build

# Run example
make example
```

### CLI Testing
```bash
# Test CLI commands in examples directory
cd examples
synq init
synq generate "Test migration"
synq status
synq migrate -y
```

## Architecture Overview

### Core Components

**Snapshot System** (`synq/core/snapshot.py`):
- Stores schema state as JSON files in `migrations/meta/`
- Captures tables, columns, indexes, and foreign keys from SQLAlchemy MetaData
- Enables offline migration generation without database connections

**Configuration** (`synq/core/config.py`):
- Manages TOML-based configuration (`synq.toml`)
- Stores metadata path, database URI, and directory paths
- Required fields: `metadata_path` (e.g., "myapp.models:metadata_obj")

**Migration Management** (`synq/core/migration.py`):
- Generates SQL migrations by comparing snapshots
- Uses SQLAlchemy's DDL compilation for cross-database compatibility
- Creates numbered migration files (e.g., `0001_create_users_table.sql`)

**Diff Engine** (`synq/core/diff.py`):
- Compares current MetaData against latest snapshot
- Detects schema changes (tables, columns, indexes, constraints)
- Generates appropriate DDL operations

**Database Interface** (`synq/core/database.py`):
- Handles migration state tracking in database
- Applies SQL migration files to target database
- Manages migration history table

### CLI Structure (`synq/cli/`)

**Commands**:
- `init`: Initialize project structure and configuration
- `generate`: Create new migration from schema changes
- `migrate`: Apply pending migrations to database  
- `status`: Show migration status and pending changes

### Key Design Patterns

1. **Snapshot-Based Workflow**: Schema state stored in JSON files enables offline migration generation
2. **SQLAlchemy Native**: Uses SQLAlchemy's MetaData and DDL compilation for compatibility
3. **File-Based Migrations**: Plain SQL files for transparency and manual review
4. **Automatic Naming**: Intelligent migration names based on detected operations

### Project Structure
```
synq/
├── synq/                   # Main package
│   ├── __init__.py        # Package exports and version
│   ├── cli/               # CLI commands and entry point
│   ├── core/              # Core functionality (config, snapshot, diff, migration)
│   └── utils/             # Utility functions
├── tests/                 # Test suite with integration tests
├── examples/              # Usage examples and testing
└── migrations/            # Generated migrations (created by synq init)
    └── meta/              # Snapshot JSON files
```

### Testing Strategy

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test with real database connections (SQLite, PostgreSQL, MySQL)
- **CLI Tests**: Test complete workflows via command-line interface
- **Coverage**: Aim for high coverage with `pytest --cov=synq`

### Database Support

Supports all SQLAlchemy-compatible databases:
- SQLite (built-in)
- PostgreSQL (install with `pip install synq-db[postgres]`)
- MySQL (install with `pip install synq-db[mysql]`)
- Other databases via appropriate SQLAlchemy drivers

### Configuration

The `synq.toml` file must contain:
```toml
[synq]
metadata_path = "myapp.models:metadata_obj"  # Required: path to MetaData
db_uri = "postgresql://user:pass@localhost/db"  # Optional: for migrations only
migrations_dir = "migrations"  # Optional: default shown
snapshot_dir = "migrations/meta"  # Optional: default shown
```

### Migration Workflow

1. **Generate**: Compare current MetaData to latest snapshot, create migration files
2. **Review**: Inspect generated SQL migration file  
3. **Apply**: Run migration against database with `synq migrate`
4. **Track**: Migration state stored in database table for consistency

## Important Notes

- The package name is `synq-db` on PyPI but the CLI command is `synq`
- Migration generation works offline (no database connection needed)
- Migration application requires database connection (configured in `synq.toml`)
- Snapshots are stored as JSON files and should be committed to version control
- SQL migration files are plain text and can be manually reviewed/modified
- Repository URL: https://github.com/SudoAI-DEV/Synq.git (all placeholder URLs updated)
- Installation now includes database-specific options in Quick Start section
- Optional dependencies configured correctly for `pip install synq-db[postgres]` and `pip install synq-db[mysql]` syntax
- Automated PyPI publishing with GitHub Actions: tests + TestPyPI + PyPI + GitHub Release (see docs/PUBLISHING.md)