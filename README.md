<div align="center">
  <h1 align="center">Synq</h1>
  <p align="center">
    A modern, snapshot-based database migration tool for SQLAlchemy.
  </p>

  <p align="center">
    <a href="https://pypi.org/project/synq-db/"><img alt="PyPI" src="https://img.shields.io/pypi/v/synq-db?color=blue"></a>
    <a href="https://github.com/your-username/synq/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/your-username/synq/actions/workflows/ci.yml/badge.svg"></a>
    <a href="https://github.com/your-username/synq/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/pypi/l/synq-db"></a>
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
pip install synq-db
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

Create your SQLAlchemy models in `my_app/models.py` as you normally would.

```python
# my_app/models.py
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String

# It's crucial to have a single MetaData instance for your project
metadata_obj = MetaData()

user_table = Table(
    "users",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("name", String(50), nullable=False),
    Column("email", String(50), unique=True),
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

Now, generate the SQL script.

```bash
synq generate "Create user table"
```

Synq compares your code with an empty state and creates two new files:

```
migrations/
├── 0000_create_user_table.sql  # The generated SQL
└── meta/
    └── 0000_snapshot.json      # The schema snapshot
```

#### 6. Apply the Migration

Run the migration against your database.

```bash
synq migrate
```

Synq connects to the database, checks which migrations haven't been applied, and runs the `0000_create_user_table.sql` script. Your database is now in sync with your models!

## CLI Command Reference

* `synq init`: Initializes the project structure.
* `synq generate "<description>"`: Generates a new migration by comparing code to the latest snapshot.
* `synq migrate`: Applies all pending migrations to the database.
* `synq status`: Shows the current state of the database and pending migrations.

## 🤝 Contributing

Contributions are welcome! We are excited to see this project grow with the help of the community. Please see our `CONTRIBUTING.md` file for guidelines on how to get started.

## 📜 License

Synq is licensed under the **MIT License**. See the `LICENSE` file for more details.

## 🙏 Acknowledgments

* Heavily inspired by the fantastic workflow of **[Drizzle ORM](https://orm.drizzle.team/)**.
* Built on the powerful and robust foundation of **[SQLAlchemy](https://www.sqlalchemy.org/)**.
