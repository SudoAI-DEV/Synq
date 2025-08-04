# Changelog

All notable changes to Synq will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Full support for SQLAlchemy 2.0+ declarative syntax with type annotations
- Django-style automatic migration naming system
- Intelligent migration name generation based on detected operations
- Optional custom migration names with `--name` flag
- Short `-y` flag for migrate command (replacing `--yes`)
- Comprehensive test suite with 50+ tests covering both SQLAlchemy versions
- Docker-based integration tests for PostgreSQL and MySQL
- Support for Python 3.13
- Pre-commit hooks with Ruff for code quality
- Extensive CI/CD pipeline with GitHub Actions
- Cross-database compatibility testing
- Performance testing with large schemas
- Security scanning with Bandit
- Dependency vulnerability scanning with Safety

### Changed
- Examples updated to use SQLAlchemy 2.0+ syntax by default
- Migration file naming improved with proper underscore separation
- Enhanced error handling and user feedback
- Switched from Black + isort to Ruff for formatting and linting
- Improved documentation with SQLAlchemy 2.0 examples

### Technical Improvements
- Added comprehensive type hints throughout codebase
- Improved test coverage to 85%+
- Added integration tests with real database containers
- Enhanced CI matrix testing across Python 3.9-3.13 and SQLAlchemy 1.4+/2.0+
- Automated PyPI publishing workflow
- Code quality gates with multiple linting tools

### Documentation
- Updated README with SQLAlchemy 2.0+ examples
- Added comprehensive CLI command reference
- Documented migration naming patterns
- Added database support matrix
- Created GitHub issue and PR templates
- Added development setup guide

## [0.1.0] - Initial Release

### Added
- Core snapshot-based migration system
- SQLAlchemy 1.4+ Table definition support
- CLI commands: init, generate, migrate, status
- SQLite, PostgreSQL, and MySQL support
- Basic migration file generation
- Schema snapshot system for offline diff generation
- Configuration management with TOML files
- Basic test suite
- MIT license
- Initial documentation

### Features
- Offline migration generation without database connection
- Fast file-based schema comparison
- Plain SQL migration files
- Simple CLI interface
- Cross-platform support (Linux, macOS, Windows)

---

## Development

### Setting up Development Environment

```bash
# Clone the repository
git clone https://github.com/SudoAI-DEV/Synq.git
cd synq

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run integration tests (requires Docker)
pytest tests/integration/

# Format code
ruff format .

# Lint code
ruff check .
```

### Running Tests

```bash
# Unit tests only
pytest tests/ -k "not integration"

# Integration tests (requires Docker)
pytest tests/integration/

# Specific database tests
pytest tests/integration/test_docker_databases.py::TestPostgreSQLDockerIntegration

# Performance tests
pytest -m slow

# All tests with coverage
pytest --cov=synq --cov-report=html
```

### Release Process

1. Update version in `synq/__init__.py`
2. Update CHANGELOG.md
3. Create git tag: `git tag v0.1.0`
4. Push tag: `git push origin v0.1.0`
5. GitHub Actions will automatically build and publish to PyPI