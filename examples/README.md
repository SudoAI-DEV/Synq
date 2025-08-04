# Synq Examples

This directory contains examples demonstrating how to use Synq.

## Basic Usage

The `basic_usage.py` file shows a simple setup with SQLAlchemy tables.

To try it out:

1. Install Synq: `pip install synq-db`
2. Navigate to this directory
3. Initialize Synq: `synq init`
4. When prompted, enter: `examples.basic_usage:metadata_obj`
5. Generate your first migration: `synq generate "Initial migration"`
6. Set up a database URI in `synq.toml`
7. Apply the migration: `synq migrate`

## Auto-Generated Migration Names (Django-style)

Synq can automatically generate intelligent migration names based on schema changes:

```bash
# Auto-generate name based on operations
synq generate                    # → create_users_table, add_email_to_user, etc.

# Use your own description  
synq generate "Add user auth"    # → add_user_auth

# Use custom name (overrides everything)
synq generate --name "v2_auth"   # → v2_auth
```

## Migration Naming Examples

Based on the operations detected, Synq generates names like:

- **Single table creation**: `create_users_table`
- **Multiple table creation**: `initial_migration`
- **Single column addition**: `add_email_to_users`
- **Multiple columns**: `add_columns_to_users`
- **Mixed operations on one table**: `update_users_schema`
- **Mixed operations on multiple tables**: `update_schema`

## Adding More Tables

Try adding new tables to `basic_usage.py` and running:

```bash
synq generate              # Auto-generates intelligent name
synq migrate -y            # Apply changes
```

This will demonstrate how Synq detects schema changes and generates appropriately named migrations.

## Configuration

Your `synq.toml` should look like:

```toml
[synq]
metadata_path = "examples.basic_usage:metadata_obj"
db_uri = "sqlite:///example.db"  # or your database URI
```

## Migration Files

After running the commands above, you'll see:

```
migrations/
├── 0000_initial_migration.sql
├── 0001_add_comments_table.sql  # if you added the comments table
└── meta/
    ├── 0000_snapshot.json
    └── 0001_snapshot.json
```

The `.sql` files contain the actual migration SQL, while the `.json` files contain the schema snapshots used for diffing.