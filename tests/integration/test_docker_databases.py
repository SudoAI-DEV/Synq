"""Integration tests using Docker containers for databases."""

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Generator

import pytest

from synq.core.config import SynqConfig
from synq.core.database import DatabaseManager
from synq.core.migration import MigrationManager
from tests.fixtures_sqlalchemy_versions import get_test_metadata

# Use non-standard ports to avoid conflicts
POSTGRES_PORT = 55432
MYSQL_PORT = 33066
POSTGRES_CONTAINER = "synq-test-postgres"
MYSQL_CONTAINER = "synq-test-mysql"


def is_docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "ps"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def wait_for_db(container_name: str, max_retries: int = 30) -> bool:
    """Wait for database container to be ready."""
    for i in range(max_retries):
        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "pg_isready"]
                if "postgres" in container_name
                else [
                    "docker",
                    "exec",
                    container_name,
                    "mysqladmin",
                    "ping",
                    "-h",
                    "localhost",
                ],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            pass

        time.sleep(1)

    return False


def cleanup_container(container_name: str) -> None:
    """Clean up Docker container."""
    try:
        subprocess.run(
            ["docker", "stop", container_name], capture_output=True, timeout=10
        )
        subprocess.run(
            ["docker", "rm", container_name], capture_output=True, timeout=10
        )
    except subprocess.TimeoutExpired:
        pass


@pytest.fixture(scope="session")
def postgres_container() -> Generator[Dict[str, Any], None, None]:
    """Start PostgreSQL container for testing."""
    if not is_docker_available():
        pytest.skip("Docker not available")

    # Clean up any existing container
    cleanup_container(POSTGRES_CONTAINER)

    # Start PostgreSQL container
    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        POSTGRES_CONTAINER,
        "-p",
        f"{POSTGRES_PORT}:5432",
        "-e",
        "POSTGRES_PASSWORD=testpass123",
        "-e",
        "POSTGRES_USER=testuser",
        "-e",
        "POSTGRES_DB=synq_test",
        "-e",
        "POSTGRES_HOST_AUTH_METHOD=trust",
        "--tmpfs",
        "/var/lib/postgresql/data:rw",  # Use tmpfs for faster tests
        "postgres:15-alpine",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            pytest.skip(f"Failed to start PostgreSQL container: {result.stderr}")

        # Wait for database to be ready
        if not wait_for_db(POSTGRES_CONTAINER):
            pytest.skip("PostgreSQL container failed to start")

        # Additional wait for full initialization
        time.sleep(2)

        connection_info = {
            "host": "localhost",
            "port": POSTGRES_PORT,
            "database": "synq_test",
            "username": "testuser",
            "password": "testpass123",
            "url": f"postgresql://testuser:testpass123@localhost:{POSTGRES_PORT}/synq_test",
        }

        yield connection_info

    finally:
        cleanup_container(POSTGRES_CONTAINER)


@pytest.fixture(scope="session")
def mysql_container() -> Generator[Dict[str, Any], None, None]:
    """Start MySQL container for testing."""
    if not is_docker_available():
        pytest.skip("Docker not available")

    # Clean up any existing container
    cleanup_container(MYSQL_CONTAINER)

    # Start MySQL container
    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        MYSQL_CONTAINER,
        "-p",
        f"{MYSQL_PORT}:3306",
        "-e",
        "MYSQL_ROOT_PASSWORD=testpass123",
        "-e",
        "MYSQL_DATABASE=synq_test",
        "-e",
        "MYSQL_USER=testuser",
        "-e",
        "MYSQL_PASSWORD=testpass123",
        "--tmpfs",
        "/var/lib/mysql:rw",  # Use tmpfs for faster tests
        "mysql:8.0",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            pytest.skip(f"Failed to start MySQL container: {result.stderr}")

        # Wait for database to be ready (MySQL takes longer to start)
        max_retries = 60
        for i in range(max_retries):
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        MYSQL_CONTAINER,
                        "mysqladmin",
                        "ping",
                        "-h",
                        "localhost",
                    ],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    break
            except subprocess.TimeoutExpired:
                pass
            time.sleep(1)
        else:
            pytest.skip("MySQL container failed to start")

        # Additional wait for full initialization
        time.sleep(3)

        connection_info = {
            "host": "localhost",
            "port": MYSQL_PORT,
            "database": "synq_test",
            "username": "testuser",
            "password": "testpass123",
            "url": f"mysql+pymysql://testuser:testpass123@localhost:{MYSQL_PORT}/synq_test",
        }

        yield connection_info

    finally:
        cleanup_container(MYSQL_CONTAINER)


