"""
Complete Knowledge Base API with Automatic Metadata Extraction
Direct S3 → Bedrock KB flow with metadata enrichment
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import services, config, etc.
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.upload_service import upload_service
from services.google_drive_service import google_drive_service
from services.metadata_extractor import metadata_extractor
from services.kb_query_service import kb_query_service
from services.ingestion_tracker import ingestion_tracker
from services.file_repository_service import file_repository_service
from config import settings
from utils.logger import (
    get_logger, setup_logging, log_upload, log_query,
    log_metadata_extraction, log_sync_job, log_kb_operation
)
from middleware import LoggingMiddleware

# Initialize logging system
setup_logging()
logger = get_logger(__name__)

# ============================================================================
# Scheduler — runs incremental sync on a configurable interval
# Set SYNC_INTERVAL_HOURS in .env (default: 1 hour)
# Set USE_EVENTBRIDGE=true to disable APScheduler (production with EventBridge)
# ============================================================================
SYNC_INTERVAL_MINUTES = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
USE_EVENTBRIDGE = os.getenv("USE_EVENTBRIDGE", "false").lower() == "true"
scheduler = AsyncIOScheduler() if not USE_EVENTBRIDGE else None


async def scheduled_incremental_sync():
    """Background job: scan S3 and ingest only new/changed files."""
    logger.info("Scheduled incremental sync starting...")
    try:
        new_or_changed = ingestion_tracker.get_new_or_changed_files()

        if not new_or_changed:
            logger.info("Scheduled sync: nothing new to ingest")
            return

        logger.info(f"Scheduled sync: found {len(new_or_changed)} new/changed files")
        sync_result = upload_service.trigger_kb_sync()

        for file_info in new_or_changed:
            ingestion_tracker.record_ingested(
                s3_key=file_info["s3_key"],
                etag=file_info["etag"],
            )

        logger.info(
            f"Scheduled sync complete — job: {sync_result['ingestion_job_id']}, "
            f"files: {len(new_or_changed)}"
        )
    except Exception as e:
        logger.error(f"Scheduled sync failed: {str(e)}")

app = FastAPI(
    title="Knowledge Base API",
    description="Multi-source document ingestion with automatic metadata extraction",
    version="3.0.0"
)

# Add logging middleware BEFORE CORS
app.add_middleware(LoggingMiddleware)

# ============================================================================
# Scheduler startup / shutdown
# ============================================================================

@app.on_event("startup")
async def start_scheduler():
    """Start the background incremental sync scheduler on app startup."""
    if USE_EVENTBRIDGE:
        logger.info(
            "USE_EVENTBRIDGE=true — APScheduler disabled. "
            "Incremental sync will be triggered by AWS EventBridge."
        )
        return

    scheduler.add_job(
        scheduled_incremental_sync,
        trigger=IntervalTrigger(minutes=SYNC_INTERVAL_MINUTES),
        id="incremental_sync",
        name=f"Incremental KB sync every {SYNC_INTERVAL_MINUTES}m",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"APScheduler started — incremental sync every {SYNC_INTERVAL_MINUTES} minute(s). "
        f"Set USE_EVENTBRIDGE=true to switch to EventBridge in production."
    )


@app.on_event("shutdown")
async def stop_scheduler():
    """Cleanly shut down the scheduler when the app stops."""
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URLs in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Request/Response Models
# ============================================================================

class PreSignedUrlRequest(BaseModel):
    file_name: str
    file_type: str
    user_id: str
    team_id: Optional[str] = None
    department: Optional[str] = None
    tags: Optional[List[str]] = None

class GoogleDriveImportRequest(BaseModel):
    files: List[Dict[str, Any]]  # [{id, name, mimeType}, ...]
    google_access_token: str
    user_id: str
    team_id: Optional[str] = None
    department: Optional[str] = None
    drive_id: Optional[str] = None  # None = personal My Drive, set for Shared Drive

class QueryRequest(BaseModel):
    query: str
    user_id: str
    team_id: Optional[str] = None
    max_results: int = 10

class SyncRequest(BaseModel):
    force: bool = False

class ScheduledSyncRequest(BaseModel):
    """Used by EventBridge / external scheduler to trigger incremental sync"""
    source: str = "scheduler"  # Who triggered this: scheduler, manual, s3_event


class FileRepoImportRequest(BaseModel):
    """Request to import files from an external S3 bucket"""
    source_bucket: str
    prefix: str = ""           # folder path e.g. "hr-policies/"
    user_id: str
    team_id: Optional[str] = None
    department: Optional[str] = None
    max_files: int = 1000


class FileRepoSingleImportRequest(BaseModel):
    """Request to import a single file from an external S3 bucket"""
    source_bucket: str
    source_key: str            # full key e.g. "hr-policies/policy.pdf"
    user_id: str
    team_id: Optional[str] = None
    department: Optional[str] = None


class FileRepoUriImportRequest(BaseModel):
    """Request to import using a plain S3 URI"""
    s3_uri: str                # e.g. s3://company-bucket/hr-policies/policy.pdf
    user_id: str
    team_id: Optional[str] = None
    department: Optional[str] = None

# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Knowledge Base API",
        "version": "3.0.0",
        "status": "healthy",
        "architecture": "S3 → Bedrock KB (with auto metadata extraction) → Query",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "s3": "connected",
            "bedrock_kb": "connected",
            "metadata_extraction": "enabled"
        },
        "kb_id": settings.BEDROCK_KB_ID,
        "region": settings.AWS_REGION
    }

@app.get("/api/supported-formats")
async def get_supported_formats():
    """Get list of supported file formats"""
    return {
        "formats": {
            "documents": [
                {"type": "PDF", "extensions": [".pdf"], "metadata": "Author, Title, Creation Date, Keywords"},
                {"type": "DOCX", "extensions": [".docx", ".doc"], "metadata": "Author, Title, Company, Creation Date"},
                {"type": "PPTX", "extensions": [".pptx", ".ppt"], "metadata": "Author, Title, Creation Date"},
                {"type": "TXT", "extensions": [".txt"], "metadata": "Filename, Size, Upload Date"},
                {"type": "Excel", "extensions": [".xlsx", ".xls"], "metadata": "Author, Sheet Names, Creation Date"}
            ],
            "images": [
                {"type": "JPG", "extensions": [".jpg", ".jpeg"], "metadata": "EXIF data (camera, location, timestamp)"},
                {"type": "PNG", "extensions": [".png"], "metadata": "Dimensions, Creation Date"}
            ],
            "videos": [
                {"type": "MP4", "extensions": [".mp4"], "metadata": "Duration, Resolution, Codec, Transcription"},
                {"type": "AVI", "extensions": [".avi"], "metadata": "Duration, Resolution, Transcription"}
            ],
            "audio": [
                {"type": "MP3", "extensions": [".mp3"], "metadata": "Duration, Bitrate, Artist, Album"},
                {"type": "WAV", "extensions": [".wav"], "metadata": "Duration, Sample Rate, Transcription"}
            ]
        },
        "metadata_types": {
            "automatic": "Extracted from file properties (author, creation date, etc.)",
            "custom": "Added by user (tags, department, category)",
            "system": "Added by system (upload date, user_id, source)"
        }
    }

# ============================================================================
# Upload Endpoints (Web UI)
# ============================================================================

@app.post("/api/upload/get-presigned-url")
async def get_presigned_url(request: PreSignedUrlRequest):
    """
    Generate pre-signed URL for direct S3 upload from frontend

    This allows frontend to upload directly to S3 without going through backend,
    which is more efficient for large files.
    """
    try:
        # Extract custom metadata from request
        custom_metadata = {
            'user_id': request.user_id,
            'source': 'web_ui',
            'filename': request.file_name,
            'upload_date': datetime.utcnow().isoformat()
        }

        if request.team_id:
            custom_metadata['team_id'] = request.team_id
        if request.department:
            custom_metadata['department'] = request.department
        if request.tags:
            custom_metadata['tags'] = ','.join(request.tags)

        # Generate pre-signed URL
        result = upload_service.generate_presigned_url(
            file_name=request.file_name,
            file_type=request.file_type,
            user_id=request.user_id,
            custom_metadata=custom_metadata
        )

        return {
            "upload_url": result['upload_url'],
            "s3_key": result['s3_key'],
            "expires_in": 3600,
            "note": "Upload file to this URL using PUT request. Bedrock KB will auto-sync and extract metadata."
        }

    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/direct")
async def upload_direct(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    team_id: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)  # Comma-separated
):
    """
    Direct file upload through backend

    Includes automatic metadata extraction from the file itself.
    """
    start_time = time.time()

    try:
        logger.info(f"Uploading file: {file.filename} for user: {user_id}")

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Extract metadata from file (AUTOMATIC)
        extracted_metadata = metadata_extractor.extract_metadata(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type
        )

        # Log metadata extraction
        log_metadata_extraction(
            logger=logger,
            filename=file.filename,
            extracted_fields=extracted_metadata,
            success=True
        )

        # Combine with custom metadata
        custom_metadata = {
            'user_id': user_id,
            'source': 'web_ui',
            'upload_date': datetime.utcnow().isoformat(),
            'filename': file.filename,
            'size': str(len(file_content))
        }

        if team_id:
            custom_metadata['team_id'] = team_id
        if department:
            custom_metadata['department'] = department
        if tags:
            custom_metadata['tags'] = tags

        # Merge extracted and custom metadata
        all_metadata = {**extracted_metadata, **custom_metadata}

        # Upload to S3 with metadata
        result = upload_service.upload_to_s3(
            file_content=file_content,
            file_name=file.filename,
            user_id=user_id,
            metadata=all_metadata
        )

        # Log successful upload
        duration_ms = round((time.time() - start_time) * 1000, 2)
        log_upload(
            logger=logger,
            filename=file.filename,
            user_id=user_id,
            file_size=file_size,
            source='web_ui',
            success=True,
            s3_key=result['s3_key']
        )

        logger.info(f"Upload completed in {duration_ms}ms - S3: {result['s3_key']}")

        return JSONResponse(
            status_code=202,
            content={
                "message": "File uploaded and KB sync started",
                "s3_key": result['s3_key'],
                "s3_uri": result['s3_uri'],
                "ingestion_job_id": result.get('ingestion_job_id'),
                "metadata": {
                    "extracted": extracted_metadata,
                    "custom": custom_metadata
                },
                "note": "Bedrock KB ingestion job started — document will be queryable in ~1-2 minutes"
            }
        )

    except Exception as e:
        # Log failed upload
        log_upload(
            logger=logger,
            filename=file.filename,
            user_id=user_id,
            file_size=len(file_content) if 'file_content' in locals() else 0,
            source='web_ui',
            success=False,
            error=str(e)
        )
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Google Drive Import
# ============================================================================

@app.get("/api/google-drive/shared-drives")
async def list_shared_drives(google_access_token: str = Query(...)):
    """
    List all Google Shared Drives (Team Drives) the user has access to.
    Use the returned drive IDs when importing files from a Shared Drive.
    """
    try:
        drives = google_drive_service.list_shared_drives(
            access_token=google_access_token
        )
        return {
            "count": len(drives),
            "shared_drives": drives,
            "note": "Use drive 'id' in the import request to import from a Shared Drive"
        }
    except Exception as e:
        logger.error(f"Failed to list shared drives: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/google-drive/files")
async def list_drive_files(
    google_access_token: str = Query(...),
    drive_id: Optional[str] = Query(None, description="Shared Drive ID. Leave empty for personal My Drive")
):
    """
    List files from personal Google Drive or a specific Shared Drive.
    """
    try:
        files = google_drive_service.list_files(
            access_token=google_access_token,
            drive_id=drive_id
        )
        return {
            "count": len(files),
            "drive_type": "shared_drive" if drive_id else "personal",
            "drive_id": drive_id,
            "files": files
        }
    except Exception as e:
        logger.error(f"Failed to list drive files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/google-drive/import")
async def import_from_google_drive(request: GoogleDriveImportRequest):
    """
    Import files from personal Google Drive or a Google Shared Drive.

    Flow:
    1. Download files (supports both My Drive and Shared Drive)
    2. Extract metadata automatically
    3. Upload to S3 with metadata
    4. Bedrock KB auto-syncs
    """
    try:
        results = []

        for file in request.files:
            logger.info(
                f"Importing from {'Shared Drive' if request.drive_id else 'My Drive'}: "
                f"{file['name']} (ID: {file['id']})"
            )

            # Download from Google Drive (personal or shared)
            file_content = google_drive_service.download_file(
                file_id=file['id'],
                access_token=request.google_access_token,
                drive_id=request.drive_id
            )

            # Extract metadata automatically
            extracted_metadata = metadata_extractor.extract_metadata(
                file_content=file_content,
                filename=file['name'],
                content_type=file.get('mimeType', 'application/octet-stream')
            )

            # Custom metadata
            custom_metadata = {
                'user_id': request.user_id,
                'source': 'google_shared_drive' if request.drive_id else 'google_drive',
                'drive_file_id': file['id'],
                'drive_id': request.drive_id or 'my_drive',
                'upload_date': datetime.utcnow().isoformat(),
                'filename': file['name']
            }

            if request.team_id:
                custom_metadata['team_id'] = request.team_id
            if request.department:
                custom_metadata['department'] = request.department

            # Merge metadata
            all_metadata = {**extracted_metadata, **custom_metadata}

            # Upload to S3
            result = upload_service.upload_to_s3(
                file_content=file_content,
                file_name=file['name'],
                user_id=request.user_id,
                metadata=all_metadata
            )

            results.append({
                "filename": file['name'],
                "s3_key": result['s3_key'],
                "source": custom_metadata['source'],
                "metadata": all_metadata
            })

        return {
            "message": f"Successfully imported {len(results)} files",
            "drive_type": "shared_drive" if request.drive_id else "personal",
            "count": len(results),
            "files": results,
            "note": "Bedrock KB will auto-sync these files"
        }

    except Exception as e:
        logger.error(f"Google Drive import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# File Repository (External S3 Bucket Import)
# ============================================================================

@app.get("/api/file-repo/list")
async def list_repo_files(
    source_bucket: str = Query(..., description="Source S3 bucket name"),
    prefix: str = Query("", description="Folder path e.g. hr-policies/"),
    max_files: int = Query(100, le=1000)
):
    """
    List files available in an external S3 bucket under a given prefix.
    Use this to preview what will be imported before triggering the import.
    """
    try:
        files = file_repository_service.list_source_files(
            source_bucket=source_bucket,
            prefix=prefix,
            max_files=max_files
        )
        return {
            "source": f"s3://{source_bucket}/{prefix}",
            "count": len(files),
            "files": files
        }
    except Exception as e:
        logger.error(f"Failed to list repo files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/file-repo/import")
async def import_from_file_repo(request: FileRepoImportRequest):
    """
    Import all files from a folder in an external S3 bucket
    into the centralised KB bucket.

    Flow:
    1. Lists all files under the given prefix in the source bucket
    2. Downloads each file
    3. Extracts metadata automatically
    4. Copies to centralised S3 bucket under file_repo/ folder
    5. Records in ingestion tracker
    6. KB incremental sync picks them up automatically
    """
    try:
        result = file_repository_service.import_prefix(
            source_bucket=request.source_bucket,
            prefix=request.prefix,
            user_id=request.user_id,
            team_id=request.team_id,
            department=request.department,
            max_files=request.max_files
        )
        return JSONResponse(status_code=202, content=result)
    except Exception as e:
        logger.error(f"File repo bulk import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/file-repo/import-single")
async def import_single_file_from_repo(request: FileRepoSingleImportRequest):
    """
    Import a single file from an external S3 bucket
    into the centralised KB bucket.
    """
    try:
        result = file_repository_service.import_file(
            source_bucket=request.source_bucket,
            source_key=request.source_key,
            user_id=request.user_id,
            team_id=request.team_id,
            department=request.department
        )
        return JSONResponse(status_code=202, content=result)
    except Exception as e:
        logger.error(f"File repo single import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/file-repo/import-uri")
async def import_from_s3_uri(request: FileRepoUriImportRequest):
    """
    Import a file by providing its full S3 URI.

    User simply pastes the S3 URI:
        s3://company-bucket/hr-policies/policy.pdf

    Backend automatically:
    1. Parses the bucket and key from the URI
    2. Downloads the file
    3. Copies to centralised KB bucket
    4. Extracts metadata
    5. KB picks it up on next sync
    """
    try:
        # Parse s3://bucket/key into bucket + key
        uri = request.s3_uri.strip()
        if not uri.startswith("s3://"):
            raise HTTPException(
                status_code=400,
                detail="Invalid S3 URI. Must start with s3://"
            )

        # Remove s3:// prefix and split into bucket + key
        without_prefix = uri[5:]  # "company-bucket/hr-policies/policy.pdf"
        parts = without_prefix.split("/", 1)

        if len(parts) < 2 or not parts[1]:
            raise HTTPException(
                status_code=400,
                detail="Invalid S3 URI. Must be s3://bucket-name/path/to/file"
            )

        source_bucket = parts[0]
        source_key = parts[1]

        logger.info(f"Importing from URI: {uri} → bucket={source_bucket}, key={source_key}")

        result = file_repository_service.import_file(
            source_bucket=source_bucket,
            source_key=source_key,
            user_id=request.user_id,
            team_id=request.team_id,
            department=request.department
        )
        return JSONResponse(status_code=202, content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URI import failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Knowledge Base Sync & Query
# ============================================================================

@app.post("/api/kb/sync")
async def sync_knowledge_base(request: SyncRequest):
    """
    Manually trigger Bedrock KB sync

    This will make KB scan S3 and ingest all new/updated files.
    Usually runs automatically on schedule, but can be triggered manually.
    """
    try:
        result = upload_service.trigger_kb_sync(force=request.force)

        # Log KB operation
        log_kb_operation(
            logger=logger,
            operation='manual_sync',
            kb_id=result['kb_id'],
            job_id=result['ingestion_job_id'],
            status=result['status']
        )

        return JSONResponse(
            status_code=202,
            content={
                "message": "Knowledge Base sync started",
                "ingestion_job_id": result['ingestion_job_id'],
                "status": result['status'],
                "kb_id": result['kb_id']
            }
        )

    except Exception as e:
        log_kb_operation(
            logger=logger,
            operation='manual_sync',
            kb_id=settings.BEDROCK_KB_ID,
            error=str(e)
        )
        logger.error(f"KB sync failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/kb/sync/status/{job_id}")
async def get_sync_status(job_id: str):
    """Get status of KB sync job"""
    try:
        status = upload_service.get_sync_status(job_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get sync status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/kb/incremental-sync")
async def incremental_sync(request: ScheduledSyncRequest):
    """
    Incremental ingestion — only processes new or changed files.

    Flow:
    1. Scan S3 bucket
    2. Compare each file's ETag against the ingestion tracker state
    3. Collect files that are new, changed, or previously failed
    4. If any found, trigger a KB ingestion job
    5. Mark them as ingested in the tracker

    This endpoint is called by:
    - AWS EventBridge scheduler (automated, e.g. every hour)
    - Manual trigger from the UI or admin
    """
    try:
        logger.info(f"Incremental sync triggered by: {request.source}")

        # Step 1: Find new or changed files
        new_or_changed = ingestion_tracker.get_new_or_changed_files()

        if not new_or_changed:
            logger.info("Incremental sync: no new or changed files found")
            return {
                "message": "No new or changed files found",
                "triggered_by": request.source,
                "files_processed": 0,
                "ingestion_job_id": None,
                "timestamp": datetime.utcnow().isoformat(),
            }

        logger.info(f"Found {len(new_or_changed)} files to ingest")

        # Step 2: Trigger KB ingestion job (KB will process all new S3 objects)
        sync_result = upload_service.trigger_kb_sync()

        # Step 3: Mark all detected files as ingested in the tracker
        for file_info in new_or_changed:
            ingestion_tracker.record_ingested(
                s3_key=file_info["s3_key"],
                etag=file_info["etag"],
            )

        return JSONResponse(
            status_code=202,
            content={
                "message": "Incremental sync started",
                "triggered_by": request.source,
                "files_processed": len(new_or_changed),
                "files": [
                    {"s3_key": f["s3_key"], "reason": f["reason"]}
                    for f in new_or_changed
                ],
                "ingestion_job_id": sync_result["ingestion_job_id"],
                "ingestion_status": sync_result["status"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"Incremental sync failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/kb/tracker/stats")
async def get_tracker_stats():
    """
    Get ingestion tracker statistics.
    Shows how many files are tracked, ingested, or failed.
    """
    try:
        stats = ingestion_tracker.get_stats()
        return {
            "tracker_stats": stats,
            "tracker_location": f"s3://{settings.S3_RAW_BUCKET}/.ingestion_tracker/state.json",
        }
    except Exception as e:
        logger.error(f"Failed to get tracker stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/kb/query")
async def query_knowledge_base(request: QueryRequest):
    """
    Query the knowledge base with multilingual support.

    - Auto-detects query language (English, Sinhala, Tamil)
    - Translates query to English for KB search
    - Translates results back to the user's language
    - Applies metadata-based access control
    """
    start_time = time.time()

    try:
        result = kb_query_service.query(
            query=request.query,
            user_id=request.user_id,
            team_id=request.team_id,
            max_results=request.max_results
        )

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Log query
        log_query(
            logger=logger,
            query=request.query,
            user_id=request.user_id,
            results_count=len(result['results']),
            duration_ms=duration_ms,
            filters={'team_id': request.team_id}
        )

        return {
            "query": request.query,
            "results_count": len(result['results']),
            "results": result['results'],
            "language": result['language'],
            "metadata_used": {
                "user_id": request.user_id,
                "team_id": request.team_id
            }
        }

    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Metadata Management
# ============================================================================

@app.get("/api/metadata/{s3_key:path}")
async def get_file_metadata(s3_key: str):
    """
    Get metadata for a specific file

    Returns both extracted and custom metadata
    """
    try:
        metadata = upload_service.get_file_metadata(s3_key)
        return {
            "s3_key": s3_key,
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Failed to get metadata: {str(e)}")
        raise HTTPException(status_code=404, detail="File not found")

@app.get("/api/documents")
async def list_documents(
    user_id: str = Query(...),
    team_id: Optional[str] = Query(None),
    limit: int = Query(100, le=1000)
):
    """
    List documents with metadata

    Useful for showing user what files they have uploaded
    """
    try:
        documents = upload_service.list_user_documents(
            user_id=user_id,
            team_id=team_id,
            limit=limit
        )

        return {
            "count": len(documents),
            "documents": documents
        }

    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Architecture Info
# ============================================================================

@app.get("/api/architecture")
async def get_architecture():
    """Get complete architecture information"""
    return {
        "version": "3.0.0",
        "architecture": "Simplified Bedrock KB with Metadata Extraction",
        "flow": {
            "upload": [
                "1. User selects source (Web UI / Google Drive / S3)",
                "2. File uploaded to S3",
                "3. Automatic metadata extraction (from file properties)",
                "4. Custom metadata added (user_id, tags, department)",
                "5. Metadata stored as S3 object metadata",
                "6. Bedrock KB auto-syncs (hourly or on-demand)",
                "7. KB processes file (BDA parsing for all formats)",
                "8. KB indexes with metadata for filtering"
            ],
            "query": [
                "1. User submits query",
                "2. System adds metadata filters (user_id, team_id)",
                "3. Bedrock KB searches with filters",
                "4. Returns only documents user has access to",
                "5. Results include source metadata"
            ]
        },
        "metadata_extraction": {
            "automatic": {
                "pdf": ["author", "title", "creation_date", "keywords", "page_count"],
                "docx": ["author", "title", "company", "creation_date", "word_count"],
                "images": ["exif_data", "dimensions", "camera_model", "location", "timestamp"],
                "videos": ["duration", "resolution", "codec", "frame_rate"],
                "audio": ["duration", "bitrate", "artist", "album", "genre"]
            },
            "custom": ["user_id", "team_id", "department", "tags", "category"],
            "system": ["upload_date", "source", "file_size", "s3_key"]
        },
        "components": {
            "storage": "Amazon S3",
            "knowledge_base": "Amazon Bedrock Knowledge Base",
            "parsing": "Built-in BDA (all formats)",
            "embeddings": "Amazon Titan Embeddings",
            "vector_store": "Managed by Bedrock KB",
            "api": "FastAPI (Python)"
        },
        "no_lambda_required": True,
        "auto_sync": "Hourly (configurable)",
        "access_control": "Metadata-based filtering"
    }

if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 80)
    logger.info("Starting Knowledge Base API with Metadata Extraction")
    logger.info("Architecture: S3 → Bedrock KB (auto metadata) → Query")
    logger.info("=" * 80)

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
