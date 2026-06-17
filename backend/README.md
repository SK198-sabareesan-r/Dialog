# Knowledge Base Backend - Complete Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Setup & Installation](#setup--installation)
5. [Configuration](#configuration)
6. [Core Services](#core-services)
7. [API Endpoints](#api-endpoints)
8. [File Processing Flow](#file-processing-flow)
9. [Multi-Language Support](#multi-language-support)
10. [Logging & Monitoring](#logging--monitoring)
11. [Testing](#testing)
12. [Deployment](#deployment)

---

## Overview

This backend system provides a comprehensive knowledge base solution with multi-format document ingestion, automatic metadata extraction, and intelligent query capabilities. It leverages AWS Bedrock Knowledge Base for fully managed document processing, chunking, embeddings, and vector storage.

### Key Features

✅ **Multi-Format Support**: PDF, DOCX, PPTX, Excel, Images (JPEG/PNG), Videos (MP4/AVI/MOV/MKV/WebM), Audio (MP3/WAV)  
✅ **Automatic Metadata Extraction**: Extracts author, date, EXIF data, duration, and more from uploaded files  
✅ **Multi-Language Support**: English, Sinhala, Tamil with automatic translation  
✅ **Hybrid Search**: Combines vector similarity and keyword (BM25) search  
✅ **AI-Generated Answers**: Claude Sonnet 4.5 generates contextual answers with citations  
✅ **Access Control**: User-level and team-level document filtering  
✅ **Google Drive Integration**: Import documents directly from Google Drive (personal and Shared Drives)  
✅ **Incremental Sync**: Scheduled background jobs to sync new/changed files  
✅ **Structured Logging**: JSON-formatted logs for monitoring and debugging  
✅ **File Repository Service**: Import files from external S3 buckets

### Simplified Architecture

This architecture uses Bedrock Knowledge Base's fully managed capabilities, eliminating the need for:

- ❌ Lambda functions
- ❌ Step Functions
- ❌ SQS queues
- ❌ Self-managed OpenSearch
- ❌ Custom chunking logic
- ❌ Custom embedding pipelines

**Bedrock Knowledge Base handles all of this internally!**

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                              │
│  • Frontend (React)                                               │
│  • Google Drive Picker                                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (Port 8001)                  │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │  Upload Service │  │  Google Drive    │  │  Query Service  │ │
│  │  • S3 Upload    │  │  Service         │  │  • Language     │ │
│  │  • Metadata     │  │  • OAuth2        │  │    Detection    │ │
│  │  • Tracker      │  │  • File Import   │  │  • Translation  │ │
│  └─────────────────┘  └──────────────────┘  └─────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           Metadata Extractor Service                        │ │
│  │  • PDF metadata (author, title, keywords)                   │ │
│  │  • DOCX metadata (author, company, dates)                   │ │
│  │  • Image EXIF (camera, location, timestamp)                 │ │
│  │  • Video metadata (duration, resolution, codec)             │ │
│  │  • Audio metadata (duration, bitrate, tags)                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           Ingestion Tracker Service                         │ │
│  │  • Tracks processed files (S3 key, ETag, timestamp)         │ │
│  │  • Prevents duplicate processing                            │ │
│  │  • Enables incremental sync                                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           Translation Service                               │ │
│  │  • Amazon Translate integration                             │ │
│  │  • Amazon Comprehend for language detection                 │ │
│  │  • Markdown-aware translation (preserves formatting)        │ │
│  │  • Languages: English, Sinhala, Tamil                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │           File Repository Service                           │ │
│  │  • Import from external S3 buckets                          │ │
│  │  • Copy files to KB bucket with metadata                    │ │
│  │  • Support for bulk imports                                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                         AWS LAYER                                 │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Amazon S3 (Raw Bucket)                                   │   │
│  │  • Stores uploaded files with metadata                    │   │
│  │  • Metadata stored as S3 object custom metadata           │   │
│  │  • Folder structure: docs/{user_id}/{timestamp}_{filename}│   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │ Auto-sync                              │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Amazon Bedrock Knowledge Base                            │   │
│  │  ┌────────────────────────────────────────────────────┐   │   │
│  │  │  Data Source (S3)                                   │   │   │
│  │  │  • Syncs files from S3 bucket                       │   │   │
│  │  │  • Incremental or full sync                         │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  │  ┌────────────────────────────────────────────────────┐   │   │
│  │  │  Built-in Data Automation (BDA)                    │   │   │
│  │  │  • PDF parsing                                      │   │   │
│  │  │  • Image OCR                                        │   │   │
│  │  │  • Video transcription                              │   │   │
│  │  │  • Audio transcription                              │   │   │
│  │  │  • Document structure preservation                  │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  │  ┌────────────────────────────────────────────────────┐   │   │
│  │  │  Chunking Engine                                    │   │   │
│  │  │  • Semantic chunking                                │   │   │
│  │  │  • Context-aware splitting                          │   │   │
│  │  │  • Configurable chunk size and overlap              │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  │  ┌────────────────────────────────────────────────────┐   │   │
│  │  │  Embedding Model                                    │   │   │
│  │  │  • Amazon Titan Embed Text v1                       │   │   │
│  │  │  • Generates vector embeddings                      │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  │  ┌────────────────────────────────────────────────────┐   │   │
│  │  │  Vector Store (Managed)                             │   │   │
│  │  │  • Stores embeddings                                │   │   │
│  │  │  • Hybrid search (vector + BM25)                    │   │   │
│  │  │  • Metadata filtering                               │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  │  ┌────────────────────────────────────────────────────┐   │   │
│  │  │  Generation Model (Claude Sonnet 4.5)               │   │   │
│  │  │  • Retrieve-and-generate                            │   │   │
│  │  │  • Contextual answer generation                     │   │   │
│  │  │  • Citation extraction                              │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Amazon Translate & Comprehend                            │   │
│  │  • Language detection (Comprehend)                        │   │
│  │  • Translation (Translate)                                │   │
│  │  • Supports: English, Sinhala, Tamil                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Upload**: User uploads file → FastAPI receives it → Metadata extracted → File stored in S3 with metadata
2. **Ingestion**: Background task triggers KB sync → Bedrock KB pulls file from S3 → BDA parses content → Chunks created → Embeddings generated → Stored in vector DB
3. **Query**: User asks question → Language detected → Query translated to English (if needed) → Hybrid search (vector + keyword) → Claude generates answer → Answer translated back → Citations included

---

## Project Structure

```
backend/
├── api/
│   ├── __init__.py
│   └── app.py                    # FastAPI application (main entry point)
│
├── config/
│   ├── __init__.py
│   ├── settings.py               # Configuration management (loads from .env)
│   ├── .env                      # Environment variables (create from .env.example)
│   └── .env.example              # Example environment configuration
│
├── services/
│   ├── __init__.py
│   ├── aws_client.py             # AWS client initialization and management
│   ├── upload_service.py         # Handles file uploads to S3 and KB sync
│   ├── metadata_extractor.py    # Extracts metadata from various file types
│   ├── translation_service.py   # Language detection and translation
│   ├── kb_query_service.py      # Query Bedrock KB with hybrid search
│   ├── google_drive_service.py  # Google Drive OAuth2 and file import
│   ├── ingestion_tracker.py     # Tracks processed files (prevents duplicates)
│   ├── file_repository_service.py # Import files from external S3 buckets
│   ├── kb_native_ingestion.py   # Direct Bedrock KB ingestion operations
│   ├── s3_service.py             # S3 operations (upload, list, delete)
│   └── excel_parser_service.py  # Excel file parsing
│
├── middleware/
│   ├── __init__.py
│   └── logging_middleware.py    # HTTP request/response logging
│
├── utils/
│   ├── __init__.py
│   └── logger.py                 # Structured JSON logging configuration
│
├── scripts/
│   ├── log_analyzer.py           # Analyze structured logs
│   └── monitor_logs.py           # Real-time log monitoring
│
├── tests/
│   ├── check_kb.py               # Test KB connectivity
│   ├── check_kb2.py              # Additional KB tests
│   ├── test_credentials.py      # Test AWS credentials
│   └── test_backend.py           # Backend integration tests
│
├── logs/
│   └── app.log                   # Application logs (JSON format)
│
├── get_sso_credentials.py        # Helper to get AWS SSO credentials
├── lambda_sync_trigger.py        # AWS Lambda function for scheduled sync
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## Setup & Installation

### Prerequisites

- Python 3.9 or higher
- AWS Account with access to:
  - Amazon S3
  - Amazon Bedrock (Knowledge Base, Claude models)
  - Amazon Translate & Comprehend
- AWS credentials (IAM user or SSO)
- (Optional) Google Cloud project for Drive integration

### Installation Steps

#### 1. Navigate to backend directory

```bash
cd backend
```

#### 2. Create a virtual environment

```bash
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Mac/Linux
source venv/bin/activate
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure environment

Copy the example environment file:

```bash
cp config/.env.example config/.env
```

Edit `config/.env` with your AWS configuration (see [Configuration](#configuration) section below).

#### 5. Run the server

```bash
cd api
python app.py
```

Or using uvicorn directly:

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8001 --reload
```

The API will be available at:
- API: `http://localhost:8001`
- Interactive docs: `http://localhost:8001/docs`
- OpenAPI spec: `http://localhost:8001/openapi.json`

---

## Configuration

All configuration is managed through environment variables in `config/.env`.

### Required Settings

```env
# ============================================================================
# AWS Credentials
# ============================================================================
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
# AWS_SESSION_TOKEN=token_here  # Only needed for SSO/temporary credentials

# ============================================================================
# S3 Storage
# ============================================================================
S3_RAW_BUCKET=your-kb-bucket-name

# ============================================================================
# Bedrock Knowledge Base
# ============================================================================
BEDROCK_KB_ID=your-knowledge-base-id
BEDROCK_DATA_SOURCE_ID=your-data-source-id
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v1

# Claude Sonnet 4.5 for answer generation (global inference profile)
BEDROCK_GENERATION_MODEL_ARN=global.anthropic.claude-sonnet-4-5-20250929-v1:0

# Number of chunks to retrieve per query
KB_NUM_RESULTS=10
```

### Optional Settings

```env
# ============================================================================
# Google Drive Integration (Optional)
# ============================================================================
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# ============================================================================
# Scheduled Sync (Optional)
# ============================================================================
SYNC_INTERVAL_MINUTES=60          # How often to run incremental sync
USE_EVENTBRIDGE=false             # Set true if using AWS EventBridge

# ============================================================================
# Upload Limits (Optional)
# ============================================================================
MAX_UPLOAD_BYTES=524288000        # 500MB default
```

### Getting AWS Credentials

#### Option 1: IAM User (Permanent Credentials)

1. Go to AWS Console → IAM → Users → Create User
2. Attach policies:
   - `AmazonS3FullAccess` (or custom policy for your bucket)
   - `AmazonBedrockFullAccess`
   - `TranslateFullAccess`
   - `ComprehendFullAccess`
3. Create access key → Copy `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`

#### Option 2: AWS SSO (Temporary Credentials)

```bash
# Run the helper script
python get_sso_credentials.py

# This will output credentials to copy into your .env file
```

### Validating Configuration

The settings are automatically validated on startup. If any required field is missing, you'll see an error:

```
ValueError: Missing required configuration: AWS_ACCESS_KEY_ID, S3_RAW_BUCKET
Please update your .env file with these values.
```

---

## Core Services

### 1. Upload Service (`services/upload_service.py`)

**Purpose**: Handles file uploads to S3 and triggers Knowledge Base synchronization.

**Key Methods**:
- `upload_to_s3(file_content, file_name, user_id, metadata)`: Stores file in S3 with metadata
- `trigger_kb_sync()`: Triggers Bedrock KB data source sync
- `poll_kb_sync_status(job_id)`: Polls sync job until completion
- `background_sync()`: Background task that triggers sync after upload response

**Flow**:
1. Receive file upload request
2. Extract metadata (via MetadataExtractor)
3. Store file in S3 with metadata as custom headers
4. Record file in ingestion tracker
5. Return immediate response to client
6. Background task triggers KB sync
7. Poll sync status until complete

**S3 Key Structure**: `docs/{user_id}/{timestamp}_{filename}`

**Example**:
```python
result = upload_service.upload_to_s3(
    file_content=file_bytes,
    file_name="report.pdf",
    user_id="user123",
    metadata={"author": "John Doe", "department": "Engineering"}
)
# Returns: {"s3_key": "docs/user123/20260617_120000_report.pdf", "etag": "..."}
```

### 2. Metadata Extractor (`services/metadata_extractor.py`)

**Purpose**: Extracts metadata from various file formats automatically.

**Supported Formats**:

| Format | Metadata Extracted |
|--------|-------------------|
| PDF | Author, title, subject, keywords, creator, producer, creation date, modification date, page count |
| DOCX | Author, title, subject, keywords, company, manager, creation date, modification date |
| PPTX | Author, title, subject, keywords, company, creation date, modification date, slide count |
| XLSX | Author, title, subject, company, creation date, modification date, sheet names |
| Images (JPEG/PNG) | EXIF data (camera make/model, GPS coordinates, date taken, resolution, ISO, aperture, shutter speed) |
| Videos (MP4/AVI/MOV/MKV/WebM) | Duration, resolution, codec, bitrate, frame rate |
| Audio (MP3/WAV) | Duration, bitrate, sample rate, ID3 tags (artist, album, title) |

**Dependencies**:
- `PyPDF2` for PDF metadata
- `python-docx` for DOCX metadata
- `python-pptx` for PPTX metadata
- `openpyxl` for XLSX metadata
- `Pillow` (PIL) for image EXIF data
- `python-magic` for MIME type detection

**Example**:
```python
with open('document.pdf', 'rb') as f:
    content = f.read()

metadata = metadata_extractor.extract_metadata(
    file_content=content,
    filename='document.pdf',
    content_type='application/pdf'
)

# Returns:
# {
#   "extraction_timestamp": "2026-06-17T10:30:00Z",
#   "filename": "document.pdf",
#   "content_type": "application/pdf",
#   "file_size": 245678,
#   "author": "John Doe",
#   "title": "Annual Report 2026",
#   "creation_date": "2026-06-01",
#   "page_count": 42
# }
```

### 3. Query Service (`services/kb_query_service.py`)

**Purpose**: Query Bedrock Knowledge Base with hybrid search and AI-generated answers.

**Search Type**: HYBRID (combines vector similarity + keyword BM25)

**Generation Model**: Claude Sonnet 4.5

**Multi-Language Flow**:
1. Detect query language (English/Sinhala/Tamil)
2. Translate query to English if needed
3. Perform hybrid search
4. Generate answer with Claude Sonnet 4.5
5. Translate answer back to original language

**Key Methods**:
- `query(query, user_id, team_id, max_results)`: Execute hybrid search with RAG

**Access Control**:
- If `user_id` provided: filters by `user_id` metadata
- If `team_id` provided: filters by `team_id` OR `user_id` metadata
- Filters are applied at the vector search level

**Response Format**:
```json
{
  "answer": "Translated answer in original language",
  "answer_english": "Original English answer",
  "citations": [
    {
      "content": {"text": "Relevant chunk text"},
      "score": 0.87,
      "location": {"s3Location": {"uri": "s3://bucket/key"}},
      "metadata": {"author": "John Doe", "user_id": "user123"},
      "s3_uri": "s3://bucket/key",
      "source_file": "report.pdf"
    }
  ],
  "results_count": 5,
  "results": [...],
  "session_id": "session-uuid",
  "language": {
    "detected": "si",
    "name": "Sinhala",
    "query_translated": true,
    "english_query": "What is machine learning?"
  },
  "retrieval": {
    "search_type": "HYBRID",
    "chunks_requested": 10,
    "chunks_returned": 5,
    "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
  }
}
```

### 4. Translation Service (`services/translation_service.py`)

**Purpose**: Detect language and translate queries/answers between English, Sinhala, and Tamil.

**AWS Services Used**:
- Amazon Comprehend: Language detection
- Amazon Translate: Translation

**Supported Languages**:
- `en`: English
- `si`: Sinhala (Sinhalese)
- `ta`: Tamil

**Key Methods**:
- `detect_language(text)`: Detect language code (e.g., "si", "ta", "en")
- `to_english(text, source_lang)`: Translate to English
- `from_english(text, target_lang)`: Translate from English
- `from_english_markdown(text, target_lang)`: Translate markdown while preserving formatting

**Markdown Translation**: Special handling to preserve:
- `**bold**` formatting
- `## headings`
- `- bullet points`
- `1. numbered lists`
- `` `code` `` blocks
- Links and other markdown syntax

**Example**:
```python
# Detect language
lang = translation_service.detect_language("இயந்திர கற்றல் என்றால் என்ன?")
# Returns: "ta" (Tamil)

# Translate to English
english = translation_service.to_english("இயந்திர கற்றல் என்றால் என்ன?", "ta")
# Returns: "What is machine learning?"

# Translate back to Tamil
tamil = translation_service.from_english("Machine learning is...", "ta")
# Returns: "இயந்திர கற்றல்..."
```

### 5. Ingestion Tracker (`services/ingestion_tracker.py`)

**Purpose**: Track processed files to prevent duplicate ingestion and enable incremental sync.

**Storage**: JSON file (`ingestion_tracker.json`)

**Data Structure**:
```json
{
  "docs/user123/20260617_120000_report.pdf": {
    "etag": "d41d8cd98f00b204e9800998ecf8427e",
    "last_ingested": "2026-06-17T12:05:30Z"
  }
}
```

**Key Methods**:
- `record_ingested(s3_key, etag)`: Record a successfully ingested file
- `is_file_ingested(s3_key, etag)`: Check if file already processed
- `get_new_or_changed_files()`: Scan S3 and find new/changed files
- `clear_tracker()`: Clear all tracking data

**Use Cases**:
1. **Duplicate Prevention**: Skip re-processing unchanged files
2. **Incremental Sync**: Scheduled job only syncs new/changed files
3. **Resume Support**: Recover from partial sync failures

### 6. Google Drive Service (`services/google_drive_service.py`)

**Purpose**: Import documents from Google Drive (both personal My Drive and Shared Drives/Team Drives).

**Key Features**:
- List files from personal Google Drive
- List files from Shared Drives (Team Drives)
- List available Shared Drives
- Download file content
- Support for various Google Workspace file types

**Key Methods**:
- `list_shared_drives(access_token)`: List all Shared Drives user has access to
- `list_files(access_token, drive_id=None)`: List files (personal or Shared Drive)
- `download_file(file_id, access_token)`: Download file content

**Scopes**: `https://www.googleapis.com/auth/drive.readonly`

### 7. File Repository Service (`services/file_repository_service.py`)

**Purpose**: Import files from external S3 buckets into the Knowledge Base.

**Use Cases**:
- Bulk import from company S3 buckets
- Import specific files by S3 URI
- Copy files from other AWS accounts (with proper permissions)

**Key Methods**:
- `import_from_s3(source_bucket, prefix, user_id, metadata)`: Bulk import from S3 prefix
- `import_single_file(source_bucket, source_key, user_id, metadata)`: Import single file
- `import_from_uri(s3_uri, user_id, metadata)`: Import using S3 URI

**Example**:
```python
# Import all files from hr-policies folder
file_repository_service.import_from_s3(
    source_bucket="company-docs",
    prefix="hr-policies/",
    user_id="hr_admin",
    metadata={"department": "HR"}
)
```

---

## API Endpoints

### Base URL: `http://localhost:8001/api`

All API endpoints are documented in the interactive API docs at `http://localhost:8001/docs`

### Upload & Ingestion

#### `POST /api/upload/direct`
Upload a file directly to S3 and trigger Knowledge Base sync.

**Request**:
```http
POST /api/upload/direct
Content-Type: multipart/form-data

file: <binary file data>
user_id: user123
team_id: team456  (optional)
department: Engineering  (optional)
```

**Response**:
```json
{
  "message": "File uploaded successfully",
  "s3_key": "docs/user123/20260617_120000_report.pdf",
  "s3_uri": "s3://your-bucket/docs/user123/20260617_120000_report.pdf",
  "etag": "d41d8cd98f00b204e9800998ecf8427e",
  "file_size": 245678,
  "extracted_metadata": {
    "author": "John Doe",
    "title": "Annual Report",
    "creation_date": "2026-06-01"
  },
  "ingestion": {
    "message": "KB sync triggered",
    "job_id": "ABC123XYZ"
  }
}
```

#### `GET /api/upload/sync-status/{job_id}`
Check the status of a Knowledge Base sync job.

**Response**:
```json
{
  "job_id": "ABC123XYZ",
  "status": "IN_PROGRESS",
  "started_at": "2026-06-17T12:00:00Z",
  "completed_at": null
}
```

Status values: `STARTING`, `IN_PROGRESS`, `COMPLETE`, `FAILED`, `STOPPING`

### Knowledge Base Sync

#### `POST /api/kb/sync`
Manually trigger a full Knowledge Base sync.

**Request**:
```json
{
  "force": false  // true to force full sync
}
```

#### `GET /api/kb/sync/latest`
Get the status of the most recent sync job.

**Response**:
```json
{
  "job_id": "ABC123XYZ",
  "status": "COMPLETE",
  "started_at": "2026-06-17T12:00:00Z",
  "completed_at": "2026-06-17T12:05:30Z",
  "statistics": {
    "documentsScanned": 42,
    "documentsIndexed": 42,
    "documentsFailed": 0
  }
}
```

#### `POST /api/kb/incremental-sync`
Trigger incremental sync (only new/changed files).

#### `GET /api/kb/tracker/stats`
Get ingestion tracker statistics.

**Response**:
```json
{
  "total_tracked_files": 42,
  "last_sync": "2026-06-17T12:05:30Z"
}
```

### Query & Retrieval

#### `POST /api/retrieve` or `POST /api/kb/query`
Query the Knowledge Base with hybrid search and get AI-generated answers.

**Request**:
```json
{
  "query": "What is machine learning?",
  "user_id": "user123",  // optional: filter by user
  "team_id": "team456",  // optional: filter by team
  "max_results": 10      // optional: default 10
}
```

**Response**: See [Query Service](#3-query-service-serviceskb_query_servicepy) response format above.

### Google Drive Integration

#### `GET /api/google-drive/shared-drives`
List Shared Drives (Team Drives) the user has access to.

**Headers**: `Authorization: Bearer <google_access_token>`

**Response**:
```json
{
  "drives": [
    {
      "id": "0ABC...",
      "name": "Engineering Team Drive"
    }
  ]
}
```

#### `GET /api/google-drive/files`
List files in user's Google Drive or a Shared Drive.

**Headers**: `Authorization: Bearer <google_access_token>`

**Query Parameters**:
- `drive_id` (optional): Shared Drive ID. Omit for personal My Drive.

**Response**:
```json
{
  "files": [
    {
      "id": "1abc...",
      "name": "document.pdf",
      "mimeType": "application/pdf",
      "size": 245678,
      "modifiedTime": "2026-06-17T10:30:00Z"
    }
  ]
}
```

#### `POST /api/google-drive/import`
Import files from Google Drive to the Knowledge Base.

**Headers**: `Authorization: Bearer <google_access_token>`

**Request**:
```json
{
  "files": [
    {"id": "1abc...", "name": "doc1.pdf", "mimeType": "application/pdf"},
    {"id": "2def...", "name": "doc2.docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
  ],
  "google_access_token": "ya29...",
  "user_id": "user123",
  "team_id": "team456",
  "drive_id": "0ABC..."  // optional: for Shared Drive files
}
```

### File Repository (S3 Import)

#### `GET /api/file-repo/list`
List files in an external S3 bucket.

**Query Parameters**:
- `bucket`: Source S3 bucket name
- `prefix`: Folder prefix (optional)

#### `POST /api/file-repo/import`
Bulk import files from an external S3 bucket.

**Request**:
```json
{
  "source_bucket": "company-docs",
  "prefix": "hr-policies/",
  "user_id": "hr_admin",
  "team_id": "hr",
  "department": "HR",
  "max_files": 1000
}
```

#### `POST /api/file-repo/import-single`
Import a single file from an external S3 bucket.

**Request**:
```json
{
  "source_bucket": "company-docs",
  "source_key": "hr-policies/policy.pdf",
  "user_id": "hr_admin"
}
```

#### `POST /api/file-repo/import-uri`
Import a file using an S3 URI.

**Request**:
```json
{
  "s3_uri": "s3://company-docs/hr-policies/policy.pdf",
  "user_id": "hr_admin"
}
```

### Metadata & Documents

#### `GET /api/metadata/{s3_key}`
Get metadata for a specific S3 object.

**Example**: `GET /api/metadata/docs/user123/20260617_120000_report.pdf`

#### `GET /api/documents`
List all documents in the Knowledge Base.

**Query Parameters**:
- `user_id` (optional): Filter by user
- `limit`: Max results (default 100)

### Health & Info

#### `GET /` or `GET /api/health`
Health check endpoint.

**Response**:
```json
{
  "service": "Knowledge Base API",
  "status": "healthy",
  "version": "3.0.0",
  "timestamp": "2026-06-17T12:00:00Z"
}
```

#### `GET /api/supported-formats`
Get list of supported file formats.

**Response**:
```json
{
  "formats": {
    "documents": ["pdf", "docx", "pptx", "xlsx", "txt"],
    "images": ["jpeg", "jpg", "png"],
    "videos": ["mp4", "avi", "mov", "mkv", "webm"],
    "audio": ["mp3", "wav"]
  }
}
```

#### `GET /api/architecture`
Get system architecture information.

---

## File Processing Flow

### Upload Flow (Detailed)

```
1. Client sends file
   ↓
2. FastAPI receives multipart upload
   ↓
3. Validate file size (< 500MB)
   ↓
4. Read file content into memory
   ↓
5. Extract metadata based on file type
   │  ├─ PDF → author, title, keywords, dates, page count
   │  ├─ DOCX → author, company, dates
   │  ├─ Image → EXIF (camera, GPS, timestamp)
   │  ├─ Video → duration, resolution, codec
   │  └─ Audio → duration, bitrate, ID3 tags
   ↓
6. Generate S3 key: docs/{user_id}/{timestamp}_{filename}
   ↓
7. Upload to S3 with metadata as custom headers
   ↓
8. Record in ingestion tracker (s3_key + etag)
   ↓
9. Return response to client immediately
   ↓
10. Background task: Trigger KB sync
    ↓
11. Poll KB sync status every 10 seconds
    ↓
12. When complete, log success or failure
```

### Knowledge Base Sync Flow (Bedrock KB Internal)

```
1. StartIngestionJob API called
   ↓
2. Bedrock KB scans S3 bucket
   ↓
3. For each new/changed file:
   │
   ├─ PDF
   │  ├─ Extract text
   │  ├─ Preserve structure (headings, lists, tables)
   │  └─ Extract embedded images (OCR if needed)
   │
   ├─ Images
   │  └─ OCR with Amazon Textract
   │
   ├─ Videos
   │  └─ Transcribe with Amazon Transcribe
   │
   ├─ Audio
   │  └─ Transcribe with Amazon Transcribe
   │
   └─ Office Docs (DOCX, PPTX, XLSX)
      └─ Parse and extract text
   ↓
4. Chunk text into semantic segments
   │  • Default chunk size: ~300 tokens
   │  • Overlap: ~20% for context
   │  • Respects paragraph boundaries
   ↓
5. Generate embeddings with Titan Embed Text v1
   │  • 1536-dimensional vectors
   ↓
6. Store in managed vector database
   │  • Vector index for similarity search
   │  • Inverted index for keyword (BM25) search
   │  • Metadata stored alongside each chunk
   ↓
7. Update sync job status to COMPLETE
```

### Query Flow (Detailed)

```
1. Client sends query: "இயந்திர கற்றல் என்றால் என்ன?" (Tamil)
   ↓
2. Detect language → "ta" (Tamil)
   ↓
3. Translate to English → "What is machine learning?"
   ↓
4. Build retrieval configuration
   │  • Search type: HYBRID
   │  • Max chunks: 10
   │  • Filters: user_id = "user123"
   ↓
5. Call Bedrock retrieve_and_generate
   │
   ├─ Retrieval Phase
   │  ├─ Vector search (semantic similarity)
   │  ├─ Keyword search (BM25)
   │  ├─ Combine scores
   │  ├─ Apply metadata filters
   │  └─ Return top 10 chunks
   │
   └─ Generation Phase
      ├─ Build prompt with retrieved chunks
      ├─ Call Claude Sonnet 4.5
      ├─ Generate contextual answer
      └─ Extract citations (chunk sources)
   ↓
6. Parse response
   │  • English answer
   │  • Citation list with S3 URIs
   ↓
7. Translate answer to Tamil
   │  • Markdown-aware translation
   │  • Preserves **bold**, ## headings, etc.
   ↓
8. Return response with:
   │  • Translated answer
   │  • Original English answer
   │  • Citations with source files
   │  • Language metadata
```

---

## Multi-Language Support

### Supported Languages

| Code | Language | Status |
|------|----------|--------|
| `en` | English | Native |
| `si` | Sinhala | Fully supported |
| `ta` | Tamil | Fully supported |

### How It Works

1. **Detection**: Amazon Comprehend analyzes query text and returns confidence scores for each detected language
2. **Translation to English**: Amazon Translate converts query to English for search (KB only indexes English)
3. **Search in English**: Hybrid search executes on English embeddings
4. **Answer Generation in English**: Claude Sonnet 4.5 generates English answer
5. **Translation to Original Language**: Answer translated back with markdown preservation

### Markdown Translation

Special care is taken to preserve markdown formatting during translation:

**Before Translation**:
```markdown
## Machine Learning Overview

**Machine learning** is a subset of AI. Key concepts:

1. **Supervised learning** - labeled data
2. **Unsupervised learning** - patterns
3. **Reinforcement learning** - rewards
```

**After Translation** (to Sinhala):
```markdown
## යන්ත්‍ර ඉගෙනීමේ දළ විශ්ලේෂණය

**යන්ත්‍ර ඉගෙනීම** AI හි උප කුලකයකි. ප්‍රධාන සංකල්ප:

1. **අධීක්ෂණය කළ ඉගෙනීම** - ලේබල් කළ දත්ත
2. **අධීක්ෂණය නොකළ ඉගෙනීම** - රටා
3. **ශක්තිමත් කිරීමේ ඉගෙනීම** - ත්‍යාග
```

### Fallback Behavior

- If language detection fails or confidence < 0.5 → assume English
- If translation fails → return English answer with error flag
- If unsupported language detected → warn user, process as English

---

## Logging & Monitoring

### Structured Logging

All logs are JSON-formatted for easy parsing and analysis.

**Log Location**: `backend/logs/app.log`

**Log Format**:
```json
{
  "timestamp": "2026-06-17T12:00:00.123Z",
  "level": "INFO",
  "logger": "services.upload_service",
  "event": "document_uploaded_to_s3",
  "data": {
    "s3_key": "docs/user123/20260617_120000_report.pdf",
    "file_size": 245678,
    "etag": "abc123",
    "upload_duration_seconds": 1.23
  }
}
```

### Log Events

#### Upload Events
- `document_uploaded_to_s3`: File successfully stored
- `kb_sync_triggered`: Sync job started
- `kb_sync_in_progress`: Polling heartbeat
- `kb_sync_completed`: Sync finished
- `kb_sync_trigger_failed`: Sync trigger failed
- `upload_failed`: S3 upload failed

#### Query Events
- `query_received`: New query received
- `language_detected`: Language detection result
- `query_translated`: Translation completed
- `kb_search_executed`: Search completed
- `answer_generated`: Answer generated
- `answer_translated`: Answer translated back

#### Metadata Events
- `metadata_extraction_started`: Starting extraction
- `metadata_extracted`: Extraction complete
- `metadata_extraction_failed`: Extraction failed

### HTTP Request Logging

The `LoggingMiddleware` logs every HTTP request/response:

```json
{
  "timestamp": "2026-06-17T12:00:00Z",
  "level": "INFO",
  "event": "http_request",
  "data": {
    "method": "POST",
    "path": "/api/upload/direct",
    "status_code": 200,
    "duration_ms": 1234,
    "client_ip": "192.168.1.100"
  }
}
```

### Log Analysis

Use the provided scripts for log analysis:

#### Real-time Monitoring
```bash
python scripts/monitor_logs.py
```

Outputs:
- Live log stream with color-coded levels
- Filters by event type
- Highlights errors

#### Log Analysis
```bash
python scripts/log_analyzer.py --hours 24 --event upload
```

Outputs:
- Event counts by type
- Error rate
- Average durations
- Top users/files

---

## Testing

### Test Files Location

All test files are in `backend/tests/`:

- `check_kb.py`: Test Bedrock KB connectivity
- `check_kb2.py`: Additional KB tests
- `test_credentials.py`: Validate AWS credentials
- `test_backend.py`: Backend integration tests

### Running Tests

#### Test AWS Credentials
```bash
python tests/test_credentials.py
```

Validates:
- AWS credentials are set
- Can access S3 bucket
- Can call Bedrock KB APIs
- Can call Translate/Comprehend APIs

#### Test Knowledge Base Connection
```bash
python tests/check_kb.py
```

Tests:
- KB exists and is accessible
- Data source is configured
- Can trigger sync
- Can query KB

#### Integration Tests
```bash
python tests/test_backend.py
```

Tests:
- End-to-end upload flow
- Metadata extraction
- Query flow
- Translation

### Manual Testing with cURL

#### Upload a file
```bash
curl -X POST http://localhost:8001/api/upload/direct \
  -F "file=@document.pdf" \
  -F "user_id=testuser" \
  -F "department=Engineering"
```

#### Query the KB
```bash
curl -X POST http://localhost:8001/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "user_id": "testuser",
    "max_results": 5
  }'
```

#### Check sync status
```bash
curl http://localhost:8001/api/upload/sync-status/ABC123XYZ
```

---

## Deployment

### Development

```bash
cd api
python app.py
```

Or with auto-reload:
```bash
uvicorn api.app:app --reload --host 0.0.0.0 --port 8001
```

### Production

#### Option 1: Uvicorn with Gunicorn

```bash
gunicorn api.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8001 \
  --timeout 300 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

#### Option 2: Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8001"]
```

Build and run:
```bash
docker build -t kb-backend .
docker run -p 8001:8001 --env-file config/.env kb-backend
```

### Scheduled Sync

#### Option 1: APScheduler (Default)

The backend uses APScheduler by default to run incremental sync every hour (configurable via `SYNC_INTERVAL_MINUTES`).

#### Option 2: AWS EventBridge

For production, use EventBridge:

1. Create Lambda function with `lambda_sync_trigger.py`
2. Create EventBridge rule: `rate(1 hour)`
3. Target: Lambda function
4. Set `USE_EVENTBRIDGE=true` in .env

---

## Troubleshooting

### Common Issues

#### 1. "Missing required configuration" error

**Cause**: `.env` file missing or incomplete

**Solution**:
```bash
cp config/.env.example config/.env
# Edit config/.env with your values
```

#### 2. "Access Denied" when accessing S3

**Cause**: IAM permissions insufficient

**Solution**: Ensure IAM user/role has `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on your bucket

#### 3. "Knowledge Base not found"

**Cause**: `BEDROCK_KB_ID` or `BEDROCK_DATA_SOURCE_ID` incorrect

**Solution**: Verify IDs in AWS Console → Bedrock → Knowledge Bases

#### 4. Sync job stays in `IN_PROGRESS` indefinitely

**Cause**: Large files or many files processing

**Solution**: Wait longer (can take 10-30 minutes for large datasets). Check CloudWatch logs for Bedrock KB.

#### 5. Queries return no results

**Cause**: KB sync not complete or files not indexed

**Solution**: 
1. Check sync status: `GET /api/kb/sync/latest`
2. Verify files are in S3
3. Check Bedrock KB console for indexing status

#### 6. Translation fails

**Cause**: Translate service not enabled in region or unsupported language

**Solution**:
1. Enable Translate in your AWS region
2. Verify language code is supported (`en`, `si`, `ta`)

---

## License

MIT License - See LICENSE file for details.

---

## Support

For issues, questions, or contributions:
- Check the logs: `backend/logs/app.log`
- Run tests: `python tests/test_backend.py`
- Review API docs: `http://localhost:8001/docs`

---

## Changelog

### v3.0.0 (2026-06-17)
- Simplified architecture using Bedrock KB native capabilities
- Added multi-language support (English, Sinhala, Tamil)
- Added automatic metadata extraction
- Added Google Drive integration (personal and Shared Drives)
- Added File Repository Service for S3 imports
- Enhanced structured logging
- Updated to Claude Sonnet 4.5 for generation
- Added incremental sync with APScheduler

---

**End of Documentation**
