"""Test fixtures for both SQLAlchemy 1.4 and 2.0 syntax."""

from datetime import datetime
from typing import Optional

from sqlalchemy import __version__ as sqlalchemy_version

# Determine SQLAlchemy version
SQLALCHEMY_VERSION = tuple(map(int, sqlalchemy_version.split(".")[:2]))
IS_SQLALCHEMY_2 = SQLALCHEMY_VERSION >= (2, 0)

if IS_SQLALCHEMY_2:
    # SQLAlchemy 2.0+ imports
    from sqlalchemy import DateTime, ForeignKey, MetaData, String, func
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

    class Base(DeclarativeBase):
        metadata = MetaData()

    # SQLAlchemy 2.0 models
    class User(Base):
        __tablename__ = "users"

        id: Mapped[int] = mapped_column(primary_key=True)
        username: Mapped[str] = mapped_column(String(50), unique=True)
        email: Mapped[str] = mapped_column(String(100), unique=True)
        is_active: Mapped[bool] = mapped_column(default=True)
        created_at: Mapped[Optional[datetime]] = mapped_column(
            DateTime, server_default=func.now()
        )

        posts: Mapped[list["Post"]] = relationship("Post", back_populates="author")

    class Post(Base):
        __tablename__ = "posts"

        id: Mapped[int] = mapped_column(primary_key=True)
        title: Mapped[str] = mapped_column(String(200))
        content: Mapped[Optional[str]] = mapped_column(String)
        author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
        published: Mapped[bool] = mapped_column(default=False)
        created_at: Mapped[Optional[datetime]] = mapped_column(
            DateTime, server_default=func.now()
        )

        author: Mapped["User"] = relationship("User", back_populates="posts")

    # Export metadata
    test_metadata_v2 = Base.metadata

else:
    # SQLAlchemy 1.4 imports
    from sqlalchemy import (
        Boolean,
        Column,
        DateTime,
        ForeignKey,
        Integer,
        MetaData,
        String,
        Table,
    )

    # SQLAlchemy 1.4 Table definitions
    test_metadata_v1 = MetaData()

    users_table = Table(
        "users",
        test_metadata_v1,
        Column("id", Integer, primary_key=True),
        Column("username", String(50), nullable=False, unique=True),
        Column("email", String(100), nullable=False, unique=True),
        Column("is_active", Boolean, default=True),
        Column("created_at", DateTime),
    )

    posts_table = Table(
        "posts",
        test_metadata_v1,
        Column("id", Integer, primary_key=True),
        Column("title", String(200), nullable=False),
        Column("content", String),
        Column("author_id", Integer, ForeignKey("users.id")),
        Column("published", Boolean, default=False),
        Column("created_at", DateTime),
    )


def get_test_metadata():
    """Get the appropriate metadata object for the current SQLAlchemy version."""
    if IS_SQLALCHEMY_2:
        return test_metadata_v2
    return test_metadata_v1


def get_sqlalchemy_version_info():
    """Get SQLAlchemy version information for testing."""
    return {
        "version": sqlalchemy_version,
        "version_tuple": SQLALCHEMY_VERSION,
        "is_v2": IS_SQLALCHEMY_2,
        "major": SQLALCHEMY_VERSION[0],
        "minor": SQLALCHEMY_VERSION[1],
    }


# Common test cases that work with both versions
def create_extended_metadata():
    """Create an extended metadata with more tables for comprehensive testing."""
    if IS_SQLALCHEMY_2:
        # SQLAlchemy 2.0 version
        class ExtendedBase(DeclarativeBase):
            metadata = MetaData()

        class Category(ExtendedBase):
            __tablename__ = "categories"

            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str] = mapped_column(String(100))
            description: Mapped[Optional[str]] = mapped_column(String)

        class Tag(ExtendedBase):
            __tablename__ = "tags"

            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str] = mapped_column(String(50), unique=True)
            color: Mapped[Optional[str]] = mapped_column(String(7))

        return ExtendedBase.metadata

    # SQLAlchemy 1.4 version
    extended_metadata = MetaData()

    categories_table = Table(
        "categories",
        extended_metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(100), nullable=False),
        Column("description", String),
    )

    tags_table = Table(
        "tags",
        extended_metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String(50), nullable=False, unique=True),
        Column("color", String(7)),
    )

    return extended_metadata
