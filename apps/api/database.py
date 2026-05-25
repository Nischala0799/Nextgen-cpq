"""
database.py
-----------
SQLAlchemy setup for NextGen CPQ.

The Quote domain model is complex and nested, so quotes are stored as
JSON text in a single column rather than a normalized relational schema.
This keeps the persistence layer thin while allowing the domain model
to evolve freely.

The DATABASE_URL defaults to a local SQLite file. Override via the
DATABASE_URL environment variable for other engines (e.g. PostgreSQL).
"""

from __future__ import annotations

import os

from sqlalchemy import Column, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cpq_quotes.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class QuoteRecord(Base):
    __tablename__ = "quotes"

    quote_id = Column(String, primary_key=True, index=True)
    data = Column(Text, nullable=False)  # JSON-serialized Quote domain object


def init_db() -> None:
    """Create all tables. Safe to call multiple times (no-op if already exist)."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Return a new SQLAlchemy session. Caller is responsible for closing it."""
    return SessionLocal()
