"""
Complete Knowledge Base API with Automatic Metadata Extraction
Direct S3 → Bedrock KB flow with metadata enrichment
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import services, config, etc.
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import os
import time
import jwt

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.upload_service import upload_service
from services.google_drive_service import google_drive_service
from services.confluence_service import confluence_service
from services.metadata_extractor import metadata_extractor
from services.kb_query_service import kb_query_service
from services.ingestion_tracker import ingestion_tracker
from services.file_repository_service import file_repository_service
from services.auth_service import auth_service
from services.auto_tagger_service import auto_tagger_service
from services.chat_session_service import chat_session_service
from services.database import get_db, SessionLocal
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


async def _poll_sync_configs():
    """Background job: run any SyncConfig rows that are due for execution."""
    try:
        from services.sync_service import sync_service
        from services.database import SessionLocal as _SessionLocal
        db = _SessionLocal()
        try:
            sync_service.run_due_syncs(db)
        except Exception as e:
            logger.error(f"Sync poll failed: {e}")
        finally:
            db.close()
    except ImportError as e:
        logger.warning(f"sync_service not available: {e}")


app = FastAPI(
    title="Knowledge Base API",
    description="Multi-source document ingestion with automatic metadata extraction",
    version="3.0.0"
)

# ============================================================================
# File size limit — 500MB to accommodate video uploads
# Run uvicorn with --limit-max-requests or set in gunicorn config.
# For development: uvicorn api.app:app --host 0.0.0.0 --port 8000
# The limit below is enforced at the application layer for multipart uploads.
# ============================================================================
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(500 * 1024 * 1024)))  # 500MB default

# Add logging middleware BEFORE CORS
app.add_middleware(LoggingMiddleware)

# ============================================================================
# Scheduler startup / shutdown
# ============================================================================

@app.on_event("startup")
async def init_database():
    """Initialize chat session tables on startup."""
    try:
        chat_session_service.init_db()
        logger.info("Chat session database initialized")
    except Exception as e:
        logger.warning(f"Chat DB init skipped (set DATABASE_URL in .env): {e}")


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
    scheduler.add_job(
        _poll_sync_configs,
        trigger=IntervalTrigger(minutes=1),
        id="poll_sync_configs",
        name="Poll scheduled source syncs every 1m",
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

class GoogleDriveImportRequest(BaseModel):
    files: List[Dict[str, Any]]  # [{id, name, mimeType}, ...]
    google_access_token: str
    user_id: str
    team_id: Optional[str] = None
    department: Optional[str] = None
    drive_id: Optional[str] = None  # None = personal My Drive, set for Shared Drive

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None   # optional — omit to search across all documents
    team_id: Optional[str] = None
    max_results: int = 10
    # Dynamic metadata filters (auto-generated by auto_tagger_service at ingestion)
    department: Optional[str] = None
    doc_type: Optional[str] = None
    topic: Optional[str] = None
    language: Optional[str] = None  # auto-detected from query if not provided
    # Chat session (optional — if provided, message is saved to this session)
    session_id: Optional[str] = None

class SyncRequest(BaseModel):
    force: bool = False

class ScheduledSyncRequest(BaseModel):
    """Used by EventBridge / external scheduler to trigger incremental sync"""
    source: str = "scheduler"  # Who triggered this: scheduler, manual, s3_event


class SyncConfigCreate(BaseModel):
    user_id: str
    source_type: str  # 'gdrive' | 'confluence' | 's3'
    display_name: str
    credentials: dict  # raw dict, will be encrypted server-side
    schedule: str = 'daily'
    space_or_path: Optional[str] = None


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


# In-memory state storage for OAuth (production: use Redis)
oauth_states = {}


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.get("/api/auth/google-url")
async def get_google_oauth_url():
    """
    Generate Google OAuth consent URL for login flow

    Returns URL that opens Google consent screen requesting:
    - openid, email, profile (for login)
    - drive.readonly (for Drive access)
    """
    try:
        # Generate CSRF protection state
        state = auth_service.generate_state()

        # PRODUCTION: Change to 'https://your-domain.com/auth-callback' before deployment
        redirect_uri = "http://localhost:3000/auth-callback"

        # Store state temporarily (production: use Redis with expiry)
        oauth_states[state] = {
            "created_at": datetime.utcnow().isoformat(),
            "redirect_uri": redirect_uri
        }

        # Generate OAuth URL
        oauth_url = auth_service.generate_google_oauth_url(
            state=state,
            redirect_uri=redirect_uri
        )

        logger.info(f"Generated OAuth URL with state: {state[:10]}...")

        return {
            "oauth_url": oauth_url,
            "state": state
        }

    except Exception as e:
        logger.error(f"Failed to generate OAuth URL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/callback")
async def auth_callback(
    code: str = Query(...),
    state: str = Query(...)
):
    """
    OAuth callback handler - exchanges code for JWT token

    Flow:
    1. Validate state parameter (CSRF protection)
    2. Exchange auth code for Google tokens
    3. Get user info from Google
    4. Create JWT with user info + Drive token
    5. Return JWT to frontend
    """
    try:
        # Validate state parameter
        if state not in oauth_states:
            logger.warning(f"Invalid state parameter: {state[:10]}...")
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        redirect_uri = oauth_states[state]["redirect_uri"]
        del oauth_states[state]  # Consume state (single use)

        # Exchange authorization code for tokens
        logger.info("Exchanging auth code for tokens...")
        tokens = auth_service.exchange_code_for_tokens(
            code=code,
            redirect_uri=redirect_uri
        )

        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token", "")

        # Get user information
        logger.info("Fetching user info from Google...")
        user_info = auth_service.get_user_info(access_token)

        # Create JWT token with embedded Drive access token + refresh token
        jwt_token = auth_service.create_jwt_token(
            user_info=user_info,
            drive_token=access_token,
            refresh_token=refresh_token,
        )

        logger.info(f"User authenticated: {user_info['email']}")

        return {
            "token": jwt_token,
            "user": {
                "email": user_info["email"],
                "name": user_info["name"],
                "picture": user_info.get("picture", "")
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/me")
async def get_current_user(authorization: Optional[str] = Query(None)):
    """
    Get current user info from JWT token

    Requires Authorization header: Bearer {jwt_token}
    """
    try:
        # Extract token from header
        token = auth_service.extract_token_from_header(authorization)
        if not token:
            raise HTTPException(status_code=401, detail="Missing authorization token")

        # Verify and decode JWT
        payload = auth_service.verify_jwt_token(token)

        return {
            "user": {
                "id": payload["sub"],
                "email": payload["email"],
                "name": payload["name"],
                "picture": payload.get("picture", "")
            }
        }

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        logger.error(f"Get current user failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/refresh-drive-token")
async def refresh_drive_token(request: Request):
    """
    Exchange the stored refresh_token for a new Google Drive access token
    and return an updated JWT. Called by the frontend when a 401 is received.
    """
    try:
        body = await request.json()
        jwt_token = body.get("jwt_token")
        if not jwt_token:
            raise HTTPException(status_code=400, detail="jwt_token required")

        payload = auth_service.verify_jwt_token(jwt_token)
        refresh_token = payload.get("drive_refresh_token", "")
        if not refresh_token:
            raise HTTPException(status_code=400, detail="No refresh token available — user must re-login")

        new_access_token = auth_service.refresh_drive_token(refresh_token)

        user_info = {
            "id": payload["sub"],
            "email": payload["email"],
            "name": payload["name"],
            "picture": payload.get("picture", ""),
        }
        new_jwt = auth_service.create_jwt_token(
            user_info=user_info,
            drive_token=new_access_token,
            refresh_token=refresh_token,
        )
        return {"token": new_jwt, "drive_token": new_access_token}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"refresh_drive_token failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/logout")
async def logout():
    """
    Logout endpoint (client-side token removal confirmation)

    Note: JWT tokens cannot be invalidated server-side unless we implement
    a token blacklist. Client must remove token from storage.
    """
    return {"message": "Logged out successfully"}


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

@app.post("/api/upload/direct")
async def upload_direct(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    team_id: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)  # Comma-separated
):
    """
    Direct file upload through backend.

    Returns HTTP 202 immediately after the file is stored in S3.
    KB ingestion (sync + polling) runs in a background task so the
    HTTP response is never blocked — safe behind any API gateway.

    Poll  GET /api/upload/sync-status/{job_id}  for ingestion progress.
    """
    start_time = time.time()

    VIDEO_MIME_MAP = {
        'mp4':  'video/mp4',
        'avi':  'video/x-msvideo',
        'mov':  'video/quicktime',
        'mkv':  'video/x-matroska',
        'webm': 'video/webm',
    }

    try:
        logger.info(f"Uploading file: {file.filename} for user: {user_id}")

        file_content = await file.read()
        file_size    = len(file_content)

        if file_size > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file_size / (1024*1024):.1f}MB exceeds the {MAX_UPLOAD_BYTES // (1024*1024)}MB limit"
            )

        # Normalise content type for video files
        content_type = file.content_type or 'application/octet-stream'
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if content_type in ('application/octet-stream', '') and file_ext in VIDEO_MIME_MAP:
            content_type = VIDEO_MIME_MAP[file_ext]
            logger.info(f"Normalised content type for {file.filename}: {content_type}")

        # Extract metadata
        extracted_metadata = metadata_extractor.extract_metadata(
            file_content=file_content,
            filename=file.filename,
            content_type=content_type
        )
        log_metadata_extraction(
            logger=logger,
            filename=file.filename,
            extracted_fields=extracted_metadata,
            success=True
        )

        # Build combined metadata
        custom_metadata = {
            'user_id':     user_id,
            'source':      'web_ui',
            'upload_date': datetime.utcnow().isoformat(),
            'filename':    file.filename,
            'size':        str(file_size),
        }
        if team_id:
            custom_metadata['team_id'] = team_id
        if department:
            custom_metadata['department'] = department
        if tags:
            custom_metadata['tags'] = tags

        all_metadata = {**extracted_metadata, **custom_metadata}

        # ── Auto-tag: use Claude to generate smart metadata for KB filtering ──
        try:
            bedrock_metadata = auto_tagger_service.generate_tags(
                file_content=file_content,
                filename=file.filename,
                content_type=content_type,
                user_id=user_id,
                team_id=team_id,
                department=department,
                tags=tags,
            )
            logger.info(f"Auto-tagging complete for {file.filename}: {list(bedrock_metadata.get('metadataAttributes', {}).keys())}")
        except Exception as e:
            logger.warning(f"Auto-tagging failed for {file.filename}, using basic metadata: {e}")
            bedrock_metadata = {
                "metadataAttributes": {
                    "user_id": user_id,
                    "filename": file.filename,
                    "content_type": content_type,
                    **({"team_id": team_id} if team_id else {}),
                    **({"department": department} if department else {}),
                }
            }

        # ── Store file in S3 (blocking — but fast, just a network PUT) ──
        result = upload_service.upload_to_s3(
            file_content=file_content,
            file_name=file.filename,
            user_id=user_id,
            metadata=all_metadata,
            bedrock_metadata=bedrock_metadata,
        )

        # ── Schedule KB sync as background task — returns BEFORE sync ───
        background_tasks.add_task(
            upload_service.background_sync,
            s3_key=result['s3_key'],
            filename=file.filename,
            etag=result['etag'],
        )

        duration_ms = round((time.time() - start_time) * 1000, 2)
        log_upload(
            logger=logger,
            filename=file.filename,
            user_id=user_id,
            file_size=file_size,
            source='web_ui',
            success=True,
            s3_key=result['s3_key'],
        )
        logger.info(f"Upload endpoint completed in {duration_ms}ms — KB sync running in background")

        return JSONResponse(
            status_code=202,
            content={
                "message":         "File uploaded — KB ingestion running in background",
                "s3_key":          result['s3_key'],
                "s3_uri":          result['s3_uri'],
                "filename":        file.filename,
                "size_bytes":      file_size,
                "metadata": {
                    "extracted": extracted_metadata,
                    "custom":    custom_metadata,
                },
                "auto_tags": bedrock_metadata.get("metadataAttributes", {}),
                "note": "Poll /api/upload/sync-status/<job_id> for ingestion progress. "
                        "The job_id is available in the backend logs under 'kb_sync_triggered'.",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        log_upload(
            logger=logger,
            filename=file.filename,
            user_id=user_id,
            file_size=len(file_content) if 'file_content' in locals() else 0,
            source='web_ui',
            success=False,
            error=str(e),
        )
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/upload/sync-status/{job_id}")
async def get_upload_sync_status(job_id: str):
    """
    Poll the status of a KB ingestion job started by an upload.

    Returns the current job status and statistics.
    Call this endpoint periodically after uploading to track ingestion progress.

    Possible status values:
      STARTING    — job accepted, not yet running
      IN_PROGRESS — Bedrock is actively chunking / embedding
      COMPLETE    — document indexed and queryable
      FAILED      — ingestion failed (check failure_reasons)
      STOPPED     — job was stopped manually
    """
    try:
        status = upload_service.get_sync_status(job_id)
        stats  = status.get('statistics', {})
        return {
            "ingestion_job_id":           status['ingestion_job_id'],
            "status":                     status['status'],
            "started_at":                 str(status.get('started_at', '')),
            "completed_at":               str(status.get('completed_at', '')),
            "documents_scanned":          stats.get('numberOfDocumentsScanned', 0),
            "new_documents_indexed":      stats.get('numberOfNewDocumentsIndexed', 0),
            "modified_documents_indexed": stats.get('numberOfModifiedDocumentsIndexed', 0),
            "documents_failed":           stats.get('numberOfDocumentsFailed', 0),
            "failure_reasons":            status.get('failure_reasons', []),
            "queryable":                  status['status'] == 'COMPLETE',
        }
    except Exception as e:
        logger.error(f"Failed to get sync status for job {job_id}: {str(e)}")
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
        status = getattr(getattr(e, 'response', None), 'status_code', None)
        if status == 401 or '401' in str(e):
            raise HTTPException(status_code=401, detail="Google access token expired — please re-authenticate")
        logger.error(f"Failed to list shared drives: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/google-drive/browse")
async def browse_drive_folder(
    google_access_token: str = Query(...),
    folder_id: str = Query("root", description="Folder ID to browse. Use 'root' for Drive root."),
    drive_id: Optional[str] = Query(None, description="Shared Drive ID. Leave empty for personal My Drive")
):
    """
    Browse a Google Drive folder and return folders and files separately.

    Used for frontend breadcrumb navigation.

    Returns:
        {
            "folders": [{id, name, mimeType}, ...],
            "files": [{id, name, mimeType, size, modifiedTime}, ...]
        }
    """
    try:
        result = google_drive_service.browse_folder(
            access_token=google_access_token,
            folder_id=folder_id,
            drive_id=drive_id
        )
        return {
            "folder_id": folder_id,
            "drive_type": "shared_drive" if drive_id else "personal",
            "drive_id": drive_id,
            "folders": result["folders"],
            "files": result["files"],
            "count": {
                "folders": len(result["folders"]),
                "files": len(result["files"])
            }
        }
    except Exception as e:
        status = getattr(getattr(e, 'response', None), 'status_code', None)
        if status == 401 or '401' in str(e):
            raise HTTPException(status_code=401, detail="Google access token expired — please re-authenticate")
        logger.error(f"Failed to browse drive folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/google-drive/shared-with-me")
async def list_shared_with_me(
    google_access_token: str = Query(...),
    page_token: Optional[str] = Query(None),
):
    """
    List folders shared with the authenticated user by other Google accounts.
    Returns folders only — user picks one as a sync source.
    """
    import requests as req
    try:
        headers = {"Authorization": f"Bearer {google_access_token}"}
        params = {
            "q": "sharedWithMe = true and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            "fields": "nextPageToken, files(id, name, mimeType, owners, sharingUser)",
            "pageSize": 100,
            "orderBy": "name",
        }
        if page_token:
            params["pageToken"] = page_token

        resp = req.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        folders = [
            {
                "id": f["id"],
                "name": f["name"],
                "owner": f.get("owners", [{}])[0].get("displayName", ""),
                "owner_email": f.get("owners", [{}])[0].get("emailAddress", ""),
                "shared_by": f.get("sharingUser", {}).get("displayName", ""),
            }
            for f in data.get("files", [])
        ]
        return {"folders": folders, "count": len(folders), "next_page_token": data.get("nextPageToken")}

    except req.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise HTTPException(status_code=401, detail="Google access token expired")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list shared-with-me: {str(e)}")
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

            # Auto-tag with Claude for Bedrock KB filtering
            try:
                bedrock_metadata = auto_tagger_service.generate_tags(
                    file_content=file_content,
                    filename=file['name'],
                    content_type=file.get('mimeType', 'application/octet-stream'),
                    user_id=request.user_id,
                    team_id=request.team_id,
                    department=request.department,
                )
            except Exception as e:
                logger.warning(f"Auto-tagging failed for {file['name']}: {e}")
                bedrock_metadata = {
                    "metadataAttributes": {
                        "user_id": request.user_id,
                        "filename": file['name'],
                        **({"team_id": request.team_id} if request.team_id else {}),
                        **({"department": request.department} if request.department else {}),
                    }
                }

            # Upload to S3 with .metadata.json companion
            result = upload_service.upload_to_s3(
                file_content=file_content,
                file_name=file['name'],
                user_id=request.user_id,
                metadata=all_metadata,
                bedrock_metadata=bedrock_metadata,
            )

            results.append({
                "filename": file['name'],
                "s3_key": result['s3_key'],
                "source": custom_metadata['source'],
                "metadata": all_metadata,
                "auto_tags": bedrock_metadata.get("metadataAttributes", {}),
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
# Confluence Cloud Import
# ============================================================================

class ConfluenceImportRequest(BaseModel):
    site_url: str
    email: str
    api_token: str
    items: List[Dict[str, Any]]   # [{type: 'page'|'attachment', id, title, download_url?}]
    user_id: Optional[str] = None
    team_id: Optional[str] = None
    department: Optional[str] = None


@app.post("/api/confluence/test")
async def confluence_test_connection(request: Request):
    """Test Confluence credentials."""
    body = await request.json()
    try:
        info = confluence_service.test_connection(
            site_url=body['site_url'],
            email=body['email'],
            api_token=body['api_token'],
        )
        return {'ok': True, 'user': info}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Connection failed: {str(e)}")


# ============================================================================
# Sync Source — Credential Validation & Resource Discovery
# ============================================================================

class S3CredsRequest(BaseModel):
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: Optional[str] = None
    region: Optional[str] = "ap-south-1"


@app.post("/api/sync/s3/list-buckets")
async def list_s3_buckets(request: S3CredsRequest):
    """
    Validate AWS credentials and return list of accessible S3 buckets.
    Called when user finishes entering S3 credentials in the sync setup form.
    """
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    try:
        kwargs = {
            "region_name": request.region or "ap-south-1",
            "aws_access_key_id": request.aws_access_key_id,
            "aws_secret_access_key": request.aws_secret_access_key,
        }
        if request.aws_session_token:
            kwargs["aws_session_token"] = request.aws_session_token

        s3 = boto3.client("s3", **kwargs)
        response = s3.list_buckets()
        buckets = [b["Name"] for b in response.get("Buckets", [])]
        return {"ok": True, "buckets": buckets, "count": len(buckets)}

    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg = e.response["Error"]["Message"]
        raise HTTPException(status_code=401, detail=f"{code}: {msg}")
    except NoCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid AWS credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync/s3/list-prefixes")
async def list_s3_prefixes(
    bucket: str = Query(...),
    prefix: str = Query(""),
    request: S3CredsRequest = None
):
    """
    List top-level folders (prefixes) in a bucket to let user pick a folder.
    """
    import boto3
    from botocore.exceptions import ClientError

    try:
        kwargs = {
            "region_name": request.region or "ap-south-1",
            "aws_access_key_id": request.aws_access_key_id,
            "aws_secret_access_key": request.aws_secret_access_key,
        }
        if request.aws_session_token:
            kwargs["aws_session_token"] = request.aws_session_token

        s3 = boto3.client("s3", **kwargs)
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            Delimiter="/",
            MaxKeys=200,
        )

        folders = [
            cp["Prefix"] for cp in response.get("CommonPrefixes", [])
        ]
        files = [
            {
                "key": obj["Key"],
                "name": obj["Key"].split("/")[-1],
                "size": obj["Size"],
                "modified": obj["LastModified"].isoformat(),
            }
            for obj in response.get("Contents", [])
            if not obj["Key"].endswith("/")
        ]

        return {
            "ok": True,
            "bucket": bucket,
            "prefix": prefix,
            "folders": folders,
            "files": files[:50],  # preview only
            "total_files": len(files),
        }

    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ConfluenceCredsRequest(BaseModel):
    site_url: str
    email: str
    api_token: str


@app.post("/api/sync/confluence/list-spaces")
async def list_confluence_spaces(request: ConfluenceCredsRequest):
    """
    Validate Confluence credentials and return list of spaces.
    Supports both Confluence Cloud (atlassian.net) and Server/DC.
    """
    import requests as req
    from requests.auth import HTTPBasicAuth

    try:
        base = request.site_url.strip().rstrip("/")
        if not base.startswith("http"):
            base = f"https://{base}"

        # Remove /wiki suffix if user included it — we add it ourselves
        if base.endswith("/wiki"):
            base = base[:-5]

        auth = HTTPBasicAuth(request.email, request.api_token)

        # Try Confluence Cloud API v2 first (atlassian.net)
        cloud_url = f"{base}/wiki/api/v2/spaces"
        resp = req.get(
            cloud_url,
            auth=auth,
            params={"limit": 100},
            timeout=15,
        )

        # Fall back to legacy REST API (Server / Data Center)
        if resp.status_code in (404, 403):
            legacy_url = f"{base}/wiki/rest/api/space"
            resp = req.get(
                legacy_url,
                auth=auth,
                params={"limit": 100, "type": "global"},
                timeout=15,
            )

        # Last resort — try without /wiki prefix (some self-hosted setups)
        if resp.status_code in (404, 403):
            legacy_url = f"{base}/rest/api/space"
            resp = req.get(
                legacy_url,
                auth=auth,
                params={"limit": 100},
                timeout=15,
            )

        resp.raise_for_status()
        data = resp.json()

        # Cloud API v2 returns {"results": [...]}
        # Legacy API returns {"results": [...]} too, but with different fields
        results = data.get("results", [])
        spaces = [
            {
                "key": s.get("key") or s.get("id", ""),
                "name": s.get("name", ""),
            }
            for s in results
            if s.get("name")
        ]

        return {"ok": True, "spaces": spaces, "count": len(spaces)}

    except req.exceptions.HTTPError as e:
        status = e.response.status_code
        try:
            detail = e.response.json()
            msg = detail.get("message") or detail.get("errorMessages", [None])[0] or str(detail)
        except Exception:
            msg = e.response.text[:300]
        raise HTTPException(
            status_code=status,
            detail=f"Confluence {status}: {msg}. Check your API token has 'Read' permission on spaces."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/confluence/spaces")
async def confluence_list_spaces(
    site_url: str = Query(...),
    email: str = Query(...),
    api_token: str = Query(...),
):
    """List all accessible Confluence spaces."""
    try:
        spaces = confluence_service.list_spaces(site_url, email, api_token)
        return {'spaces': spaces}
    except Exception as e:
        logger.error(f"Confluence list spaces failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/confluence/pages")
async def confluence_list_pages(
    site_url: str = Query(...),
    email: str = Query(...),
    api_token: str = Query(...),
    space_key: str = Query(...),
    parent_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List pages in a Confluence space."""
    try:
        pages = confluence_service.list_pages(site_url, email, api_token, space_key, parent_id, search)
        return {'pages': pages}
    except Exception as e:
        logger.error(f"Confluence list pages failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/confluence/attachments")
