<div align="center">
  <h1 align="center">Synq</h1>
  <p align="center">
    A modern, snapshot-based database migration tool for SQLAlchemy.
  </p>

  <p align="center">
    <a href="https://pypi.org/project/synq-db/"><img alt="PyPI" src="https://img.shields.io/pypi/v/synq-db?color=blue"></a>
    <a href="https://github.com/SudoAI-DEV/Synq/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/SudoAI-DEV/Synq/actions/workflows/ci.yml/badge.svg"></a>
    <a href="https://github.com/SudoAI-DEV/Synq/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/pypi/l/synq-db"></a>
  </p>
</div>

---

**Synq** brings the fast, offline-first workflow of tools like [Drizzle ORM](https://orm.drizzle.team/) to the Python and SQLAlchemy ecosystem. Instead of connecting to a database to detect schema changes (reflection), Synq uses schema snapshots to generate new migrations. This makes the process deterministic, incredibly fast, and independent of your database's state during development.

## Core Philosophy

Why choose Synq? It's all about the workflow.

| Feature                 | **Synq (Snapshot-based)** | **Traditional (Reflection-based e.g., Alembic)** |
| ----------------------- | ----------------------------------------------------------- | ------------------------------------------------------- |
| **Generation Source** | Compares your code (`MetaData`) to a **local snapshot file**. | Compares your code (`MetaData`) to a **live database**. |
| **DB Connection?** | **Not required** to generate migrations.                    | **Required** to generate migrations.                    |
| **Speed** | Extremely fast file-based comparison.                       | Slower, involves network latency and DB queries.        |
| **Determinism** | 100% deterministic. The output only depends on your code.   | Can be influenced by the state of the reference DB.     |
| **Workflow** | Ideal for offline development and clean CI/CD pipelines.    | Tightly coupled with a development database instance.   |

## ✨ Key Features

* **Offline Migration Generation**: Create new SQL migration scripts without ever touching a database.
* **Snapshot-based Diffing**: Synq creates a `snapshot.json` file for each migration, representing the state of your schema at that point in time.
* **Pure SQL Migrations**: Generates plain, easy-to-read `.sql` files that you can inspect and even modify before applying.
* **Simple & Modern CLI**: A clean, intuitive command-line interface to manage your migration lifecycle.
* **SQLAlchemy Native**: Built on top of SQLAlchemy's powerful `MetaData` and dialect-specific DDL compilation.

## 🚀 Quick Start

#### 1. Installation

```bash
# Basic installation (includes SQLite support)
pip install synq-db

# With PostgreSQL support
pip install synq-db[postgres]

# With MySQL support  
pip install synq-db[mysql]

# With all database drivers
pip install synq-db[postgres,mysql]
```
*(Note: The package name is `synq-db` to avoid conflicts, but the command is `synq`)*

#### 2. Initialize Synq

In your project root, run:

```bash
synq init
```

This will create a `migrations` directory and a `synq.toml` configuration file.

```
.
├── my_app/
│   └── models.py
├── migrations/
│   └── meta/
└── synq.toml
```

#### 3. Define Your Models

Synq supports both SQLAlchemy 1.4+ Table definitions and SQLAlchemy 2.0+ declarative models.

**SQLAlchemy 2.0+ (Recommended):**

```python
# my_app/models.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

metadata_obj = Base.metadata  # Reference for Synq

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )
    
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    author: Mapped["User"] = relationship("User", back_populates="posts")
```

**SQLAlchemy 1.4+ (Legacy):**

```python
# my_app/models.py
from sqlalchemy import MetaData, Table, Column, Integer, String, ForeignKey

metadata_obj = MetaData()

users_table = Table(
    "users", metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("username", String(50), nullable=False, unique=True),
    Column("email", String(100), nullable=False, unique=True),
)

posts_table = Table(
    "posts", metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("title", String(200), nullable=False),
    Column("author_id", Integer, ForeignKey("users.id")),
)
```

#### 4. Configure Synq

Edit `synq.toml` to point to your `MetaData` object and your database URI.

```toml
# synq.toml
[synq]
# Path to your SQLAlchemy MetaData instance
metadata_path = "my_app.models:metadata_obj"

# Database connection string (used only for 'migrate')
db_uri = "postgresql://user:password@localhost/mydatabase"
```

#### 5. Generate Your First Migration

Synq can automatically generate intelligent migration names, or you can provide your own:

```bash
# Auto-generate name based on detected changes
synq generate

# Provide a custom description  
synq generate "Create user and post tables"

# Use a specific name (overrides auto-generation)
synq generate --name "initial_schema"
```

Synq compares your code with an empty state and creates two new files:

```
migrations/
├── 0000_initial_migration.sql  # The generated SQL
└── meta/
    └── 0000_snapshot.json      # The schema snapshot
```

**Example generated migration names:**
- `create_users_table` - Single table creation
- `add_email_to_users` - Single column addition  
- `initial_migration` - Multiple table creation
- `update_schema` - Mixed operations across tables

#### 6. Apply the Migration

Run the migration against your database.

```bash
synq migrate -y
```

Synq connects to the database, checks which migrations haven't been applied, and runs the SQL script. Your database is now in sync with your models!

#### 7. Iterative Development

As you modify your models, Synq detects changes and generates new migrations:

```bash
# Add new models or modify existing ones in your code
# Then generate a new migration
synq generate  # Automatically detects changes

# Apply the new migration
synq migrate -y

# Check status anytime
synq status
```

## CLI Command Reference

### `synq init`
Initializes the project structure with migration directories and configuration.

```bash
synq init --metadata-path "myapp.models:metadata_obj" --db-uri "postgresql://..."
```

### `synq generate`
Generates a new migration by comparing your current schema to the latest snapshot.

```bash
# Auto-generate name based on detected operations
synq generate

# Provide custom description
synq generate "Add user authentication"

# Use specific name (overrides auto-generation)  
synq generate --name "v2_auth_system"

# Use custom config file
synq generate -c /path/to/synq.toml
```

### `synq migrate`
Applies all pending migrations to the database.

```bash
# Interactive mode (prompts for confirmation)
synq migrate

# Auto-confirm all migrations
synq migrate -y

# Dry run (show what would be applied)
synq migrate --dry-run
```

### `synq status`
Shows the current migration status and pending changes.

```bash
synq status
```

## Supported Databases

Synq supports all databases that SQLAlchemy supports:

- **SQLite** - Built-in support
- **PostgreSQL** - Install: `pip install synq-db[postgres]`
- **MySQL** - Install: `pip install synq-db[mysql]`
- **Oracle, SQL Server, etc.** - Use appropriate SQLAlchemy drivers

## Python & SQLAlchemy Support

- **Python**: 3.9, 3.10, 3.11, 3.12, 3.13
- **SQLAlchemy**: 1.4+ and 2.0+
- **Operating Systems**: Linux, macOS, Windows

## Migration Naming

Synq automatically generates intelligent migration names based on detected operations:

| Operations | Generated Name | Example |
|------------|----------------|---------|
| Single table creation | `create_{table}_table` | `create_users_table` |
| Multiple table creation | `initial_migration` | `initial_migration` |
| Single column addition | `add_{column}_to_{table}` | `add_email_to_users` |
| Multiple columns to one table | `add_columns_to_{table}` | `add_columns_to_users` |
| Mixed operations on one table | `update_{table}_schema` | `update_users_schema` |
| Mixed operations on multiple tables | `update_schema` | `update_schema` |
| Table deletion | `delete_{table}_table` | `delete_old_table` |
| Index creation | `add_{index}_to_{table}` | `add_email_index_to_users` |

You can always override auto-generated names with `--name` or by providing a description.

## 🤝 Contributing

Contributions are welcome! We are excited to see this project grow with the help of the community. Please see our `CONTRIBUTING.md` file for guidelines on how to get started.

## 📜 License

Synq is licensed under the **MIT License**. See the `LICENSE` file for more details.

## 🙏 Acknowledgments

* Heavily inspired by the fantastic workflow of **[Drizzle ORM](https://orm.drizzle.team/)**.
* Built on the powerful and robust foundation of **[SQLAlchemy](https://www.sqlalchemy.org/)**.