@pytest.fixture
def temp_migration_dir() -> Generator[Path, None, None]:
    """Create temporary directory for migrations."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.mark.integration
class TestPostgreSQLDockerIntegration:
    """Test PostgreSQL integration using Docker."""

    def test_postgres_full_workflow(
        self, postgres_container: Dict[str, Any], temp_migration_dir: Path
    ) -> None:
        """Test complete migration workflow with PostgreSQL."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations"),
            snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
            db_uri=postgres_container["url"],
        )

        migration_manager = MigrationManager(config)
        db_manager = DatabaseManager(config.db_uri)

        # Create initial migration
        metadata = get_test_metadata()
        migration_manager.create_migration(
            metadata=metadata,
            name="initial_migration",
            description="Initial PostgreSQL migration",
        )

        # Verify files created
        migration_files = list(config.migrations_path.glob("*.sql"))
        assert len(migration_files) == 1

        # Apply migration
        db_manager.ensure_migration_table()
        db_manager.apply_pending_migrations()

        # Verify tables created
        from sqlalchemy import create_engine, text

        engine = create_engine(postgres_container["url"])

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            tables = [row[0] for row in result.fetchall()]

            assert "users" in tables
            assert "posts" in tables
            assert "synq_migrations" in tables

    def test_postgres_constraints_and_indexes(
        self, postgres_container: Dict[str, Any], temp_migration_dir: Path
    ) -> None:
        """Test PostgreSQL-specific constraints and indexes."""
        from sqlalchemy import (
            Column,
            ForeignKey,
            Index,
            Integer,
            MetaData,
            String,
            Table,
            UniqueConstraint,
        )

        # Create metadata with constraints
        metadata = MetaData()

        users_table = Table(
            "users",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("username", String(50), nullable=False),
            Column("email", String(100), nullable=False),
            UniqueConstraint("username", "email", name="uq_user_credentials"),
        )

        posts_table = Table(
            "posts",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("title", String(200), nullable=False),
            Column("user_id", Integer, ForeignKey("users.id")),
            Index("idx_posts_user_id", "user_id"),
            Index("idx_posts_title", "title"),
        )

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations"),
            snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
            db_uri=postgres_container["url"],
        )

        migration_manager = MigrationManager(config)
        db_manager = DatabaseManager(config.db_uri)

        # Create and apply migration
        migration_manager.create_migration(
            metadata=metadata,
            name="constraints_test",
            description="Test constraints and indexes",
        )

        db_manager.ensure_migration_table()
        db_manager.apply_pending_migrations()

        # Verify constraints were created
        from sqlalchemy import create_engine, text

        engine = create_engine(postgres_container["url"])

        with engine.connect() as conn:
            # Check unique constraints
            result = conn.execute(
                text(
                    "SELECT constraint_name FROM information_schema.table_constraints "
                    "WHERE table_name = 'users' AND constraint_type = 'UNIQUE'"
                )
            )
            constraints = [row[0] for row in result.fetchall()]
            assert any("uq_user_credentials" in c for c in constraints)

            # Check indexes
            result = conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'posts'")
            )
            indexes = [row[0] for row in result.fetchall()]
            assert any("idx_posts_user_id" in idx for idx in indexes)


@pytest.mark.integration
class TestMySQLDockerIntegration:
    """Test MySQL integration using Docker."""

    def test_mysql_full_workflow(
        self, mysql_container: Dict[str, Any], temp_migration_dir: Path
    ) -> None:
        """Test complete migration workflow with MySQL."""
        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations"),
            snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
            db_uri=mysql_container["url"],
        )

        migration_manager = MigrationManager(config)
        db_manager = DatabaseManager(config.db_uri)

        # Create initial migration
        metadata = get_test_metadata()
        migration_manager.create_migration(
            metadata=metadata,
            name="initial_migration",
            description="Initial MySQL migration",
        )

        # Apply migration
        db_manager.ensure_migration_table()
        db_manager.apply_pending_migrations()

        # Verify tables created
        from sqlalchemy import create_engine, text

        engine = create_engine(mysql_container["url"])

        with engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]

            assert "users" in tables
            assert "posts" in tables
            assert "synq_migrations" in tables

    def test_mysql_charset_and_collation(
        self, mysql_container: Dict[str, Any], temp_migration_dir: Path
    ) -> None:
        """Test MySQL-specific charset and collation handling."""
        from sqlalchemy import Column, Integer, MetaData, String, Table

        # Create metadata with MySQL-specific options
        metadata = MetaData()

        users_table = Table(
            "users",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("username", String(50, collation="utf8mb4_unicode_ci")),
            Column("email", String(100)),
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations"),
            snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
            db_uri=mysql_container["url"],
        )

        migration_manager = MigrationManager(config)
        db_manager = DatabaseManager(config.db_uri)

        # Create and apply migration
        migration_manager.create_migration(
            metadata=metadata,
            name="charset_test",
            description="Test MySQL charset and collation",
        )

        db_manager.ensure_migration_table()
        db_manager.apply_pending_migrations()

        # Verify table was created with correct charset
        from sqlalchemy import create_engine, text

        engine = create_engine(mysql_container["url"])

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_collation FROM information_schema.tables "
                    "WHERE table_name = 'users' AND table_schema = 'synq_test'"
                )
            )
            collations = [row[0] for row in result.fetchall()]
            assert any("utf8mb4" in c for c in collations)


