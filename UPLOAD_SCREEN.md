# Upload Screen — Document Ingestion

## Overview

The Upload screen (`frontend/src/pages/UploadNew.jsx`) is the central hub for ingesting documents into the Bedrock Knowledge Base. It supports four source types:

| Source | Type | How it works |
|--------|------|-------------|
| Local Upload | One-time | Drag & drop or browse, uploads directly |
| Google Drive | Scheduled sync | Browses logged-in user's Drive, syncs a folder |
| AWS S3 | Scheduled sync | Manual creds entry, syncs a bucket/prefix |
| Confluence | Scheduled sync | Connect with API token, syncs a space |

The page uses a **vertical source tab sidebar** on the left and a **content card** on the right.

---

## Page Layout

```
┌──────────────────────────────────────────────────────────┐
│  Header: "Document Ingestion"                             │
│  Subtitle: Upload or sync documents to the KB             │
├──────────────┬───────────────────────────────────────────┤
│  Source Tabs │  Content Card                             │
│              │  ┌─────────────────────────────────────┐  │
│  ● Local     │  │ Tab header (source icon + label)    │  │
│    Upload    │  ├─────────────────────────────────────┤  │
│  ○ Google    │  │                                      │  │
│    Drive     │  │  Tab-specific UI                     │  │
│  ○ AWS S3    │  │                                      │  │
│  ○ Confluence│  └─────────────────────────────────────┘  │
└──────────────┴───────────────────────────────────────────┘
```

---

## Source 1: Local Upload

### What it does
Direct one-time file upload from the user's computer to S3, followed by automatic KB ingestion.

### User flow
1. Drag & drop a file or click **Browse Files**
2. File is validated client-side (size ≤ 500 MB, supported extension)
3. Click **Upload & Ingest**
4. File is `POST`ed to `/api/upload/direct` as multipart/form-data
5. Backend:
   - Reads file content
   - Extracts metadata (author, title, dates from PDF/DOCX/XLSX EXIF etc.)
   - Uploads to central S3 at key `docs/{filename}` with metadata headers
   - Records ETag in `ingestion_tracker` (dedup)
   - Triggers Bedrock KB ingestion as a background task
6. Frontend polls KB ingestion status every 8 seconds

### Upload progress
Real-time percentage progress bar via `onUploadProgress` callback in axios.

### KB Ingestion Status card
Appears after successful upload and polls `/api/kb/sync/latest`:

| Status | Behaviour |
|--------|-----------|
| `PENDING` | Waiting for job to be created |
| `STARTING` | Job accepted by Bedrock |
| `IN_PROGRESS` | Actively chunking and embedding |
| `COMPLETE` | Document indexed and queryable |
| `FAILED` | Ingestion failed |
| `STOPPED` | Job stopped manually |

Shows: elapsed time counter, indeterminate progress bar while running, final stats (Scanned / Indexed / Failed), Bedrock job ID.

### Supported formats
PDF · DOC · DOCX · TXT · HTML · XLSX · XLS · CSV · PNG · JPG · JPEG · GIF · WEBP · MP4 · MP3 · WAV

**Max file size:** 500 MB

### S3 key pattern
```
docs/{filename}
```

---

## Source 2: Google Drive

### What it does
Schedules automatic recurring syncs from a Google Drive folder. Uses the OAuth token from the user's existing login session — no separate credential entry needed.

### View toggle
Two modes at the top of the tab:

#### My Drive
- Automatically loads the user's Drive on tab open
- Shared Drives dropdown (if user has team drive access)
- Breadcrumb navigation for folder traversal
- **Click a folder row** → selects it (highlighted blue, "Selected" badge)
- **"Open" button** → navigates inside the folder (browser mode)
- **"Sync current folder" button** → selects the breadcrumb-current folder
- Files in the folder are shown with a count indicator (selecting a folder syncs all files inside)

#### Shared with me
- Lists all folders other Google accounts have shared with the logged-in user
- Shows: folder name, shared-by display name, owner email
- Click any row to select it for sync
- Refresh button to reload

### Sync config setup (once folder selected)
A blue-bordered card appears with:
- **Sync name** — auto-filled from folder name, editable
- **Schedule picker** — choose frequency
- **"Schedule Sync"** button

### What gets stored as credentials
```json
{
  "access_token": "ya29...",
  "refresh_token": "1//...",
  "drive_id": null
}
```
`client_id` and `client_secret` are auto-filled from app `.env` — user never enters these.

### How sync runs (backend)
1. APScheduler picks up due configs
2. If `refresh_token` present → exchanges it for a fresh `access_token` via Google OAuth and persists the new token back to the config
3. Calls `google_drive_service.list_files(access_token, drive_id)` — lists all files (up to 1000)
4. For each file:
   - Skips folders
   - Checks `modifiedTime` against `sync_tracker` — skips if unchanged
   - Downloads file content via Drive API (Google native formats exported as PDF)
   - Uploads to central S3 at `docs/{filename}` with metadata `{source: 'gdrive', gdrive_file_id, sync_config_id}`
   - Records in `sync_tracker`
