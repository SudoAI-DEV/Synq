# Development Guide

This guide covers setting up Synq for development.

## Prerequisites

- Python 3.9 or higher
- pip or uv for package management

## Setup

1. Clone the repository:
```bash
git clone https://github.com/SudoAI-DEV/Synq.git
cd synq
```

2. Install in development mode:
```bash
# Using pip
pip install -e ".[dev]"

# Or using uv (recommended)
uv pip install -e ".[dev]"
```

3. Set up pre-commit hooks:
```bash
pre-commit install
```

## Development Workflow

### Running Tests

Run the full test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=synq --cov-report=html
```

Run specific test files:
```bash
pytest tests/test_config.py
```

### Code Quality

Format code:
```bash
ruff format synq/ tests/ examples/
ruff check --fix synq/ tests/ examples/
```

Run linting:
```bash
ruff check synq/ examples/
mypy synq/
```

Run all checks:
```bash
make check-all
```

### Testing Your Changes

1. Create test migrations in the `examples/` directory
2. Test CLI commands:
   ```bash
   cd examples
   synq init
   synq generate "Test migration"
   synq status
   ```

### Project Structure

```
synq/
├── synq/                   # Main package
│   ├── cli/               # CLI commands
│   ├── core/              # Core functionality
│   └── utils/             # Utilities
├── tests/                 # Test suite
├── examples/              # Usage examples
├── docs/                  # Documentation
└── pyproject.toml         # Package configuration
```

### Adding New Features

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Write tests first (TDD approach recommended)
3. Implement the feature
4. Update documentation if needed
5. Run the full test suite
6. Submit a pull request

### Database Testing

Test with different databases:

```bash
# SQLite (default)
pytest tests/test_database.py

# PostgreSQL (requires running instance)
DB_URI="postgresql://user:pass@localhost/testdb" pytest tests/test_database.py

# MySQL (requires running instance)  
DB_URI="mysql://user:pass@localhost/testdb" pytest tests/test_database.py
```

### Release Process

1. Update version in `synq/__init__.py`
2. Update `CHANGELOG.md`
3. Run `make build` to create distribution packages
4. Test the package: `pip install dist/synq_db-*.whl`
5. Upload to PyPI: `make upload`

## Architecture Overview

### Core Components

- **Config**: Configuration management (TOML files)
- **Snapshot**: Schema state capture and comparison
- **Diff**: Change detection between snapshots  
- **Migration**: SQL generation and file management
- **Database**: Connection and migration state tracking
- **CLI**: Command-line interface

### Key Design Decisions

1. **Snapshot-based**: Store schema state in JSON files rather than querying live databases
2. **SQLAlchemy Native**: Use SQLAlchemy's DDL compilation for cross-database SQL generation
3. **Offline-first**: Generate migrations without database connectivity
4. **File-based**: Store migrations as plain SQL files for transparency

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all checks pass
5. Submit a pull request

See `CONTRIBUTING.md` for detailed contribution guidelines.