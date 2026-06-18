"""
Sync Engine — Orchestrates scheduled sync from external sources to centralized S3.

Flow:
1. Load sync source config (with decrypted credentials)
2. Instantiate the right connector (S3 / Drive / Confluence)
3. List new/modified files since last sync
4. For each file: download → extract metadata → upload to centralized S3
5. Trigger Bedrock KB ingestion if any new files
6. Update sync status in DB
"""

from datetime import datetime
from typing import Optional

from services.sync_source_service import sync_source_service
from services.connectors import get_connector
from services.upload_service import upload_service
from services.metadata_extractor import metadata_extractor
from services.ingestion_tracker import ingestion_tracker
from utils.logger import get_logger

logger = get_logger(__name__)


async def run_sync(source_id: str) -> dict:
    """
    Execute a full sync run for a given source.

    Returns summary dict with counts and status.
    """
    # 1. Load source config
    source = sync_source_service.get_with_credentials(source_id)
    if not source:
        logger.error(f"Sync source {source_id} not found")
        return {"status": "failed", "error": "Source not found"}

    if not source.get("enabled"):
        logger.info(f"Sync source {source_id} is disabled — skipping")
        return {"status": "skipped", "reason": "disabled"}

    source_type = source["source_type"]
    credentials = source["credentials"]
    target_path = source.get("target_path", "")
    user_id = source["user_id"]
    since = datetime.fromisoformat(source["last_sync_at"]) if source.get("last_sync_at") else None

    # 2. Create history record
    history_id = sync_source_service.create_history(source_id)

    logger.info(f"Starting sync: {source['name']} ({source_type}) for {user_id}")

    try:
        # 3. Get connector
        connector = get_connector(source_type)

        # 4. List files
        files = connector.list_files(credentials, target_path, since=since)
        files_found = len(files)

        if files_found == 0:
            logger.info(f"Sync {source['name']}: no new/modified files")
            sync_source_service.complete_history(
                history_id, status="success",
                files_found=0, files_synced=0, files_skipped=0,
            )
            sync_source_service.update_sync_status(source_id, "success", files_synced=0)
            return {"status": "success", "files_found": 0, "files_synced": 0}

        logger.info(f"Sync {source['name']}: found {files_found} files to process")

        # 5. Process each file
        files_synced = 0
        files_skipped = 0
        files_failed = 0
        errors = []

        for file_info in files:
            try:
                # Deterministic S3 key
                s3_key = connector.get_deterministic_key(user_id, file_info)

                # Check if already ingested (ETag dedup)
                # For Drive/Confluence we use modified time as pseudo-etag
                etag_or_hash = file_info.get("etag", file_info.get("modified", ""))
                if ingestion_tracker.is_already_ingested(s3_key, etag_or_hash):
                    files_skipped += 1
                    continue

                # Download
                content = connector.download_file(credentials, file_info["id"])

                # Extract metadata
                filename = file_info["name"]
                content_type = _guess_content_type(filename)
                extracted_metadata = metadata_extractor.extract_metadata(
                    file_content=content,
                    filename=filename,
                    content_type=content_type,
                )

                # Build metadata
                custom_metadata = {
                    "user_id": user_id,
                    "source": f"sync_{source_type}",
                    "sync_source_id": source_id,
                    "sync_source_name": source["name"],
                    "upload_date": datetime.utcnow().isoformat(),
                    "filename": filename,
                    "original_path": file_info.get("path", ""),
                    "size": str(len(content)),
                }
                all_metadata = {**extracted_metadata, **custom_metadata}

                # Upload to centralized S3
                result = upload_service.upload_to_s3(
                    file_content=content,
                    file_name=filename,
                    user_id=user_id,
                    metadata=all_metadata,
                    s3_key_override=s3_key,
                )

                # Record in tracker
                ingestion_tracker.record_ingested(
                    s3_key=result["s3_key"],
                    etag=etag_or_hash,
                )

                files_synced += 1
                logger.debug(f"Synced: {filename} → {s3_key}")

            except Exception as e:
                files_failed += 1
                errors.append(f"{file_info['name']}: {str(e)}")
                logger.warning(f"Failed to sync {file_info['name']}: {e}")
                continue

        # 6. Trigger KB ingestion if anything new
        if files_synced > 0:
            try:
                upload_service.trigger_kb_sync()
                logger.info(f"KB sync triggered after importing {files_synced} files")
            except Exception as e:
                logger.error(f"KB sync trigger failed: {e}")

        # 7. Update status
        status = "success" if files_failed == 0 else "partial"
        sync_source_service.complete_history(
            history_id,
            status=status,
            files_found=files_found,
            files_synced=files_synced,
            files_skipped=files_skipped,
            files_failed=files_failed,
            error="; ".join(errors[:5]) if errors else None,
        )
        sync_source_service.update_sync_status(
            source_id, status, files_synced=files_synced,
            error=errors[0] if errors else None,
        )

        summary = {
            "status": status,
            "files_found": files_found,
            "files_synced": files_synced,
            "files_skipped": files_skipped,
            "files_failed": files_failed,
            "errors": errors[:5],
        }
        logger.info(f"Sync complete: {source['name']} — {summary}")
        return summary

    except Exception as e:
        logger.error(f"Sync failed for {source['name']}: {e}", exc_info=True)
        sync_source_service.complete_history(
            history_id, status="failed", error=str(e)
        )
        sync_source_service.update_sync_status(source_id, "failed", error=str(e))
        return {"status": "failed", "error": str(e)}


def _guess_content_type(filename: str) -> str:
    """Guess content type from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mapping = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv",
        "txt": "text/plain",
        "html": "text/html",
        "json": "application/json",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "mp4": "video/mp4",
        "mp3": "audio/mpeg",
    }
    return mapping.get(ext, "application/octet-stream")