@pytest.mark.integration
class TestCrossDatabase:
    """Test compatibility across different databases."""

    def test_same_migration_different_databases(
        self,
        postgres_container: Dict[str, Any],
        mysql_container: Dict[str, Any],
        temp_migration_dir: Path,
    ) -> None:
        """Test that same migration works across different databases."""
        metadata = get_test_metadata()

        # Test with PostgreSQL
        pg_config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations_pg"),
            snapshot_dir=str(temp_migration_dir / "migrations_pg" / "meta"),
            db_uri=postgres_container["url"],
        )

        pg_migration_manager = MigrationManager(pg_config)
        pg_db_manager = DatabaseManager(pg_config)

        pg_migration_manager.create_migration(
            metadata=metadata,
            name="cross_database_test",
            description="Cross-database compatibility test",
        )

        pg_db_manager.ensure_migration_table()
        pg_db_manager.apply_pending_migrations()

        # Test with MySQL
        mysql_config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations_mysql"),
            snapshot_dir=str(temp_migration_dir / "migrations_mysql" / "meta"),
            db_uri=mysql_container["url"],
        )

        mysql_migration_manager = MigrationManager(mysql_config)
        mysql_db_manager = DatabaseManager(mysql_config)

        mysql_migration_manager.create_migration(
            metadata=metadata,
            name="cross_database_test",
            description="Cross-database compatibility test",
        )

        mysql_db_manager.ensure_migration_table()
        mysql_db_manager.apply_pending_migrations()

        # Verify both databases have the same tables
        from sqlalchemy import create_engine, text

        # Check PostgreSQL
        pg_engine = create_engine(postgres_container["url"])
        with pg_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            pg_tables = set(row[0] for row in result.fetchall())

        # Check MySQL
        mysql_engine = create_engine(mysql_container["url"])
        with mysql_engine.connect() as conn:
            result = conn.execute(text("SHOW TABLES"))
            mysql_tables = set(row[0] for row in result.fetchall())

        # Both should have the same core tables
        core_tables = {"users", "posts"}
        assert core_tables.issubset(pg_tables)
        assert core_tables.issubset(mysql_tables)


@pytest.mark.slow
@pytest.mark.integration
class TestDatabasePerformance:
    """Test database performance with containers."""

    def test_large_migration_postgres(
        self, postgres_container: Dict[str, Any], temp_migration_dir: Path
    ) -> None:
        """Test large migration performance with PostgreSQL."""
        from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table

        # Create large metadata (20 tables for Docker tests)
        metadata = MetaData()

        for i in range(20):
            columns = [Column("id", Integer, primary_key=True)]
            for j in range(5):
                columns.extend(
                    [
                        Column(f"varchar_col_{j}", String(100)),
                        Column(f"int_col_{j}", Integer),
                        Column(f"datetime_col_{j}", DateTime),
                    ]
                )

            Table(f"large_table_{i}", metadata, *columns)

        config = SynqConfig(
            metadata_path="test:metadata",
            migrations_dir=str(temp_migration_dir / "migrations"),
            snapshot_dir=str(temp_migration_dir / "migrations" / "meta"),
            db_uri=postgres_container["url"],
        )

        migration_manager = MigrationManager(config)
        db_manager = DatabaseManager(config.db_uri)

        # Measure migration creation time
        start_time = time.time()
        migration_manager.create_migration(
            metadata=metadata,
            name="large_migration_test",
            description="Large migration performance test",
        )
        creation_time = time.time() - start_time

        # Measure application time
        db_manager.ensure_migration_table()

        start_time = time.time()
        db_manager.apply_pending_migrations()
        application_time = time.time() - start_time

        # Performance assertions (adjust thresholds as needed)
        assert creation_time < 10.0  # 10 seconds max for creation
        assert application_time < 30.0  # 30 seconds max for application

        # Verify all tables were created
        from sqlalchemy import create_engine, text

        engine = create_engine(postgres_container["url"])

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name LIKE 'large_table_%'"
                )
            )
            tables = [row[0] for row in result.fetchall()]

            assert len(tables) == 20