async def confluence_list_attachments(
    site_url: str = Query(...),
    email: str = Query(...),
    api_token: str = Query(...),
    page_id: str = Query(...),
):
    """List attachments on a Confluence page."""
    try:
        attachments = confluence_service.list_attachments(site_url, email, api_token, page_id)
        return {'attachments': attachments}
    except Exception as e:
        logger.error(f"Confluence list attachments failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/confluence/import")
async def import_from_confluence(request: ConfluenceImportRequest, background_tasks: BackgroundTasks):
    """Import selected Confluence pages and/or attachments into the KB."""
    imported = []
    errors = []

    custom_metadata = {
        'user_id': request.user_id,
        'team_id': request.team_id,
        'department': request.department,
        'source': 'confluence',
    }

    for item in request.items:
        try:
            item_type = item.get('type', 'page')
            item_title = item.get('title', 'untitled')

            if item_type == 'page':
                content_bytes, filename = confluence_service.download_page_as_html(
                    site_url=request.site_url,
                    email=request.email,
                    api_token=request.api_token,
                    page_id=item['id'],
                    page_title=item_title,
                )
                content_type = 'text/html'

            elif item_type == 'attachment':
                content_bytes = confluence_service.download_attachment(
                    site_url=request.site_url,
                    email=request.email,
                    api_token=request.api_token,
                    download_url=item['download_url'],
                    filename=item_title,
                )
                filename = item_title
                content_type = item.get('media_type', 'application/octet-stream')

            else:
                continue

            # Upload to S3 KB bucket
            extracted_metadata = metadata_extractor.extract_metadata(content_bytes, filename)
            merged_metadata = {**extracted_metadata, **{k: v for k, v in custom_metadata.items() if v}}

            result = upload_service.upload_to_s3(
                file_content=content_bytes,
                file_name=filename,
                user_id=request.user_id or 'confluence',
                metadata=merged_metadata,
            )
            s3_key = result.get('s3_key', f'docs/{filename}')

            imported.append({
                'id': item['id'],
                'title': item_title,
                'type': item_type,
                'filename': filename,
                's3_key': s3_key,
            })
            logger.info(f"Confluence import: {filename} → s3://{settings.S3_RAW_BUCKET}/{s3_key}")

        except Exception as e:
            logger.error(f"Confluence import failed for {item.get('title', item.get('id'))}: {e}")
            errors.append({'id': item.get('id'), 'title': item.get('title', ''), 'error': str(e)})

    if imported:
        last = imported[-1]
        background_tasks.add_task(upload_service.background_sync, last['s3_key'], last['filename'])

    return {
        'imported': imported,
        'errors': errors,
        'total': len(imported),
        'message': f"Imported {len(imported)} item(s) from Confluence. KB sync started.",
    }


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

