"""
Database Service — SQLAlchemy setup for PostgreSQL (RDS)
"""

from sqlalchemy import create_engine, Column, String, Boolean, Integer, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from contextlib import contextmanager
import uuid

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Engine & Session ──────────────────────────────────────────────────────────
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Auto-reconnect stale connections
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """
    Database session generator.

    Works as both:
    - FastAPI dependency: db = Depends(get_db)
    - Context manager: with get_db_context() as db:
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager wrapper for use outside FastAPI (services, scripts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Models ────────────────────────────────────────────────────────────────────

class SyncSource(Base):
    __tablename__ = "sync_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # 's3', 'google_drive', 'confluence'
    name = Column(String(255), nullable=False)
    credentials = Column(Text, nullable=False)  # Encrypted JSON
    target_path = Column(String(500))  # folder_id, prefix, or space_key
    schedule_cron = Column(String(100), nullable=False, default="0 */6 * * *")
    enabled = Column(Boolean, default=True)
    last_sync_at = Column(DateTime)
    last_sync_files = Column(Integer, default=0)
    last_sync_status = Column(String(50))
    last_sync_error = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": self.user_id,
            "source_type": self.source_type,
            "name": self.name,
            "target_path": self.target_path,
            "schedule_cron": self.schedule_cron,
            "enabled": self.enabled,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_files": self.last_sync_files,
            "last_sync_status": self.last_sync_status,
            "last_sync_error": self.last_sync_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SyncHistory(Base):
    __tablename__ = "sync_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime)
    status = Column(String(50))  # 'running', 'success', 'partial', 'failed'
    files_found = Column(Integer, default=0)
    files_synced = Column(Integer, default=0)
    files_skipped = Column(Integer, default=0)
    files_failed = Column(Integer, default=0)
    error = Column(Text)
    details = Column(JSON)

    def to_dict(self):
        return {
            "id": str(self.id),
            "source_id": str(self.source_id),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "files_found": self.files_found,
            "files_synced": self.files_synced,
            "files_skipped": self.files_skipped,
            "files_failed": self.files_failed,
            "error": self.error,
        }


# ── Create tables on import ───────────────────────────────────────────────────
def init_db():
    """Create all tables if they don't exist."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
