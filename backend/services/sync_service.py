"""
Sync Service — scheduled multi-source document synchronisation.

Supports Google Drive, Confluence Cloud, and external S3 buckets.
Each source is represented by a SyncConfig row that stores encrypted credentials
and a schedule.  The APScheduler job calls run_due_syncs() every 5 minutes;
it picks up configs whose next_run_at has passed and runs each one.

Credentials are encrypted at rest with Fernet (symmetric AES-128-CBC + HMAC).
Set ENCRYPTION_KEY in .env to a value produced by:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import json
import os
import re
import requests
import boto3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from .models import SyncConfig, SyncTracker, SyncRun
from .upload_service import upload_service
from .google_drive_service import google_drive_service
from .confluence_service import confluence_service
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Schedule → timedelta mapping
# ---------------------------------------------------------------------------

_SCHEDULE_DELTAS: Dict[str, timedelta] = {
    '2m':     timedelta(minutes=2),
    '5m':     timedelta(minutes=5),
    'hourly': timedelta(hours=1),
    '6h':     timedelta(hours=6),
    '12h':    timedelta(hours=12),
    'daily':  timedelta(hours=24),
    'weekly': timedelta(days=7),
}


class SyncService:
    """CRUD + execution logic for scheduled source syncs."""

    # ------------------------------------------------------------------
    # Encryption helpers
    # ------------------------------------------------------------------

    def _get_fernet(self) -> Fernet:
        key = os.getenv('ENCRYPTION_KEY', settings.ENCRYPTION_KEY)
        if not key:
            raise RuntimeError(
                "ENCRYPTION_KEY is not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\""
            )
        return Fernet(key.encode())

    def encrypt_credentials(self, creds: dict) -> str:
        """Encrypt a credentials dict to a Fernet token string."""
        f = self._get_fernet()
        return f.encrypt(json.dumps(creds).encode()).decode()

    def decrypt_credentials(self, enc: str) -> dict:
        """Decrypt a Fernet token string back to a credentials dict."""
        f = self._get_fernet()
        return json.loads(f.decrypt(enc.encode()).decode())

    # ------------------------------------------------------------------
    # Schedule helpers
    # ------------------------------------------------------------------

    def _compute_next_run(self, schedule: str) -> datetime:
        delta = _SCHEDULE_DELTAS.get(schedule, timedelta(hours=24))
        return datetime.utcnow() + delta

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_config(
        self,
        db: Session,
        user_id: str,
        source_type: str,
        display_name: str,
        credentials: dict,
        schedule: str,
        space_or_path: Optional[str] = None,
    ) -> dict:
        """Create a new SyncConfig row and return it as a dict (no credentials)."""
        credentials_enc = self.encrypt_credentials(credentials)
        next_run_at = self._compute_next_run(schedule)

        config = SyncConfig(
            user_id=user_id,
            source_type=source_type,
            display_name=display_name,
            credentials_enc=credentials_enc,
            schedule=schedule,
            space_or_path=space_or_path,
            status='active',
            next_run_at=next_run_at,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        logger.info(f"Created sync config {config.id} for user {user_id} ({source_type})")
        return self._config_to_dict(config)

    def list_configs(self, db: Session, user_id: str) -> List[dict]:
        """Return all SyncConfigs for a user (credentials omitted)."""
        configs = (
            db.query(SyncConfig)
            .filter(SyncConfig.user_id == user_id)
            .order_by(SyncConfig.created_at.desc())
            .all()
        )
        return [self._config_to_dict(c) for c in configs]

    def get_config(self, db: Session, config_id: str, user_id: str) -> Optional[SyncConfig]:
        """Return the raw ORM object (or None) — caller decides what to expose."""
        return (
            db.query(SyncConfig)
            .filter(SyncConfig.id == config_id, SyncConfig.user_id == user_id)
            .first()
        )

    def update_config(self, db: Session, config_id: str, user_id: str, **kwargs) -> bool:
        """Update arbitrary fields on a SyncConfig. Re-encrypt credentials if provided."""
        config = self.get_config(db, config_id, user_id)
        if not config:
            return False

        if 'credentials' in kwargs:
            kwargs['credentials_enc'] = self.encrypt_credentials(kwargs.pop('credentials'))

        if 'schedule' in kwargs:
            kwargs['next_run_at'] = self._compute_next_run(kwargs['schedule'])

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        db.commit()
        return True

    def delete_config(self, db: Session, config_id: str, user_id: str) -> bool:
        """Delete a SyncConfig and its SyncTracker rows (cascade handles DB side)."""
        config = self.get_config(db, config_id, user_id)
        if not config:
            return False
        db.delete(config)
        db.commit()
        logger.info(f"Deleted sync config {config_id}")
        return True

    def pause_config(self, db: Session, config_id: str, user_id: str) -> bool:
        """Set a config to 'paused' so it is skipped by the scheduler."""
        config = self.get_config(db, config_id, user_id)
        if not config:
            return False
        config.status = 'paused'
        db.commit()
        return True

    def resume_config(self, db: Session, config_id: str, user_id: str) -> bool:
        """Resume a paused config and recompute next_run_at."""
        config = self.get_config(db, config_id, user_id)
        if not config:
            return False
        config.status = 'active'
        config.next_run_at = self._compute_next_run(config.schedule)
        db.commit()
        return True

    def get_due_configs(self, db: Session) -> List[SyncConfig]:
        """Return all active configs whose next_run_at has arrived."""
        return (
            db.query(SyncConfig)
            .filter(
                SyncConfig.status == 'active',
                SyncConfig.next_run_at <= datetime.utcnow(),
            )
            .all()
        )

    def get_tracker_history(
        self, db: Session, config_id: str, user_id: str, limit: int = 50
    ) -> List[dict]:
        """Return recent SyncTracker rows for a config (per-file)."""
        rows = (
            db.query(SyncTracker)
            .filter(SyncTracker.sync_config_id == config_id, SyncTracker.user_id == user_id)
            .order_by(SyncTracker.last_synced_at.desc())
            .limit(limit)
            .all()
        )
        return [self._tracker_to_dict(r) for r in rows]

    def get_run_history(
        self, db: Session, config_id: str, user_id: str, limit: int = 20
    ) -> List[dict]:
        """Return recent run-level history for a config."""
        rows = (
            db.query(SyncRun)
            .filter(SyncRun.sync_config_id == config_id, SyncRun.user_id == user_id)
            .order_by(SyncRun.started_at.desc())
            .limit(limit)
            .all()
        )
        return [self._run_to_dict(r) for r in rows]

    def _run_to_dict(self, run: SyncRun) -> dict:
        duration_s = None
        if run.started_at and run.completed_at:
            duration_s = round((run.completed_at - run.started_at).total_seconds(), 1)
        return {
            'id': run.id,
            'started_at': run.started_at.isoformat() if run.started_at else None,
            'completed_at': run.completed_at.isoformat() if run.completed_at else None,
            'status': run.status,
            'files_synced': run.files_synced or 0,
            'files_failed': run.files_failed or 0,
            'duration_s': duration_s,
            'error': run.error,
            'trigger': run.trigger or 'scheduler',
        }

    # ------------------------------------------------------------------
    # Tracker helpers
    # ------------------------------------------------------------------

    def _check_and_upsert_tracker(
        self,
        db: Session,
        config_id: str,
        user_id: str,
        source_file_id: str,
        fingerprint: str,
    ) -> bool:
        """
        Return True if the file is new or its fingerprint has changed (needs sync).
        Return False if it is already up-to-date.

        Upserts the row so the fingerprint is always current after a successful sync.
        """
        existing = (
            db.query(SyncTracker)
            .filter(
                SyncTracker.sync_config_id == config_id,
                SyncTracker.source_file_id == source_file_id,
            )
            .first()
        )
        if existing is None:
            # New file — insert placeholder so we can mark it synced/failed later
            tracker = SyncTracker(
                sync_config_id=config_id,
                user_id=user_id,
                source_file_id=source_file_id,
                fingerprint=fingerprint,
                status='synced',
                last_synced_at=datetime.utcnow(),
            )
            db.add(tracker)
            db.flush()
            return True
        if existing.fingerprint != fingerprint:
            # Changed fingerprint — mark for re-sync but keep row
            existing.fingerprint = fingerprint
            existing.status = 'synced'
            existing.last_synced_at = datetime.utcnow()
            db.flush()
            return True
        return False

    def mark_tracker_synced(
        self,
        db: Session,
        config_id: str,
        source_file_id: str,
        fingerprint: str,
        s3_key: str,
    ) -> None:
        """Update (or create) a tracker row as successfully synced."""
        existing = (
            db.query(SyncTracker)
            .filter(
                SyncTracker.sync_config_id == config_id,
                SyncTracker.source_file_id == source_file_id,
            )
            .first()
        )
        if existing:
            existing.fingerprint = fingerprint
            existing.s3_key = s3_key
            existing.status = 'synced'
            existing.last_synced_at = datetime.utcnow()
        else:
            tracker = SyncTracker(
                sync_config_id=config_id,
                user_id='',
                source_file_id=source_file_id,
                fingerprint=fingerprint,
                s3_key=s3_key,
                status='synced',
                last_synced_at=datetime.utcnow(),
            )
            db.add(tracker)
        db.flush()

    def mark_tracker_failed(
        self,
        db: Session,
        config_id: str,
        source_file_id: str,
        error: str,
    ) -> None:
        """Mark a tracker row as failed."""
        existing = (
            db.query(SyncTracker)
            .filter(
                SyncTracker.sync_config_id == config_id,
                SyncTracker.source_file_id == source_file_id,
            )
            .first()
        )
        if existing:
            existing.status = 'failed'
            existing.last_synced_at = datetime.utcnow()
            db.flush()

    def mark_config_done(
        self,
        db: Session,
        config: SyncConfig,
        files_synced: int,
        error: Optional[str] = None,
    ) -> None:
        """Record completion stats and schedule the next run."""
        config.last_run_at = datetime.utcnow()
        config.next_run_at = self._compute_next_run(config.schedule)
        config.files_synced = (config.files_synced or 0) + files_synced
        if error:
            config.status = 'error'
            config.last_error = error
        else:
            config.status = 'active'
            config.last_error = None
        db.commit()

    # ------------------------------------------------------------------
    # Per-source sync runners
    # ------------------------------------------------------------------

    def sync_gdrive(self, db: Session, config: SyncConfig) -> int:
        """
        Sync all files from a Google Drive (personal or Shared Drive).

        Credentials dict expected:
            {
                "access_token": "ya29...",
                "refresh_token": "1//...",   # optional, used to refresh if needed
            }

        Returns the number of files actually uploaded/updated.
        """
        creds = self.decrypt_credentials(config.credentials_enc)
        access_token = creds.get('access_token', '')
        refresh_token = creds.get('refresh_token')
        # space_or_path stores the folder_id selected by user
        # drive_id (shared drive) is stored in credentials
        folder_id = config.space_or_path or None
        drive_id = creds.get('drive_id') or None

        # Attempt to refresh token when a refresh_token is available
        if refresh_token and settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
            try:
                resp = requests.post(
                    'https://oauth2.googleapis.com/token',
                    data={
                        'client_id':     settings.GOOGLE_CLIENT_ID,
                        'client_secret': settings.GOOGLE_CLIENT_SECRET,
                        'refresh_token': refresh_token,
                        'grant_type':    'refresh_token',
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                token_data = resp.json()
                access_token = token_data.get('access_token', access_token)
                # Persist the refreshed token back to the config
                creds['access_token'] = access_token
                config.credentials_enc = self.encrypt_credentials(creds)
                db.flush()
                logger.info(f"[sync_gdrive] Refreshed access token for config {config.id}")
            except Exception as e:
                logger.warning(f"[sync_gdrive] Token refresh failed for config {config.id}: {e}")

        # List files in the specified folder (or whole drive if no folder set)
        files = google_drive_service.list_files(
            access_token=access_token,
            drive_id=drive_id,
            folder_id=folder_id,
            page_size=1000,
        )

        files_synced = 0
        for file in files:
            file_id = file['id']
            file_name = file.get('name', file_id)
            modified_time = file.get('modifiedTime', '')
            mime_type = file.get('mimeType', '')

            # Skip folders
            if mime_type == 'application/vnd.google-apps.folder':
                continue

            needs_sync = self._check_and_upsert_tracker(
                db, config.id, config.user_id, file_id, modified_time
            )
            if not needs_sync:
                continue

            try:
                file_content = google_drive_service.download_file(
                    file_id=file_id,
                    access_token=access_token,
                    drive_id=drive_id,
                )
                result = upload_service.upload_to_s3(
                    file_content=file_content,
                    file_name=file_name,
                    user_id=config.user_id,
                    metadata={
                        'source': 'gdrive',
                        'sync_config_id': config.id,
                        'gdrive_file_id': file_id,
                    },
                )
                self.mark_tracker_synced(
                    db, config.id, file_id, modified_time, result['s3_key']
                )
                files_synced += 1
                logger.info(
                    f"[sync_gdrive] Synced {file_name} → {result['s3_key']} "
                    f"(config {config.id})"
                )
            except Exception as e:
                logger.error(
                    f"[sync_gdrive] Failed to sync file {file_id} ({file_name}): {e}"
                )
                self.mark_tracker_failed(db, config.id, file_id, str(e))

        if files_synced > 0:
            try:
                upload_service.trigger_kb_sync()
            except Exception as e:
                logger.warning(f"[sync_gdrive] trigger_kb_sync failed: {e}")

        db.commit()
        return files_synced

    def sync_confluence(self, db: Session, config: SyncConfig) -> int:
        """
        Sync all pages in a Confluence space.

        Credentials dict expected:
            {
                "site_url":  "https://your-org.atlassian.net",
                "email":     "user@example.com",
                "api_token": "ATATT...",
            }

        space_or_path should be the Confluence space key (e.g. "HR").
        Returns the number of pages uploaded/updated.
        """
        creds = self.decrypt_credentials(config.credentials_enc)
        site_url = creds['site_url']
        email = creds['email']
        api_token = creds['api_token']
        space_key = config.space_or_path or ''

        if not space_key:
            raise ValueError(
                f"SyncConfig {config.id}: space_or_path must be set to a Confluence space key"
            )

        # Fetch pages with version info so we can fingerprint by version number
        pages_raw: List[Dict[str, Any]] = []
        start = 0
        limit = 50
        while True:
            data = confluence_service._get(
                site_url, email, api_token, '/content',
                {
                    'spaceKey': space_key,
                    'type': 'page',
                    'depth': 'all',
                    'start': start,
                    'limit': limit,
                    'expand': 'version',
                }
            )
            results = data.get('results', [])
            pages_raw.extend(results)
            if data.get('size', 0) < limit:
                break
            start += limit

        files_synced = 0
        for page in pages_raw:
            page_id = page['id']
            page_title = page.get('title', page_id)
            version_number = str(page.get('version', {}).get('number', '0'))

            needs_sync = self._check_and_upsert_tracker(
                db, config.id, config.user_id, page_id, version_number
            )
            if not needs_sync:
                continue

            try:
                file_content, file_name = confluence_service.download_page_as_html(
                    site_url=site_url,
                    email=email,
                    api_token=api_token,
                    page_id=page_id,
                    page_title=page_title,
                )
                result = upload_service.upload_to_s3(
                    file_content=file_content,
                    file_name=file_name,
                    user_id=config.user_id,
                    metadata={
                        'source': 'confluence',
                        'sync_config_id': config.id,
                        'confluence_page_id': page_id,
                        'space_key': space_key,
                    },
                )
                self.mark_tracker_synced(
                    db, config.id, page_id, version_number, result['s3_key']
                )
                files_synced += 1
                logger.info(
                    f"[sync_confluence] Synced page '{page_title}' → {result['s3_key']} "
                    f"(config {config.id})"
                )
            except Exception as e:
                logger.error(
                    f"[sync_confluence] Failed to sync page {page_id} ({page_title}): {e}"
                )
                self.mark_tracker_failed(db, config.id, page_id, str(e))

        if files_synced > 0:
            try:
                upload_service.trigger_kb_sync()
            except Exception as e:
                logger.warning(f"[sync_confluence] trigger_kb_sync failed: {e}")

        db.commit()
        return files_synced

    def sync_s3(self, db: Session, config: SyncConfig) -> int:
        """
        Sync objects from a source S3 bucket into the application S3 bucket.

        Credentials dict expected:
            {
                "source_bucket":          "company-docs",
                "aws_access_key_id":      "AKIA...",
                "aws_secret_access_key":  "...",
                "aws_region":             "us-east-1",
            }

        space_or_path is used as the object prefix to list (e.g. "hr-policies/").
        Returns the number of objects synced.
        """
        creds = self.decrypt_credentials(config.credentials_enc)
        # Support both 'bucket' (new UI) and 'source_bucket' (old UI)
        source_bucket = creds.get('bucket') or creds['source_bucket']
        aws_access_key_id = creds['aws_access_key_id']
        aws_secret_access_key = creds['aws_secret_access_key']
        aws_region = creds.get('aws_region', settings.AWS_REGION)
        prefix = config.space_or_path or ''

        source_s3 = boto3.client(
            's3',
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=creds.get('aws_session_token') or None,
        )

        paginator = source_s3.get_paginator('list_objects_v2')
        files_synced = 0

        for page in paginator.paginate(Bucket=source_bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                source_key = obj['Key']
                # Skip "folder" placeholders
                if source_key.endswith('/'):
                    continue

                etag = obj.get('ETag', '').strip('"')
                needs_sync = self._check_and_upsert_tracker(
                    db, config.id, config.user_id, source_key, etag
                )
                if not needs_sync:
                    continue

                try:
                    response = source_s3.get_object(Bucket=source_bucket, Key=source_key)
                    file_content = response['Body'].read()

                    # Use just the filename component as the destination file name
                    file_name = source_key.split('/')[-1]

                    result = upload_service.upload_to_s3(
                        file_content=file_content,
                        file_name=file_name,
                        user_id=config.user_id,
                        metadata={
                            'source': 's3',
                            'sync_config_id': config.id,
                            'source_bucket': source_bucket,
                            'source_key': source_key,
                        },
                    )
                    self.mark_tracker_synced(
                        db, config.id, source_key, etag, result['s3_key']
                    )
                    files_synced += 1
                    logger.info(
                        f"[sync_s3] Synced s3://{source_bucket}/{source_key} → "
                        f"{result['s3_key']} (config {config.id})"
                    )
                except Exception as e:
                    logger.error(
                        f"[sync_s3] Failed to sync {source_key}: {e}"
                    )
                    self.mark_tracker_failed(db, config.id, source_key, str(e))

        if files_synced > 0:
            try:
                upload_service.trigger_kb_sync()
            except Exception as e:
                logger.warning(f"[sync_s3] trigger_kb_sync failed: {e}")

        db.commit()
        return files_synced

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def run_sync(self, db: Session, config: SyncConfig, trigger: str = 'scheduler') -> None:
        """Dispatch to the correct per-source runner and record completion."""
        logger.info(f"[run_sync] Starting sync for config {config.id} ({config.source_type}, user {config.user_id})")

        # Create a run record
        run = SyncRun(
            sync_config_id=config.id,
            user_id=config.user_id,
            started_at=datetime.utcnow(),
            status='running',
            trigger=trigger,
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        files_synced = 0
        error_msg = None
        try:
            if config.source_type == 'gdrive':
                files_synced = self.sync_gdrive(db, config)
            elif config.source_type == 'confluence':
                files_synced = self.sync_confluence(db, config)
            elif config.source_type == 's3':
                files_synced = self.sync_s3(db, config)
            else:
                raise ValueError(f"Unknown source_type: {config.source_type!r}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[run_sync] Sync failed for config {config.id}: {e}")
        finally:
            # Update run record
            run.completed_at = datetime.utcnow()
            run.status = 'failed' if error_msg else 'success'
            run.files_synced = files_synced
            run.error = error_msg
            db.commit()
            self.mark_config_done(db, config, files_synced, error=error_msg)

        logger.info(f"[run_sync] Finished config {config.id} — files_synced={files_synced}, error={error_msg}")

    def run_due_syncs(self, db: Session) -> None:
        """Find all due configs and run them sequentially."""
        due = self.get_due_configs(db)
        if not due:
            logger.debug("[run_due_syncs] No configs due for sync")
            return
        logger.info(f"[run_due_syncs] {len(due)} config(s) due for sync")
        for config in due:
            try:
                self.run_sync(db, config)
            except Exception as e:
                logger.error(
                    f"[run_due_syncs] Unexpected error for config {config.id}: {e}"
                )

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def _config_to_dict(self, config: SyncConfig) -> dict:
        return {
            'id':            config.id,
            'user_id':       config.user_id,
            'source_type':   config.source_type,
            'display_name':  config.display_name,
            'schedule':      config.schedule,
            'space_or_path': config.space_or_path,
            'status':        config.status,
            'last_run_at':   config.last_run_at.isoformat() if config.last_run_at else None,
            'last_error':    config.last_error,
            'next_run_at':   config.next_run_at.isoformat() if config.next_run_at else None,
            'files_synced':  config.files_synced,
            'created_at':    config.created_at.isoformat() if config.created_at else None,
        }

    def _tracker_to_dict(self, tracker: SyncTracker) -> dict:
        return {
            'id':             tracker.id,
            'sync_config_id': tracker.sync_config_id,
            'user_id':        tracker.user_id,
            'source_file_id': tracker.source_file_id,
            'fingerprint':    tracker.fingerprint,
            's3_key':         tracker.s3_key,
            'status':         tracker.status,
            'last_synced_at': tracker.last_synced_at.isoformat() if tracker.last_synced_at else None,
        }


# Singleton instance
sync_service = SyncService()