@app.get("/api/kb/sync/latest")
async def get_latest_sync_job():
    """
    Return the most recently started KB ingestion job.
    Used by the frontend SyncStatusCard to track background ingestion progress.
    """
    try:
        response = upload_service.bedrock_agent_client.list_ingestion_jobs(
            knowledgeBaseId=settings.BEDROCK_KB_ID,
            dataSourceId=settings.BEDROCK_DATA_SOURCE_ID,
            sortBy={'attribute': 'STARTED_AT', 'order': 'DESCENDING'},
            maxResults=1,
        )
        jobs = response.get('ingestionJobSummaries', [])
        if not jobs:
            raise HTTPException(status_code=404, detail="No ingestion jobs found")

        job = jobs[0]
        return {
            "ingestion_job_id": job['ingestionJobId'],
            "status":           job['status'],
            "started_at":       str(job.get('startedAt', '')),
            "updated_at":       str(job.get('updatedAt', '')),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest sync job: {str(e)}")
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

@app.post("/api/retrieve")
@app.post("/api/kb/query")
async def query_knowledge_base(request: QueryRequest):
    """
    Hybrid search + retrieve-and-generate against Bedrock Knowledge Base.

    - HYBRID search (vector + keyword BM25), 10 chunks
    - Claude Sonnet 4.5 generates a summarised answer with citations
    - Auto-detects query language (English, Sinhala, Tamil)
    - Translates query → English for retrieval, answer → original language
    """
    start_time = time.time()

    try:
        result = kb_query_service.query(
            query=request.query,
            user_id=request.user_id,
            team_id=request.team_id,
            max_results=request.max_results,
            department=request.department,
            doc_type=request.doc_type,
            topic=request.topic,
            language=request.language,
        )

        duration_ms = round((time.time() - start_time) * 1000, 2)

        log_query(
            logger=logger,
            query=request.query,
            user_id=request.user_id,
            results_count=result['results_count'],
            duration_ms=duration_ms,
            filters={'team_id': request.team_id},
        )

        return {
            "query": request.query,
            "answer": result['answer'],                  # LLM-generated summary
            "results_count": result['results_count'],
            "results": result['results'],                # cited chunks
            "language": result['language'],
            "retrieval": result['retrieval'],            # search_type, chunks, model
        }

    except Exception as e:
        logger.error(f"Query failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/retrieve/stream")
async def query_knowledge_base_stream(request: QueryRequest):
    """
    Streaming version of /api/retrieve using Server-Sent Events.

    Sends progress stages in real-time, then streams the answer word-by-word
    so the user sees immediate feedback instead of waiting 5-15s for a full response.

    Event types:
      stage    — progress update (detecting language, searching, generating...)
      chunk    — a piece of the answer text (streamed word-by-word)
      sources  — the citations/source documents (sent once at end)
      done     — final signal with metadata (language, retrieval info)
      error    — if something fails
    """
    import asyncio

    async def event_stream():
        try:
            start_time_s = time.time()

            # Stage 1: Detecting language
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'detecting_language', 'message': 'Detecting language...'})}\n\n"
            await asyncio.sleep(0)

            from services.translation_service import translation_service, SUPPORTED_LANGUAGES
            from utils.greeting_detector import greeting_detector
            from services.conversational_service import conversational_service

            detected_lang = translation_service.detect_language(request.query)
            lang_name = SUPPORTED_LANGUAGES.get(detected_lang, 'Unknown')

            yield f"data: {json.dumps({'type': 'stage', 'stage': 'language_detected', 'message': f'Language: {lang_name}', 'language': detected_lang})}\n\n"
            await asyncio.sleep(0)

            # Stage 2: Check if it's a greeting/conversational message
            is_greeting, greeting_type = greeting_detector.is_greeting(request.query, detected_lang)

            if is_greeting:
                # Handle as conversational message - skip KB search
                yield f"data: {json.dumps({'type': 'stage', 'stage': 'generating', 'message': 'Generating response...'})}\n\n"
                await asyncio.sleep(0)

                # Generate conversational response
                answer_parts = []
                for text_chunk in conversational_service.generate_response(
                    query=request.query,
                    greeting_type=greeting_type,
                    language=detected_lang
                ):
                    answer_parts.append(text_chunk)
                    yield f"data: {json.dumps({'type': 'chunk', 'text': text_chunk})}\n\n"
                    await asyncio.sleep(0.03)

                answer = ''.join(answer_parts)
                duration_ms = round((time.time() - start_time_s) * 1000, 2)

                # Send done event (no citations for greetings)
                yield f"data: {json.dumps({'type': 'done', 'language': {'detected': detected_lang, 'name': lang_name}, 'retrieval': {}, 'duration_ms': duration_ms}, default=str)}\n\n"

                # Save to chat session if session_id provided
                if request.session_id and request.user_id:
                    try:
                        db = SessionLocal()
                        chat_session_service.add_message(
                            db=db,
                            user_id=request.user_id,
                            session_id=request.session_id,
                            user_text=request.query,
                            assistant_answer=answer,
                            citations=[],
                            language={'detected': detected_lang, 'name': lang_name},
                            duration_ms=duration_ms,
                        )
                        db.close()
                    except Exception as save_err:
                        logger.warning(f"Failed to save greeting message to session: {save_err}")

                return  # Exit early - no KB search needed

            # Stage 3: Translating if needed (only for non-greetings)
            english_query = request.query
            if not translation_service.is_english(detected_lang):
                yield f"data: {json.dumps({'type': 'stage', 'stage': 'translating', 'message': f'Translating {lang_name} → English...', 'original': request.query, 'from_lang': lang_name})}\n\n"
                await asyncio.sleep(0)
                english_query = translation_service.to_english(request.query, detected_lang)
                yield f"data: {json.dumps({'type': 'stage', 'stage': 'translated', 'message': f'Translated: \"{english_query}\"', 'translated_query': english_query, 'from_lang': lang_name, 'to_lang': 'English'})}\n\n"
                await asyncio.sleep(0)

            # Stage 4: Searching knowledge base
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'searching', 'message': 'Searching knowledge base...'})}\n\n"
            await asyncio.sleep(0)

            # Stage 5: Generating answer
            yield f"data: {json.dumps({'type': 'stage', 'stage': 'generating', 'message': 'Generating answer from sources...'})}\n\n"
            await asyncio.sleep(0)

            # Run the actual query (blocking but sent as one stage)
            result = kb_query_service.query(
                query=request.query,
                user_id=request.user_id,
                team_id=request.team_id,
                max_results=request.max_results,
                department=request.department,
                doc_type=request.doc_type,
                topic=request.topic,
                language=request.language,
            )

            # Stage 6: Stream the answer word-by-word
            answer = result.get('answer', '')
            if answer:
                yield f"data: {json.dumps({'type': 'stage', 'stage': 'streaming', 'message': 'Answer ready'})}\n\n"
                await asyncio.sleep(0)

                # Stream in chunks of ~3-5 words for smooth rendering
                words = answer.split(' ')
                buffer = []
                for i, word in enumerate(words):
                    buffer.append(word)
                    if len(buffer) >= 4 or i == len(words) - 1:
                        chunk_text = ' '.join(buffer) + (' ' if i < len(words) - 1 else '')
                        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk_text})}\n\n"
                        buffer = []
                        await asyncio.sleep(0.03)

            # Stage 7: Send sources (only fields the frontend needs)
            raw_citations = result.get('results', [])
            if raw_citations:
                clean_citations = []
                for c in raw_citations:
                    clean_citations.append({
                        'source_file': c.get('source_file', ''),
                        's3_uri': c.get('s3_uri', ''),
                        'score': c.get('score', 0),
                        'content': {'text': (c.get('content', {}).get('text', '') or '')[:500]},
                    })
                yield f"data: {json.dumps({'type': 'sources', 'citations': clean_citations})}\n\n"
                await asyncio.sleep(0)

            # Stage 8: Done with metadata
            duration_ms = round((time.time() - start_time_s) * 1000, 2)
            yield f"data: {json.dumps({'type': 'done', 'language': result.get('language', {}), 'retrieval': result.get('retrieval', {}), 'duration_ms': duration_ms}, default=str)}\n\n"

            # Auto-save to chat session if session_id provided
            if request.session_id and request.user_id:
                try:
                    db = SessionLocal()
                    chat_session_service.add_message(
                        db=db,
                        user_id=request.user_id,
                        session_id=request.session_id,
                        user_text=request.query,
                        assistant_answer=answer,
                        citations=raw_citations,
                        language=result.get('language'),
                        duration_ms=duration_ms,
                    )
                    db.close()
                except Exception as save_err:
                    logger.warning(f"Failed to save message to session: {save_err}")

        except Exception as e:
            logger.error(f"Stream query failed: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Chat Sessions (PostgreSQL RDS)
# ============================================================================

class CreateSessionRequest(BaseModel):
    user_id: str
    first_message: str = ""

class AddMessageRequest(BaseModel):
    user_id: str
    user_text: str
    assistant_answer: str
    citations: Optional[List[Dict[str, Any]]] = None
    language: Optional[Dict[str, Any]] = None
    duration_ms: float = 0

class UpdateTitleRequest(BaseModel):
    user_id: str
    title: str


@app.post("/api/chat/sessions")
async def create_chat_session(request: CreateSessionRequest):
    """Create a new chat session."""
    db = SessionLocal()
    try:
        session = chat_session_service.create_session(
            db=db, user_id=request.user_id, first_message=request.first_message
        )
        return session
    finally:
        db.close()


@app.get("/api/chat/sessions")
async def list_chat_sessions(user_id: str = Query(...), limit: int = Query(50, le=100)):
    """List all chat sessions for a user."""
    db = SessionLocal()
    try:
        sessions = chat_session_service.list_sessions(db=db, user_id=user_id, limit=limit)
        return {"sessions": sessions, "count": len(sessions)}
    finally:
        db.close()


@app.get("/api/chat/sessions/{session_id}")
async def get_chat_session(session_id: str, user_id: str = Query(...)):
    """Get a session with all messages."""
    db = SessionLocal()
    try:
        session = chat_session_service.get_session(db=db, user_id=user_id, session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    finally:
        db.close()


@app.post("/api/chat/sessions/{session_id}/messages")
async def add_chat_message(session_id: str, request: AddMessageRequest):
    """Add a user+assistant message pair to a session."""
    db = SessionLocal()
    try:
        result = chat_session_service.add_message(
            db=db,
            user_id=request.user_id,
            session_id=session_id,
            user_text=request.user_text,
            assistant_answer=request.assistant_answer,
            citations=request.citations,
            language=request.language,
            duration_ms=request.duration_ms,
        )
        if not result:
            raise HTTPException(status_code=404, detail="Session not found")
        return result
    finally:
        db.close()


@app.put("/api/chat/sessions/{session_id}/title")
async def update_session_title(session_id: str, request: UpdateTitleRequest):
    """Rename a session."""
    db = SessionLocal()
    try:
        success = chat_session_service.update_title(
            db=db, user_id=request.user_id, session_id=session_id, title=request.title
        )
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Title updated"}
    finally:
        db.close()


@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str, user_id: str = Query(...)):
    """Delete a session and all its messages."""
    db = SessionLocal()
    try:
        success = chat_session_service.delete_session(db=db, user_id=user_id, session_id=session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session deleted"}
    finally:
        db.close()


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
# Scheduled Sync API
# ============================================================================

@app.post("/api/sync/configs")
async def create_sync_config(body: SyncConfigCreate, db=Depends(get_db)):
    """Create a new scheduled sync configuration."""
    try:
        from services.sync_service import sync_service
        config = sync_service.create_config(
            db=db,
            user_id=body.user_id,
            source_type=body.source_type,
            display_name=body.display_name,
            credentials=body.credentials,
            schedule=body.schedule,
            space_or_path=body.space_or_path,
        )
        return {"status": "created", "config": config}
    except Exception as e:
        logger.error(f"create_sync_config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync/configs")
async def list_sync_configs(user_id: str = Query(...), db=Depends(get_db)):
    """List all sync configurations for a user."""
    try:
        from services.sync_service import sync_service
        configs = sync_service.list_configs(db=db, user_id=user_id)
        return {"configs": configs, "count": len(configs)}
    except Exception as e:
        logger.error(f"list_sync_configs failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync/configs/{config_id}")
async def get_sync_config(config_id: str, user_id: str = Query(...), db=Depends(get_db)):
    """Get a single sync configuration (credentials not returned)."""
    try:
        from services.sync_service import sync_service
        config = sync_service.get_config(db=db, config_id=config_id, user_id=user_id)
        if not config:
            raise HTTPException(status_code=404, detail="Sync config not found")
        return {"config": sync_service._config_to_dict(config)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_sync_config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sync/configs/{config_id}")
async def delete_sync_config(config_id: str, user_id: str = Query(...), db=Depends(get_db)):
    """Delete a sync configuration and all its tracker rows."""
    try:
        from services.sync_service import sync_service
        deleted = sync_service.delete_config(db=db, config_id=config_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Sync config not found")
        return {"status": "deleted", "config_id": config_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"delete_sync_config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/sync/configs/{config_id}/pause")
async def pause_sync_config(config_id: str, user_id: str = Query(...), db=Depends(get_db)):
    """Pause a sync configuration so it is skipped by the scheduler."""
    try:
        from services.sync_service import sync_service
        ok = sync_service.pause_config(db=db, config_id=config_id, user_id=user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Sync config not found")
        return {"status": "paused", "config_id": config_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"pause_sync_config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/sync/configs/{config_id}/resume")
async def resume_sync_config(config_id: str, user_id: str = Query(...), db=Depends(get_db)):
    """Resume a paused sync configuration and schedule the next run."""
    try:
        from services.sync_service import sync_service
        ok = sync_service.resume_config(db=db, config_id=config_id, user_id=user_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Sync config not found")
        return {"status": "resumed", "config_id": config_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"resume_sync_config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync/configs/{config_id}/run")
async def trigger_sync_config(
    config_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Query(...),
    db=Depends(get_db),
):
    """Trigger an immediate sync for a configuration (runs in background)."""
    try:
        from services.sync_service import sync_service
        config = sync_service.get_config(db=db, config_id=config_id, user_id=user_id)
        if not config:
            raise HTTPException(status_code=404, detail="Sync config not found")

        def _run_in_background():
            from services.database import SessionLocal as _SessionLocal
            bg_db = _SessionLocal()
            try:
                bg_config = sync_service.get_config(bg_db, config_id, user_id)
                if bg_config:
                    sync_service.run_sync(bg_db, bg_config, trigger='manual')
            except Exception as e:
                logger.error(f"Background sync failed for config {config_id}: {e}")
            finally:
                bg_db.close()

        background_tasks.add_task(_run_in_background)
        return {"status": "accepted", "config_id": config_id, "message": "Sync started in background"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"trigger_sync_config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync/configs/{config_id}/files")
async def get_synced_files(
    config_id: str,
    user_id: str = Query(...),
    limit: int = Query(100, le=500),
    db=Depends(get_db),
):
    """List all files synced by a config (from sync_tracker)."""
    try:
        from services.sync_service import sync_service
        config = sync_service.get_config(db=db, config_id=config_id, user_id=user_id)
        if not config:
            raise HTTPException(status_code=404, detail="Sync config not found")
        files = sync_service.get_tracker_history(db=db, config_id=config_id, user_id=user_id, limit=limit)
        return {"config_id": config_id, "files": files, "count": len(files)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_synced_files failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync/configs/{config_id}/history")
async def get_sync_history(
    config_id: str,
    user_id: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    """List recent run-level history for a sync configuration."""
    try:
        from services.sync_service import sync_service
        config = sync_service.get_config(db=db, config_id=config_id, user_id=user_id)
        if not config:
            raise HTTPException(status_code=404, detail="Sync config not found")
        runs = sync_service.get_run_history(db=db, config_id=config_id, user_id=user_id, limit=limit)
        return {"config_id": config_id, "history": runs, "count": len(runs)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_sync_history failed: {e}")
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


# ============================================================================
# Sync Source Endpoints
# ============================================================================

from services.sync_source_service import sync_source_service
from services.sync_engine import run_sync
from services.database import init_db

# Initialize database tables on startup
@app.on_event("startup")
async def init_database():
    """Create sync_sources and sync_history tables if they don't exist."""
    try:
        init_db()
    except Exception as e:
        logger.warning(f"Database init skipped (set DATABASE_URL in .env): {e}")


class CreateSyncSourceRequest(BaseModel):
    source_type: str          # 's3', 'google_drive', 'confluence'
    name: str
    credentials: Dict[str, Any]
    target_path: str = ""
    schedule_cron: str = "0 */6 * * *"


class UpdateSyncSourceRequest(BaseModel):
    name: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    target_path: Optional[str] = None
    schedule_cron: Optional[str] = None
    enabled: Optional[bool] = None


@app.get("/api/sync-sources")
async def list_sync_sources(user_id: str = Query(...)):
    """List all sync sources for a user."""
    try:
        sources = sync_source_service.list_for_user(user_id)
        return {"count": len(sources), "sources": sources}
    except Exception as e:
        logger.error(f"Failed to list sync sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync-sources")
async def create_sync_source(request: CreateSyncSourceRequest, user_id: str = Query(...)):
    """Create a new sync source configuration."""
    try:
        source = sync_source_service.create(
            user_id=user_id,
            source_type=request.source_type,
            name=request.name,
            credentials=request.credentials,
            target_path=request.target_path,
            schedule_cron=request.schedule_cron,
        )

        # Schedule the sync job if scheduler is running
        if scheduler and scheduler.running:
            from apscheduler.triggers.cron import CronTrigger
            scheduler.add_job(
                run_sync,
                trigger=CronTrigger.from_crontab(request.schedule_cron),
                id=f"sync_{source['id']}",
                args=[source["id"]],
                replace_existing=True,
            )
            logger.info(f"Scheduled sync job for source: {source['id']}")

        return source
    except Exception as e:
        logger.error(f"Failed to create sync source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/sync-sources/{source_id}")
async def update_sync_source(source_id: str, request: UpdateSyncSourceRequest):
    """Update a sync source configuration."""
    try:
        updates = {k: v for k, v in request.dict().items() if v is not None}
        result = sync_source_service.update(source_id, **updates)
        if not result:
            raise HTTPException(status_code=404, detail="Sync source not found")

        # Reschedule if cron changed
        if request.schedule_cron and scheduler and scheduler.running:
            from apscheduler.triggers.cron import CronTrigger
            try:
                scheduler.reschedule_job(
                    f"sync_{source_id}",
                    trigger=CronTrigger.from_crontab(request.schedule_cron),
                )
            except Exception:
                # Job might not exist yet
                scheduler.add_job(
                    run_sync,
                    trigger=CronTrigger.from_crontab(request.schedule_cron),
                    id=f"sync_{source_id}",
                    args=[source_id],
                    replace_existing=True,
                )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update sync source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sync-sources/{source_id}")
async def delete_sync_source(source_id: str):
    """Delete a sync source and remove its scheduled job."""
    try:
        success = sync_source_service.delete(source_id)
        if not success:
            raise HTTPException(status_code=404, detail="Sync source not found")

        # Remove scheduled job
        if scheduler and scheduler.running:
            try:
                scheduler.remove_job(f"sync_{source_id}")
            except Exception:
                pass

        return {"message": "Sync source deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete sync source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync-sources/{source_id}/test")
async def test_sync_source(source_id: str):
    """Test connection to a sync source (validates credentials)."""
    try:
        source = sync_source_service.get_with_credentials(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Sync source not found")

        from services.connectors import get_connector
        connector = get_connector(source["source_type"])
        result = connector.test_connection(source["credentials"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test sync source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync-sources/{source_id}/sync-now")
async def trigger_sync_now(source_id: str, background_tasks: BackgroundTasks):
    """Manually trigger an immediate sync for a source."""
    try:
        source = sync_source_service.get(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Sync source not found")

        # Run sync in background
        background_tasks.add_task(run_sync, source_id)

        return {
            "message": f"Sync triggered for '{source['name']}'",
            "source_id": source_id,
            "status": "running",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sync-sources/{source_id}/history")
async def get_sync_history(source_id: str, limit: int = Query(20, le=100)):
    """Get sync run history for a source."""
    try:
        history = sync_source_service.get_history(source_id, limit=limit)
        return {"count": len(history), "history": history}
    except Exception as e:
        logger.error(f"Failed to get sync history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Register all enabled sync sources on startup ──
@app.on_event("startup")
async def schedule_sync_sources():
    """Load all enabled sync sources and schedule their cron jobs."""
    if not scheduler or USE_EVENTBRIDGE:
        return

    try:
        from apscheduler.triggers.cron import CronTrigger
        sources = sync_source_service.get_all_enabled()
        for source in sources:
            scheduler.add_job(
                run_sync,
                trigger=CronTrigger.from_crontab(source["schedule_cron"]),
                id=f"sync_{source['id']}",
                args=[source["id"]],
                replace_existing=True,
            )
        logger.info(f"Scheduled {len(sources)} sync source(s) from database")
    except Exception as e:
        logger.warning(f"Could not load sync sources (DB may not be configured): {e}")


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