5. Triggers Bedrock KB ingestion if any files synced
6. Updates `last_run_at`, `files_synced`, `status` on the config

### Dedup mechanism
Uses `modifiedTime` from Drive API as fingerprint. If `modifiedTime` hasn't changed → file skipped.

### S3 key pattern
```
docs/{filename}
```
(currently uses the same `docs/` prefix as direct uploads — handled by ETag dedup in tracker)

---

## Source 3: AWS S3

### What it does
Syncs files from an **external** S3 bucket into the centralized KB S3 bucket on a schedule. User manually enters AWS credentials.

### Credential fields

| Field | Required | Notes |
|-------|----------|-------|
| Sync Name | ✅ | Label for this sync config |
| S3 Bucket | ✅ | Exact bucket name — no `s3://` prefix |
| Prefix / Folder Path | ❌ | e.g. `documents/hr/` — blank syncs entire bucket |
| AWS Access Key ID | ✅ | IAM key with `s3:GetObject` + `s3:ListObjectsV2` permissions |
| AWS Secret Access Key | ✅ | Matching secret key |
| AWS Session Token | ❌ | For SSO / temporary credentials (e.g. from `aws sso login`) |
| Region | ❌ | Defaults to `ap-south-1` |

### How sync runs (backend)
1. APScheduler picks up due configs
2. Reads encrypted credentials from DB, decrypts with Fernet key
3. Creates a boto3 S3 client with user-provided credentials (supports session token)
4. Paginates `list_objects_v2` on the source bucket under the configured prefix
5. For each object:
   - Skips "folder" placeholder keys (ending in `/`)
   - Checks ETag against `sync_tracker` — skips if unchanged
   - Downloads via `get_object`
   - Uploads to central S3 at `docs/{original_filename}` with metadata `{source: 's3', sync_config_id, source_bucket, source_key}`
   - Records ETag in `sync_tracker`
6. Triggers Bedrock KB ingestion if any files synced

### Dedup mechanism
Uses the **S3 ETag** (MD5 of object content for single-part uploads) as fingerprint. Unchanged files are skipped efficiently.

### Error scenarios
| Error | Cause |
|-------|-------|
| `NoSuchBucket` | Bucket name wrong or doesn't exist in that region |
| `InvalidAccessKeyId` | Access Key ID is wrong or expired |
| `AccessDenied` | IAM permissions insufficient |
| `InvalidClientTokenId` | Session token expired — refresh SSO credentials |

### S3 key pattern
```
docs/{filename}
```

---

## Source 4: Confluence

### What it does
Syncs pages from a Confluence Cloud (or Server/DC) space into the KB on a schedule.

### Step-by-step flow

#### Step 1 — Enter credentials

| Field | Required | Notes |
|-------|----------|-------|
| Sync Name | ✅ | Label for this sync config |
| Confluence Site URL | ✅ | e.g. `yourcompany.atlassian.net` — no `/wiki` suffix, no `https://` |
| Atlassian Email | ✅ | Email used to log into Atlassian |
| API Token | ✅ | From [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens) |

#### Step 2 — Connect & List Spaces
- Click **"Connect & List Spaces"**
- Backend calls `POST /api/sync/confluence/list-spaces`
- Tries Cloud API v2 (`/wiki/api/v2/spaces`) first, falls back to legacy REST API (`/wiki/rest/api/space`) for Server/DC
- Returns list of accessible spaces with key and name
- Select the space to sync

#### Step 3 — Set schedule → Save

### How sync runs (backend)
1. APScheduler picks up due configs
2. Decrypts credentials
3. Calls `confluence_service` to list all pages in the space via REST API
4. For each page:
   - Checks `version.number` against `sync_tracker` — skips if unchanged
   - Downloads page body as HTML via `/rest/api/content/{id}?expand=body.storage`
   - Wraps in full HTML document with page title as `<h1>`
   - Uploads to central S3 as `.html` file with metadata `{source: 'confluence', sync_config_id, space_key, page_id}`
   - Records version number in `sync_tracker`
5. Triggers Bedrock KB ingestion if any pages synced

### Dedup mechanism
Uses Confluence **page version number** as fingerprint. Only syncs pages that have been updated since the last run.

### S3 key pattern
```
docs/{page_title}.html
```

---

## Sync Schedule Options

| Value | Label | Interval | Use case |
|-------|-------|----------|----------|
| `2m` | Every 2 min | 2 minutes | Testing only |
| `5m` | Every 5 min | 5 minutes | Testing only |
| `hourly` | Every hour | 1 hour | High-frequency updates |
| `6h` | Every 6h | 6 hours | Active content |
| `12h` | Every 12h | 12 hours | Moderate updates |
| `daily` | Daily | 24 hours | Most common |
| `weekly` | Weekly | 7 days | Slow-changing content |

**Scheduler:** APScheduler runs every **1 minute** polling for due configs. Due = configs where `next_run_at <= now`.

---

## Active Syncs — Per-Tab History

After saving any sync config, an **Active Syncs** section appears below the form showing all configs for that source type.

