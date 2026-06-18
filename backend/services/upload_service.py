"""
Upload Service - Handles file uploads to S3 and KB sync.

Flow (non-blocking):
  1. upload_to_s3()       — stores file in S3, records in tracker, returns immediately
  2. background_sync()    — called by FastAPI BackgroundTasks AFTER response is sent
                            triggers KB ingestion job and polls to completion

Structured JSON log events emitted:
  document_uploaded_to_s3   : file stored, size, etag, upload duration
  kb_sync_triggered         : job ID, KB/DS IDs, trigger duration
  kb_sync_polling_started   : polling config
  kb_sync_in_progress       : heartbeat every poll cycle
  kb_sync_completed         : final status, statistics, total sync duration
  kb_sync_trigger_failed    : warning — file is in S3, next scheduled sync will pick it up
  upload_failed             : error on S3 put
"""

import json
import time
import boto3
from datetime import datetime
from typing import Dict, Any, Optional

from config import settings
from utils.logger import get_logger
from .ingestion_tracker import ingestion_tracker

logger = get_logger(__name__)


class UploadService:
    """Handles file uploads to S3 and Bedrock KB synchronisation."""

    def __init__(self):
        aws_credentials = {
            'region_name':           settings.AWS_REGION,
            'aws_access_key_id':     settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        }
        if settings.AWS_SESSION_TOKEN:
            aws_credentials['aws_session_token'] = settings.AWS_SESSION_TOKEN

        self.s3_client            = boto3.client('s3',            **aws_credentials)
        self.bedrock_agent_client = boto3.client('bedrock-agent', **aws_credentials)
        self.bucket         = settings.S3_RAW_BUCKET
        self.kb_id          = settings.BEDROCK_KB_ID
        self.data_source_id = settings.BEDROCK_DATA_SOURCE_ID

    # ------------------------------------------------------------------
    # Step 1 — Store file in S3 (called in the request thread)
    # Returns immediately; does NOT trigger or poll KB sync.
    # ------------------------------------------------------------------

    def upload_to_s3(
        self,
        file_content: bytes,
        file_name: str,
        user_id: str,
        metadata: Dict[str, Any],
        bedrock_metadata: Optional[Dict[str, Any]] = None,
        s3_key_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Store file in S3 with metadata and record it in the ingestion tracker.
        Also writes a companion .metadata.json file for Bedrock KB filtering.

        Returns as soon as the S3 PUT completes — KB sync is NOT started here.
        The caller is responsible for scheduling background_sync().

        Args:
            bedrock_metadata: If provided, written as the Bedrock KB .metadata.json
                              file alongside the document. Must follow the format:
                              {"metadataAttributes": {"key": "value", ...}}
            s3_key_override:  If provided, use this as the S3 key instead of the default.
                              Used by sync engine for deterministic keys.
        """
        # Use override if provided, otherwise default pattern
        s3_key = s3_key_override or f"docs/{file_name}"

        # Sanitise metadata values → ASCII strings (S3 header requirement)
        string_metadata: Dict[str, str] = {}
        for k, v in metadata.items():
            raw = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            string_metadata[k] = raw.encode('ascii', errors='replace').decode('ascii')

        try:
            t0 = time.time()
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_content,
                Metadata=string_metadata,
            )
            upload_ms = round((time.time() - t0) * 1000, 2)

            # Write Bedrock KB .metadata.json companion file
            if bedrock_metadata:
                metadata_key = f"{s3_key}.metadata.json"
                self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=metadata_key,
                    Body=json.dumps(bedrock_metadata, ensure_ascii=False).encode("utf-8"),
                    ContentType="application/json",
                )
                logger.info(json.dumps({
                    "event":        "metadata_json_written",
                    "metadata_key": metadata_key,
                    "attributes":   list(bedrock_metadata.get("metadataAttributes", {}).keys()),
                }))

            head = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            etag = head["ETag"].strip('"')

            logger.info(json.dumps({
                "event":       "document_uploaded_to_s3",
                "filename":    file_name,
                "s3_uri":      f"s3://{self.bucket}/{s3_key}",
                "s3_key":      s3_key,
                "bucket":      self.bucket,
                "size_bytes":  len(file_content),
                "etag":        etag,
                "user_id":     user_id,
                "duration_ms": upload_ms,
            }))

            # Record in tracker immediately so the scheduled sync
            # doesn't double-ingest while the background task runs
            ingestion_tracker.record_ingested(s3_key, etag)

            return {
                's3_key':  s3_key,
                's3_uri':  f"s3://{self.bucket}/{s3_key}",
                'etag':    etag,
                'metadata': string_metadata,
            }

        except Exception as e:
            logger.error(json.dumps({
                "event":    "upload_failed",
                "filename": file_name,
                "s3_key":   s3_key,
                "error":    str(e),
            }))
            raise

    # ------------------------------------------------------------------
    # Step 2 — Trigger KB sync and poll to completion (background task)
    # Called by FastAPI BackgroundTasks AFTER the HTTP 202 is sent.
    # ------------------------------------------------------------------

    def background_sync(self, s3_key: str, filename: str, etag: str) -> None:
        """
        Trigger a Bedrock KB ingestion job for the uploaded file and
        poll until it reaches a terminal state (COMPLETE / FAILED).

        This runs in a background thread — the HTTP response has already
        been sent to the client before this executes.

        Args:
            s3_key: S3 key of the uploaded file
            filename: Original filename
            etag: ETag of the uploaded file (for duplicate detection)
        """
        try:
            # Check if this exact version already ingested (ETag comparison)
            if ingestion_tracker.is_already_ingested(s3_key, etag):
                logger.info(json.dumps({
                    "event": "kb_sync_skipped_duplicate",
                    "filename": filename,
                    "s3_key": s3_key,
                    "etag": etag,
                    "reason": "File with same ETag already ingested - no changes detected",
                }))
                return  # Skip KB sync - file unchanged

            # File is new or changed - proceed with KB sync
            t1 = time.time()
            sync_result = self.trigger_kb_sync()
            trigger_ms  = round((time.time() - t1) * 1000, 2)

            logger.info(json.dumps({
                "event":               "kb_sync_triggered",
                "filename":            filename,
                "s3_key":              s3_key,
                "kb_id":               self.kb_id,
                "data_source_id":      self.data_source_id,
                "ingestion_job_id":    sync_result['ingestion_job_id'],
                "initial_job_status":  sync_result['status'],
                "trigger_duration_ms": trigger_ms,
            }))

            self._poll_sync_completion(
                ingestion_job_id=sync_result['ingestion_job_id'],
                filename=filename,
            )

        except Exception as e:
            logger.warning(json.dumps({
                "event":    "kb_sync_trigger_failed",
                "filename": filename,
                "s3_key":   s3_key,
                "error":    str(e),
                "note":     "File is safely in S3 — next scheduled sync will pick it up",
            }))

    # ------------------------------------------------------------------
    # Polling (used by background_sync and manual /api/kb/sync)
    # ------------------------------------------------------------------

    def _poll_sync_completion(
        self,
        ingestion_job_id: str,
        filename: str,
        poll_interval_s: int = 10,
        max_wait_s: int = 1800,  # 30 min — large videos can take a while
    ) -> Dict[str, Any]:
        """
        Poll get_ingestion_job until COMPLETE / FAILED / STOPPED.
        Logs a heartbeat every poll cycle and a JSON summary on completion.
        """
        t_start = time.time()

        logger.info(json.dumps({
            "event":            "kb_sync_polling_started",
            "ingestion_job_id": ingestion_job_id,
            "filename":         filename,
            "poll_interval_s":  poll_interval_s,
            "max_wait_s":       max_wait_s,
        }))

        while True:
            elapsed = time.time() - t_start

            if elapsed > max_wait_s:
                logger.warning(json.dumps({
                    "event":            "kb_sync_poll_timeout",
                    "ingestion_job_id": ingestion_job_id,
                    "filename":         filename,
                    "elapsed_s":        round(elapsed, 1),
                }))
                return {}

            status     = self.get_sync_status(ingestion_job_id)
            job_status = status['status']

            if job_status in ('COMPLETE', 'FAILED', 'STOPPED'):
                total_s = round(time.time() - t_start, 2)
                stats   = status.get('statistics', {})

                payload = {
                    "event":                      "kb_sync_completed",
                    "ingestion_job_id":           ingestion_job_id,
                    "filename":                   filename,
                    "status":                     job_status,
                    "total_sync_duration_s":      total_s,
                    "documents_scanned":          stats.get('numberOfDocumentsScanned', 0),
                    "new_documents_indexed":      stats.get('numberOfNewDocumentsIndexed', 0),
                    "modified_documents_indexed": stats.get('numberOfModifiedDocumentsIndexed', 0),
                    "documents_failed":           stats.get('numberOfDocumentsFailed', 0),
                    "documents_deleted":          stats.get('numberOfDocumentsDeleted', 0),
                    "started_at":                 str(status.get('started_at', '')),
                    "completed_at":               str(status.get('completed_at', '')),
                }
                if status.get('failure_reasons'):
                    payload['failure_reasons'] = status['failure_reasons']

                if job_status == 'COMPLETE':
                    logger.info(json.dumps(payload))
                else:
                    logger.error(json.dumps(payload))

                return status

            # Heartbeat while still in progress
            logger.info(json.dumps({
                "event":            "kb_sync_in_progress",
                "ingestion_job_id": ingestion_job_id,
                "filename":         filename,
                "status":           job_status,
                "elapsed_s":        round(elapsed, 1),
            }))
            time.sleep(poll_interval_s)

    # ------------------------------------------------------------------
    # KB sync helpers
    # ------------------------------------------------------------------

    def trigger_kb_sync(self, force: bool = False) -> Dict[str, Any]:
        """Start a Bedrock KB ingestion job and return job details."""
        try:
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                description=f"Sync triggered at {datetime.utcnow().isoformat()}",
            )
            job = response['ingestionJob']
            logger.info(f"Started KB ingestion job: {job['ingestionJobId']}")
            return {
                'ingestion_job_id': job['ingestionJobId'],
                'status':          job['status'],
                'kb_id':           self.kb_id,
                'data_source_id':  self.data_source_id,
                'started_at':      job.get('startedAt', datetime.utcnow()).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to trigger KB sync: {e}")
            raise

    def get_sync_status(self, ingestion_job_id: str) -> Dict[str, Any]:
        """Fetch the current status of a KB ingestion job."""
        try:
            response = self.bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                ingestionJobId=ingestion_job_id,
            )
            job = response['ingestionJob']
            return {
                'ingestion_job_id': ingestion_job_id,
                'status':           job['status'],
                'started_at':       job.get('startedAt'),
                'completed_at':     job.get('completedAt'),
                'updated_at':       job.get('updatedAt'),
                'statistics':       job.get('statistics', {}),
                'failure_reasons':  job.get('failureReasons', []),
            }
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            raise

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_file_metadata(self, s3_key: str) -> Dict[str, Any]:
        """Get S3 object metadata for a stored file."""
        try:
            r = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            return {
                'metadata':       r.get('Metadata', {}),
                'content_type':   r.get('ContentType'),
                'content_length': r.get('ContentLength'),
                'last_modified':  r.get('LastModified').isoformat() if r.get('LastModified') else None,
                'etag':           r.get('ETag'),
            }
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise


# Singleton instance
upload_service = UploadService()
