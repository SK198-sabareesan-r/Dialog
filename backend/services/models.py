"""
SQLAlchemy models for chat sessions and scheduled sync configuration.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="New conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True)
    language = Column(JSON, nullable=True)
    duration_ms = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class SyncConfig(Base):
    __tablename__ = "sync_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=False, index=True)
    source_type = Column(String(20), nullable=False)
    display_name = Column(String(255))
    credentials_enc = Column(Text, nullable=False)
    schedule = Column(String(20), nullable=False, default='daily')
    space_or_path = Column(String(500), nullable=True)
    status = Column(String(20), default='active')
    last_run_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    files_synced = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    trackers = relationship("SyncTracker", back_populates="config", cascade="all, delete-orphan")
    runs = relationship("SyncRun", back_populates="config", cascade="all, delete-orphan")


class SyncRun(Base):
    """One record per sync execution — run-level history."""
    __tablename__ = "sync_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sync_config_id = Column(String(36), ForeignKey("sync_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default='running')  # 'running'|'success'|'partial'|'failed'|'skipped'
    files_found = Column(Integer, default=0)
    files_synced = Column(Integer, default=0)
    files_skipped = Column(Integer, default=0)
    files_failed = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    trigger = Column(String(20), default='scheduler')  # 'scheduler'|'manual'

    config = relationship("SyncConfig", back_populates="runs")


class SyncTracker(Base):
    __tablename__ = "sync_tracker"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sync_config_id = Column(
        String(36), ForeignKey("sync_configs.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(String(255), index=True)
    source_file_id = Column(String(500), nullable=False)  # gdrive file.id / confluence page.id / s3 key
    fingerprint = Column(String(255), nullable=False)  # modifiedTime / version.number / ETag
    s3_key = Column(String(500), nullable=True)
    status = Column(String(20), default='synced')  # 'synced'|'failed'|'deleted'
    last_synced_at = Column(DateTime, default=datetime.utcnow)

    config = relationship("SyncConfig", back_populates="trackers")

    __table_args__ = (
        UniqueConstraint('sync_config_id', 'source_file_id', name='uq_sync_tracker_config_file'),
    )
