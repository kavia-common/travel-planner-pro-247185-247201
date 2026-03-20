"""
Database configuration and session management.

Provides SQLAlchemy engine and session factory for PostgreSQL connectivity.
Reads DATABASE_URL from environment. If not set, constructs one from the
individual POSTGRES_* variables provided by the database_postgresql container:
  POSTGRES_URL, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()


def _build_database_url() -> str:
    """
    Build the database connection URL.

    Priority:
    1. DATABASE_URL environment variable (if set explicitly).
    2. POSTGRES_URL environment variable (provided by the database container).
    3. Construct from POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT.
    4. Default fallback for local development.
    """
    # 1. Explicit DATABASE_URL
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    # 2. POSTGRES_URL from database container
    postgres_url = os.getenv("POSTGRES_URL")
    if postgres_url:
        return postgres_url

    # 3. Construct from individual POSTGRES_* variables
    pg_user = os.getenv("POSTGRES_USER")
    pg_password = os.getenv("POSTGRES_PASSWORD")
    pg_db = os.getenv("POSTGRES_DB")
    pg_port = os.getenv("POSTGRES_PORT", "5432")
    pg_host = os.getenv("POSTGRES_HOST", "localhost")

    if pg_user and pg_password and pg_db:
        return f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

    # 4. Default fallback for local development
    return "postgresql://appuser:dbuser123@localhost:5000/myapp"


DATABASE_URL = _build_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# PUBLIC_INTERFACE
def get_db():
    """
    Dependency that provides a SQLAlchemy database session.

    Yields a session and ensures it is closed after the request completes.
    Used as a FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
