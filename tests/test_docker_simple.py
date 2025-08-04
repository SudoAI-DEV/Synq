"""Simplified Docker database tests for Synq."""

import subprocess
import time

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, text

# Use non-standard ports to avoid conflicts
POSTGRES_PORT = 55432
POSTGRES_CONTAINER = "synq-test-postgres-simple"


def is_docker_available() -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "ps"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
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


@pytest.fixture(scope="function")
def postgres_container():
    """Start a simple PostgreSQL container for testing."""
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
        "postgres:15-alpine",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            pytest.skip(f"Failed to start PostgreSQL container: {result.stderr}")

        # Wait for database to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "exec",
                        POSTGRES_CONTAINER,
                        "pg_isready",
                        "-U",
                        "testuser",
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
            pytest.skip("PostgreSQL container failed to start")

        # Additional wait for full initialization
        time.sleep(2)

        db_uri = (
            f"postgresql://testuser:testpass123@localhost:{POSTGRES_PORT}/synq_test"
        )

        yield db_uri

    finally:
        cleanup_container(POSTGRES_CONTAINER)


def test_docker_postgres_basic_connection(postgres_container):
    """Test basic PostgreSQL connection via Docker."""
    engine = create_engine(postgres_container)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        assert "PostgreSQL" in version


def test_docker_postgres_table_creation(postgres_container):
    """Test table creation in PostgreSQL Docker container."""
    engine = create_engine(postgres_container)

    # Create a simple table
    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS test_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL
            )
        """)
        )
        conn.commit()

        # Insert test data
        conn.execute(
            text("""
            INSERT INTO test_users (username, email) 
            VALUES ('testuser', 'test@example.com')
        """)
        )
        conn.commit()

        # Query data back
        result = conn.execute(text("SELECT username, email FROM test_users"))
        row = result.fetchone()
        assert row[0] == "testuser"
        assert row[1] == "test@example.com"

        # Clean up
        conn.execute(text("DROP TABLE test_users"))
        conn.commit()


@pytest.mark.integration
def test_docker_postgres_with_sqlalchemy_metadata(postgres_container):
    """Test SQLAlchemy MetaData with PostgreSQL Docker container."""
    engine = create_engine(postgres_container)

    # Create metadata with tables
    metadata = MetaData()

    users_table = Table(
        "users",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("username", String(50), unique=True, nullable=False),
        Column("email", String(100), unique=True, nullable=False),
    )

    posts_table = Table(
        "posts",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(200), nullable=False),
        Column("user_id", Integer, nullable=False),
    )

    # Create tables
    metadata.create_all(engine)

    try:
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            )
            tables = [row[0] for row in result.fetchall()]

            assert "users" in tables
            assert "posts" in tables

            # Test data insertion
            conn.execute(
                text("""
                INSERT INTO users (username, email) 
                VALUES ('dockeruser', 'docker@example.com')
            """)
            )

            conn.execute(
                text("""
                INSERT INTO posts (title, user_id) 
                VALUES ('Docker Test Post', 1)
            """)
            )
            conn.commit()

            # Test data retrieval
            result = conn.execute(
                text("""
                SELECT u.username, p.title 
                FROM users u 
                JOIN posts p ON u.id = p.user_id
            """)
            )
            row = result.fetchone()
            assert row[0] == "dockeruser"
            assert row[1] == "Docker Test Post"

    finally:
        # Clean up
        metadata.drop_all(engine)


def test_docker_availability():
    """Test that Docker is available for integration tests."""
    if is_docker_available():
        print("✅ Docker is available - integration tests can run")
    else:
        print("❌ Docker is not available - integration tests will be skipped")
        pytest.skip("Docker not available")


if __name__ == "__main__":
    # Run basic availability test
    test_docker_availability()

    print("Docker simple tests can be run with:")
    print("pytest tests/test_docker_simple.py -v -s")
