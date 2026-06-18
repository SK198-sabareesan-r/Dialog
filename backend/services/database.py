"""
Database connection — PostgreSQL RDS via SQLAlchemy.

Set DATABASE_URL in .env:
  DATABASE_URL=postgresql://user:password@host:5432/dbname
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

DATABASE_URL = settings.DATABASE_URL

ssl_cert_path = Path(__file__).parent.parent / 'global-bundle.pem'

connect_args = {}
if ssl_cert_path.exists():
    connect_args = {
        "sslmode": "verify-full",
        "sslrootcert": str(ssl_cert_path),
    }

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
