"""SQLAlchemy PostgreSQL database engine, connection pooling, and session lifecycle.

Strictly PostgreSQL only. Configured with connection pre-ping and recycling
to maintain resilience against cloud poolers (e.g. Neon) and network blips.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv()

logger = logging.getLogger(__name__)

# Base declarative class for all SQLAlchemy 2.0 ORM models
Base = declarative_base()


def get_postgres_url() -> str:
    """Retrieves and standardizes the PostgreSQL connection URL for psycopg 3."""
    raw_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@127.0.0.1:5432/obscura",
    ).strip()

    # Normalize driver prefix for SQLAlchemy + psycopg
    if raw_url.startswith("postgresql://"):
        raw_url = "postgresql+psycopg://" + raw_url.removeprefix("postgresql://")
    elif raw_url.startswith("postgres://"):
        raw_url = "postgresql+psycopg://" + raw_url.removeprefix("postgres://")

    # If channel_binding is in query parameters and causes issues with certain drivers, clean it safely
    parsed = urlparse(raw_url)
    if parsed.query:
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        # channel_binding=require is handled natively by libpq/psycopg
        new_query = urlencode(query_params, doseq=True)
        raw_url = urlunparse(parsed._replace(query=new_query))

    return raw_url


DATABASE_URL = get_postgres_url()

# Configure resilient connection engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,      # Probes connection before giving to caller
    pool_recycle=300,        # Recycles connections every 5 minutes
    echo=False,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a thread-safe database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

