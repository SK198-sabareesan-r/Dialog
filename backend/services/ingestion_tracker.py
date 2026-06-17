"""
Ingestion Tracker Service - Tracks which files have been ingested into Bedrock KB.

Uses an S3 JSON file as the state store.
Location: s3://<bucket>/.ingestion_tracker/state.json

Each entry records the S3 key, ETag, ingestion timestamp, and status.
This allows incremental ingestion — only new or changed files are processed.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

TRACKER_KEY = ".ingestion_tracker/state.json"


class IngestionTracker:
    """
    Tracks ingestion state using a JSON file stored in S3.

    The state file maps s3_key → { etag, ingested_at, status }
    """

    def __init__(self):
        aws_credentials = {
            "region_name": settings.AWS_REGION,
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        }
        if settings.AWS_SESSION_TOKEN:
            aws_credentials["aws_session_token"] = settings.AWS_SESSION_TOKEN

        self.s3_client = boto3.client("s3", **aws_credentials)
        self.bucket = settings.S3_RAW_BUCKET

    # ------------------------------------------------------------------
    # State file read / write
    # ------------------------------------------------------------------

    def _load_state(self) -> Dict[str, Any]:
        """Load the tracker state from S3. Returns empty dict if not found."""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket, Key=TRACKER_KEY
            )
            state = json.loads(response["Body"].read().decode("utf-8"))
            logger.debug(f"Loaded ingestion tracker: {len(state)} records")
            return state
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                logger.info("Ingestion tracker state file not found — starting fresh")
                return {}
            logger.error(f"Failed to load tracker state: {str(e)}")
            raise

    def _save_state(self, state: Dict[str, Any]) -> None:
        """Persist the tracker state back to S3."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=TRACKER_KEY,
                Body=json.dumps(state, indent=2).encode("utf-8"),
                ContentType="application/json",
            )
            logger.debug(f"Saved ingestion tracker: {len(state)} records")
        except Exception as e:
            logger.error(f"Failed to save tracker state: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_ingested(self, s3_key: str, etag: str) -> None:
        """
        Mark a file as successfully ingested.
        Called after upload so we know this file is in the tracker.
        """
        state = self._load_state()
        state[s3_key] = {
            "etag": etag,
            "ingested_at": datetime.utcnow().isoformat(),
            "status": "ingested",
        }
        self._save_state(state)
        logger.info(f"Recorded ingestion: {s3_key}")

    def mark_failed(self, s3_key: str, etag: str, error: str) -> None:
        """Mark a file as failed so it will be retried next cycle."""
        state = self._load_state()
        state[s3_key] = {
            "etag": etag,
            "ingested_at": datetime.utcnow().isoformat(),
            "status": "failed",
            "error": error,
        }
        self._save_state(state)
        logger.warning(f"Marked as failed: {s3_key} — {error}")

    def is_already_ingested(self, s3_key: str, current_etag: str) -> bool:
        """
        Return True if this exact version of the file is already ingested.
        Returns False if:
          - file is not in the tracker (new file)
          - file ETag has changed (file was updated)
          - file previously failed
        """
        state = self._load_state()
        record = state.get(s3_key)

        if record is None:
            return False  # New file

        if record.get("status") == "failed":
            return False  # Retry failed files

        if record.get("etag") != current_etag:
            return False  # File changed

        return True  # Already ingested, same version

    def get_new_or_changed_files(self) -> list:
        """
        Scan the entire S3 bucket and return files that are
        new or changed compared to the tracker state.

        Returns list of dicts: [{ s3_key, etag, size, last_modified }]
        """
        state = self._load_state()
        new_or_changed = []

        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket)

            for page in pages:
                for obj in page.get("Contents", []):
                    key = obj["Key"]

                    # Skip the tracker file itself
                    if key.startswith(".ingestion_tracker/"):
                        continue

                    etag = obj["ETag"].strip('"')  # AWS wraps ETags in quotes
                    record = state.get(key)

                    is_new = record is None
                    is_changed = record and record.get("etag") != etag
                    is_failed = record and record.get("status") == "failed"

                    if is_new or is_changed or is_failed:
                        new_or_changed.append({
                            "s3_key": key,
                            "etag": etag,
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                            "reason": "new" if is_new else ("changed" if is_changed else "retry_failed"),
                        })

            logger.info(
                f"Incremental scan complete: {len(new_or_changed)} new/changed files "
                f"out of total bucket objects"
            )
            return new_or_changed

        except Exception as e:
            logger.error(f"Failed to scan bucket for changes: {str(e)}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Return summary statistics of the tracker state."""
        state = self._load_state()

        ingested = sum(1 for r in state.values() if r.get("status") == "ingested")
        failed = sum(1 for r in state.values() if r.get("status") == "failed")

        return {
            "total_tracked": len(state),
            "ingested": ingested,
            "failed": failed,
        }


# Singleton instance
ingestion_tracker = IngestionTracker()
