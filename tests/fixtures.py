"""Test fixtures for Synq tests."""

from sqlalchemy import Column, Integer, MetaData, String, Table

# Test metadata for import testing
test_metadata = MetaData()

Table(
    "users",
    test_metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(50), nullable=False),
    Column("email", String(50), unique=True),
)
