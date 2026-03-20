"""
Database configuration and session management.

Provides SQLAlchemy engine and session factory for PostgreSQL connectivity.
Uses DATABASE_URL from environment or falls back to db_connection.txt from
the database container.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Read DATABASE_URL from env; fall back to known connection string
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://appuser:dbuser123@localhost:5000/myapp"
)

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