### Sync Config Card

| Field shown | Description |
|-------------|-------------|
| Name | Display name given at creation |
| Status badge | Active (green) / Paused (grey) / Error (red) |
| Schedule | Human-readable frequency |
| Last run | Formatted timestamp or "Never" |
| Files synced | Total cumulative count |
| Last error | Red text showing most recent failure reason |

### Action Buttons

| Button | Icon | Action |
|--------|------|--------|
| Run Now | ⚡ Zap | Triggers an immediate manual sync in background |
| History | 📊 Activity | Toggles run history panel inline |
| Pause | ⏸ | Pauses scheduled execution |
| Resume | ▶ | Resumes a paused config, recomputes `next_run_at` |
| Delete | 🗑 | Permanently deletes config and all history |

### Run History Panel

Clicking **Activity** expands run history inline under the card:

| Column | Description |
|--------|-------------|
| Status badge | Running (blue) / Success (green) / Partial (yellow) / Failed (red) / Skipped (grey) |
| Start timestamp | `DD Mon HH:MM:SS` |
| Error | Truncated error message (red), if any |
| Files synced | `↑ N synced` count |
| Duration | Run time in seconds |
| Trigger type | `👆 manual` or `⏰ auto` |

History refreshes automatically after a manual run (4-second delay to allow the run to record).

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `sync_configs` | One row per sync source (encrypted creds, schedule, last_run_at, status) |
| `sync_tracker` | One row per synced file/page (fingerprint for dedup, per-file status) |
| `sync_runs` | One row per execution (started_at, completed_at, status, file counts, trigger) |

### sync_configs columns
`id, user_id, source_type, display_name, credentials_enc (Fernet), schedule, space_or_path, status, last_run_at, last_error, next_run_at, files_synced, created_at`

### sync_tracker columns
`id, sync_config_id, user_id, source_file_id, fingerprint, s3_key, status, last_synced_at`

### sync_runs columns
`id, sync_config_id, user_id, started_at, completed_at, status, files_found, files_synced, files_skipped, files_failed, error, trigger`

---

## Credentials Security

All credentials are encrypted using **Fernet symmetric encryption** (AES-128-CBC + HMAC-SHA256) before storage in PostgreSQL. The encryption key (`ENCRYPTION_KEY`) is set in `.env` and must be stable across restarts — losing the key makes stored credentials unreadable.

Generate a key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/upload/direct` | Direct file upload + S3 store |
| `GET` | `/api/kb/sync/latest` | Latest KB ingestion job status |
| `GET` | `/api/upload/sync-status/{job_id}` | Poll specific KB ingestion job |
| `GET` | `/api/google-drive/shared-drives` | List team/shared drives |
| `GET` | `/api/google-drive/browse` | Browse Drive folder contents |
| `GET` | `/api/google-drive/shared-with-me` | Folders shared by other accounts |
| `POST` | `/api/sync/confluence/list-spaces` | Validate Confluence creds + list spaces |
| `GET` | `/api/sync/configs` | List all sync configs for user |
| `POST` | `/api/sync/configs` | Create new sync config |
| `PUT` | `/api/sync/configs/{id}/pause` | Pause a sync |
| `PUT` | `/api/sync/configs/{id}/resume` | Resume a paused sync |
| `DELETE` | `/api/sync/configs/{id}` | Delete sync config + history |
| `POST` | `/api/sync/configs/{id}/run` | Trigger manual run |
| `GET` | `/api/sync/configs/{id}/history` | Get run-level history |

---

## Deduplication Strategy

All synced files land in the **centralized S3 bucket** (`dialog-telecom`). Dedup is handled by two layers:

### Layer 1 — sync_tracker (per-file fingerprint)
Each source uses a different fingerprint:

| Source | Fingerprint used |
|--------|-----------------|
| Google Drive | `modifiedTime` from Drive API |
| Confluence | Page `version.number` |
| AWS S3 | Object `ETag` (MD5 of content) |

Before downloading a file, the sync service checks if the fingerprint matches what's stored in `sync_tracker`. If it matches → skip. If different → re-download and re-ingest.

### Layer 2 — ingestion_tracker (S3 ETag)
After uploading to the central S3 bucket, the actual S3 ETag is recorded. The incremental KB sync job (`scheduled_incremental_sync`) also uses this to avoid re-ingesting unchanged objects.

This double-layer means:
- Same content uploaded twice → skipped at S3 level
- Drive file edited → `modifiedTime` differs → re-synced
- Confluence page edited → version number differs → re-synced
- S3 object replaced with same content → same ETag → skipped

---

## S3 Key Structure

| Source | S3 key |
|--------|--------|
| Local Upload | `docs/{filename}` |
| Google Drive sync | `docs/{filename}` |
| AWS S3 sync | `docs/{filename}` |
| Confluence sync | `docs/{page_title}.html` |

All sources use the `docs/` prefix. The `sync_tracker` records the original `source_file_id` (Drive file ID / Confluence page ID / S3 key) mapped to the destination S3 key.
