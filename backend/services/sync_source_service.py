"""
Sync Source Service — CRUD operations for sync source configurations
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from services.database import get_db_context, SyncSource, SyncHistory
from services.encryption import encrypt_credentials, decrypt_credentials
from utils.logger import get_logger

logger = get_logger(__name__)


class SyncSourceService:
    """Manages sync source configurations stored in PostgreSQL."""

    def create(
        self,
        user_id: str,
        source_type: str,
        name: str,
        credentials: dict,
        target_path: str,
        schedule_cron: str = "0 */6 * * *",
    ) -> dict:
        """Create a new sync source."""
        encrypted_creds = encrypt_credentials(credentials)

        with get_db_context() as db:
            source = SyncSource(
                user_id=user_id,
                source_type=source_type,
                name=name,
                credentials=encrypted_creds,
                target_path=target_path,
                schedule_cron=schedule_cron,
                enabled=True,
            )
            db.add(source)
            db.flush()
            result = source.to_dict()

        logger.info(f"Created sync source: {name} ({source_type}) for {user_id}")
        return result

    def list_for_user(self, user_id: str) -> List[dict]:
        """List all sync sources for a given user."""
        with get_db_context() as db:
            sources = (
                db.query(SyncSource)
                .filter(SyncSource.user_id == user_id)
                .order_by(SyncSource.created_at.desc())
                .all()
            )
            return [s.to_dict() for s in sources]

    def get(self, source_id: str) -> Optional[dict]:
        """Get a single sync source by ID."""
        with get_db_context() as db:
            source = db.query(SyncSource).filter(SyncSource.id == source_id).first()
            return source.to_dict() if source else None

    def get_with_credentials(self, source_id: str) -> Optional[dict]:
        """Get a sync source with decrypted credentials (for sync engine use)."""
        with get_db_context() as db:
            source = db.query(SyncSource).filter(SyncSource.id == source_id).first()
            if not source:
                return None
            result = source.to_dict()
            result["credentials"] = decrypt_credentials(source.credentials)
            return result

    def update(self, source_id: str, **kwargs) -> Optional[dict]:
        """Update a sync source. Pass only fields to update."""
        with get_db_context() as db:
            source = db.query(SyncSource).filter(SyncSource.id == source_id).first()
            if not source:
                return None

            # Handle credentials separately (needs encryption)
            if "credentials" in kwargs:
                kwargs["credentials"] = encrypt_credentials(kwargs["credentials"])

            for key, value in kwargs.items():
                if hasattr(source, key):
                    setattr(source, key, value)

            source.updated_at = datetime.utcnow()
            db.flush()
            result = source.to_dict()

        logger.info(f"Updated sync source: {source_id}")
        return result

    def delete(self, source_id: str) -> bool:
        """Delete a sync source and its history."""
        with get_db_context() as db:
            source = db.query(SyncSource).filter(SyncSource.id == source_id).first()
            if not source:
                return False
            db.delete(source)

        logger.info(f"Deleted sync source: {source_id}")
        return True

    def toggle_enabled(self, source_id: str, enabled: bool) -> Optional[dict]:
        """Enable or disable a sync source."""
        return self.update(source_id, enabled=enabled)

    def get_all_enabled(self) -> List[dict]:
        """Get all enabled sync sources (for scheduler startup)."""
        with get_db_context() as db:
            sources = (
                db.query(SyncSource)
                .filter(SyncSource.enabled == True)
                .all()
            )
            results = []
            for s in sources:
                d = s.to_dict()
                d["credentials"] = decrypt_credentials(s.credentials)
                results.append(d)
            return results

    def update_sync_status(
        self,
        source_id: str,
        status: str,
        files_synced: int = 0,
        error: Optional[str] = None,
    ):
        """Update last sync status after a sync run."""
        with get_db_context() as db:
            source = db.query(SyncSource).filter(SyncSource.id == source_id).first()
            if source:
                source.last_sync_at = datetime.utcnow()
                source.last_sync_status = status
                source.last_sync_files = files_synced
                source.last_sync_error = error

    # ── Sync History ──────────────────────────────────────────────────────

    def create_history(self, source_id: str) -> str:
        """Create a new sync history record (status=running). Returns history ID."""
        with get_db_context() as db:
            history = SyncHistory(
                source_id=source_id,
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(history)
            db.flush()
            return str(history.id)

    def complete_history(
        self,
        history_id: str,
        status: str,
        files_found: int = 0,
        files_synced: int = 0,
        files_skipped: int = 0,
        files_failed: int = 0,
        error: Optional[str] = None,
    ):
        """Mark a sync history record as complete."""
        with get_db_context() as db:
            history = db.query(SyncHistory).filter(SyncHistory.id == history_id).first()
            if history:
                history.completed_at = datetime.utcnow()
                history.status = status
                history.files_found = files_found
                history.files_synced = files_synced
                history.files_skipped = files_skipped
                history.files_failed = files_failed
                history.error = error

    def get_history(self, source_id: str, limit: int = 20) -> List[dict]:
        """Get recent sync history for a source."""
        with get_db_context() as db:
            records = (
                db.query(SyncHistory)
                .filter(SyncHistory.source_id == source_id)
                .order_by(SyncHistory.started_at.desc())
                .limit(limit)
                .all()
            )
            return [r.to_dict() for r in records]


# Singleton
sync_source_service = SyncSourceService()
