# Complete System Flow - Dialog Knowledge Base

## Overview
This document explains how documents flow through the system from upload to being queryable in the chat interface.

---

## 📊 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER UPLOADS DOCUMENT                               │
│                         (via Web UI - Upload Page)                           │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: FRONTEND VALIDATION                                                 │
│  File: frontend/src/pages/UploadNew.jsx                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Check file size (max 500MB)                                              │
│  • Check file type (PDF, DOCX, HTML, XLSX, images, videos, audio)          │
│  • Show "Ready to upload" status                                            │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: UPLOAD TO BACKEND API                                              │
│  Endpoint: POST /api/upload/direct                                          │
│  File: backend/api/app.py (line 420-570)                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Receive file via multipart/form-data                                     │
│  • User sees "Uploading to S3" (progress bar)                               │
│  • File content loaded into memory                                          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: METADATA EXTRACTION                                                │
│  File: backend/services/metadata_extractor.py                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  • PDF → Extract text, page count, author, title                            │
│  • DOCX → Extract text, word count, author                                  │
│  • Image → Extract dimensions, format, EXIF data                            │
│  • Video → Extract duration, resolution, codec                              │
│  • User sees "Extracting metadata"                                          │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: AI AUTO-TAGGING                                                    │
│  File: backend/services/auto_tagger_service.py                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Send document text to Claude (Bedrock)                                   │
│  • Claude analyzes and generates tags:                                      │
│    - doc_type (policy, guide, manual, etc.)                                 │
│    - topic (billing, technical support, etc.)                               │
│    - department (HR, IT, Sales, etc.)                                       │
│  • Tags used for filtering in KB queries                                    │
│  • User sees "Generating AI tags"                                           │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: UPLOAD TO S3                                                       │
│  File: backend/services/upload_service.py (upload_to_s3)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Store file: s3://dialog-telecom/docs/filename.pdf                        │
│  • Store metadata: s3://dialog-telecom/docs/filename.pdf.metadata.json      │
│  • Get ETag (content hash) from S3                                          │
│  • User sees "Uploading to S3" → "Complete"                                 │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: ETAG VERIFICATION (Duplicate Check)                                │
│  File: backend/services/upload_service.py (background_sync)                 │
│  File: backend/services/ingestion_tracker.py                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Check: Is this exact file already ingested?                              │
│  • Compare NEW ETag vs OLD ETag in tracker                                  │
│                                                                              │
│  IF SAME ETAG (Duplicate):                                                  │
│    → Skip KB sync (instant)                                                 │
│    → Log: "kb_sync_skipped_duplicate"                                       │
│    → User sees "Ready for queries" immediately                              │
│                                                                              │
│  IF DIFFERENT ETAG (New or Changed):                                        │
│    → Continue to Step 7 (trigger KB sync)                                   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ (if new/changed)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: TRIGGER KB SYNC JOB                                                │
│  File: backend/services/upload_service.py (trigger_kb_sync)                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Call AWS Bedrock KB API: start_ingestion_job()                           │
│  • KB ID: RTG6PKX6VX                                                        │
│  • Data Source ID: 2JIWZKQVKG                                               │
│  • Returns ingestion_job_id (e.g., "ECUFMRZDAU")                            │
│  • User sees "Triggering KB sync"                                           │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 8: BEDROCK KB INGESTION (AWS Background Process)                      │
│  Service: AWS Bedrock Knowledge Base                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Bedrock Data Automation scans S3 bucket                                  │
│  • Finds new/changed files (checks ETag)                                    │
│  • Processes document:                                                      │
│    - Extract text from PDF/DOCX/HTML/images/videos                          │
│    - Chunk text into smaller pieces (~300 tokens each)                      │
│    - Generate embeddings (vector representations)                           │
│    - Store in OpenSearch Serverless (vector database)                       │
│  • Job Status: STARTING → IN_PROGRESS → COMPLETE                            │
│  • Duration: 10-30 seconds (depending on file size)                         │
│  • User sees "Syncing to Knowledge Base" (animated)                         │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 9: POLL SYNC STATUS                                                   │
│  File: backend/services/upload_service.py (_poll_sync_completion)           │
│  File: frontend/src/pages/UploadNew.jsx (KB sync polling)                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Backend polls every 10 seconds (background)                              │
│  • Frontend polls /api/kb/sync/latest every 2 seconds                       │
│  • Check job status via get_ingestion_job()                                 │
│  • When status = "COMPLETE":                                                │
│    → User sees "Ready for queries" ✅                                        │
│    → Document is now searchable in chat                                     │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DOCUMENT NOW QUERYABLE IN CHAT                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔍 Query Flow (User Asks Question)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  USER TYPES QUESTION IN CHAT                                                │
│  Page: frontend/src/pages/Retrieve.jsx                                      │
│  Example: "What are the Dialog data packages?"                              │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: GREETING DETECTION                                                 │
│  File: backend/utils/greeting_detector.py                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Check: Is this a greeting? (hi, hello, thanks, bye)                      │
│                                                                              │
│  IF GREETING:                                                               │
│    → Skip KB search                                                         │
│    → Generate conversational response directly                              │
│    → Return answer (fast, 1-2 seconds)                                      │
│                                                                              │
│  IF NOT GREETING:                                                           │
│    → Continue to Step 2                                                     │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ (if not greeting)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: LANGUAGE DETECTION                                                 │
│  File: backend/services/translation_service.py                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Detect language: English, Sinhala, or Tamil                              │
│  • User sees: "Detecting language..."                                       │
│  • User sees: "Language: English" (or Sinhala/Tamil)                        │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: TRANSLATION (if needed)                                            │
│  File: backend/services/translation_service.py                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  • IF Sinhala or Tamil:                                                     │
│    → Translate to English using AWS Translate                               │
│    → Example: "ඩේටා පැකේජ මොනවාද?" → "What are the data packages?"        │
│    → User sees: "Translating Sinhala → English..."                          │
│  • IF English:                                                              │
│    → Skip translation                                                       │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: SEARCH KNOWLEDGE BASE                                              │
│  File: backend/services/kb_query_service.py                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Send query to Bedrock KB: retrieve_and_generate()                        │
│  • Bedrock KB does:                                                         │
│    1. Convert query to embedding (vector)                                   │
│    2. Search OpenSearch for similar chunks (vector similarity)              │
│    3. Retrieve top 10 most relevant chunks                                  │
│    4. Return chunks with metadata (file name, score, text)                  │
│  • User sees: "Searching knowledge base..."                                 │
│  • Duration: 2-3 seconds                                                    │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: GENERATE ANSWER (RAG)                                              │
│  File: backend/services/kb_query_service.py                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Send to Claude (Bedrock):                                                │
│    - User's question                                                        │
│    - Retrieved chunks (context)                                             │
│  • Claude generates answer based ONLY on provided chunks                    │
│  • User sees: "Generating answer from sources..."                           │
│  • Duration: 2-5 seconds                                                    │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: STREAM ANSWER TO USER                                              │
│  File: backend/api/app.py (query_knowledge_base_stream)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Stream answer word-by-word (chunks of 3-5 words)                         │
│  • User sees answer appear in real-time                                     │
│  • Also send citations (source documents)                                   │
│  • User sees: "Knowledge Base" tag with document names                      │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: SAVE TO CHAT HISTORY                                               │
│  File: backend/services/chat_session_service.py                             │
│  Database: PostgreSQL RDS                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Save user question + AI answer to database                               │
│  • Include:                                                                 │
│    - User query                                                             │
│    - AI answer                                                              │
│    - Citations (source documents)                                           │
│    - Timestamp (IST timezone)                                               │
│    - Language info                                                          │
│  • User can access this conversation later from sidebar                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Scheduled Incremental Sync

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  BACKGROUND PROCESS (Runs Every 1 Minute)                                   │
│  File: backend/api/app.py (scheduled_incremental_sync)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Scan entire S3 bucket (dialog-telecom)                                  │
│  2. Compare each file's ETag with ingestion tracker                         │
│  3. Find new or changed files                                               │
│  4. If found:                                                               │
│     → Trigger KB sync job                                                   │
│     → Wait for completion                                                   │
│     → Update tracker                                                        │
│  5. If nothing new:                                                         │
│     → Log: "nothing new to ingest"                                          │
│     → Wait until next cycle                                                 │
│                                                                              │
│  This ensures files uploaded via other methods (Google Drive, S3 import)    │
│  are also indexed automatically                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📝 Simple Explanation of Each Component

### 1. **Frontend (React)**
- **Purpose:** User interface for uploading files and asking questions
- **Location:** `frontend/src/pages/`
- **Key Pages:**
  - `UploadNew.jsx` - Upload files, see progress
  - `Retrieve.jsx` - Chat interface, ask questions
  - `Sidebar.jsx` - Previous chat sessions

### 2. **Backend API (FastAPI)**
- **Purpose:** Handle requests, coordinate services
- **Location:** `backend/api/app.py`
- **Key Endpoints:**
  - `POST /api/upload/direct` - Upload files
  - `POST /api/retrieve/stream` - Ask questions (streaming)
  - `GET /api/chat/sessions` - Get chat history

### 3. **Metadata Extractor**
- **Purpose:** Extract information from documents
- **Location:** `backend/services/metadata_extractor.py`
- **Extracts:**
  - PDF: text, page count, author
  - Images: dimensions, format
  - Videos: duration, resolution

### 4. **Auto-Tagger (Claude)**
- **Purpose:** Automatically tag documents with categories
- **Location:** `backend/services/auto_tagger_service.py`
- **Tags Generated:**
  - `doc_type`: policy, guide, manual, FAQ
  - `topic`: billing, technical, account
  - `department`: HR, IT, Sales

### 5. **Upload Service**
- **Purpose:** Store files in S3, manage KB sync
- **Location:** `backend/services/upload_service.py`
- **Does:**
  - Upload to S3
  - Trigger KB ingestion
  - Poll sync status
  - Track with ETag

### 6. **Ingestion Tracker**
- **Purpose:** Remember which files are already indexed
- **Location:** `backend/services/ingestion_tracker.py`
- **Stores:** `s3://dialog-telecom/.ingestion_tracker/state.json`
- **Format:**
  ```json
  {
    "docs/file.pdf": {
      "etag": "abc123",
      "ingested_at": "2026-06-18T12:00:00",
      "status": "ingested"
    }
  }
  ```

### 7. **Bedrock Knowledge Base**
- **Purpose:** Vector database for semantic search
- **Service:** AWS Bedrock KB
- **Components:**
  - **Embeddings:** Convert text to vectors (numbers)
  - **OpenSearch:** Store and search vectors
  - **Data Automation:** Process files automatically

### 8. **Translation Service**
- **Purpose:** Support Sinhala and Tamil queries
- **Location:** `backend/services/translation_service.py`
- **Uses:** AWS Translate
- **Flow:** Sinhala → English → Search KB → Answer

### 9. **Greeting Detector**
- **Purpose:** Handle greetings without KB search
- **Location:** `backend/utils/greeting_detector.py`
- **Detects:** hi, hello, thanks, bye (English, Sinhala, Tamil)
- **Benefit:** Fast responses for small talk

### 10. **Query Service**
- **Purpose:** Search KB and generate answers
- **Location:** `backend/services/kb_query_service.py`
- **Process:**
  1. Convert query to embedding
  2. Search similar chunks
  3. Send chunks + query to Claude
  4. Claude generates answer

### 11. **Chat Session Service**
- **Purpose:** Save conversation history
- **Location:** `backend/services/chat_session_service.py`
- **Database:** PostgreSQL RDS
- **Tables:**
  - `chat_sessions`: conversation metadata
  - `chat_messages`: individual messages

### 12. **Conversational Service**
- **Purpose:** Generate friendly greeting responses
- **Location:** `backend/services/conversational_service.py`
- **Uses:** Claude (Bedrock)
- **Responses:** Warm, helpful, brief (1-2 sentences)

---

## 🎯 Key Features

### 1. **ETag Deduplication**
- **What:** Skip KB sync for duplicate files
- **How:** Compare file hash (ETag) before syncing
- **Benefit:** Save time (0s vs 10s) and AWS costs

### 2. **Streaming Responses**
- **What:** Show answer as it's generated
- **How:** Server-Sent Events (SSE)
- **Benefit:** User sees progress, feels faster

### 3. **Multilingual Support**
- **Languages:** English, Sinhala (සිංහල), Tamil (தமிழ்)
- **How:** Auto-detect → translate → search → answer
- **Benefit:** Users query in their native language

### 4. **Greeting Detection**
- **What:** Respond to "hi", "thanks" without KB search
- **How:** Pattern matching before KB query
- **Benefit:** Fast responses (1-2s vs 5-10s)

### 5. **Auto-Tagging**
- **What:** Automatically categorize documents
- **How:** Claude analyzes content, generates tags
- **Benefit:** Better search filtering

### 6. **Real-Time Status**
- **What:** Show upload → sync → ready progress
- **How:** Poll KB sync status every 2 seconds
- **Benefit:** User knows when document is queryable

---

## 📊 Performance Metrics

| Operation | Duration | Notes |
|-----------|----------|-------|
| Upload to S3 | 1-3s | Depends on file size |
| Metadata extraction | 0.5-1s | Fast for most files |
| Auto-tagging | 2-5s | Claude API call |
| KB sync (new file) | 10-30s | Bedrock ingestion |
| KB sync (duplicate) | 0s | Skipped via ETag |
| Query KB | 2-3s | Vector search |
| Generate answer | 2-5s | Claude streaming |
| **Total (upload → queryable)** | **15-40s** | For new files |
| **Total (duplicate)** | **2-5s** | ETag skip |
| **Total (query)** | **4-8s** | Search + generate |
| **Total (greeting)** | **1-2s** | No KB search |

---

## 🗄️ Data Storage

### S3 Bucket Structure
```
s3://dialog-telecom/
├── docs/
│   ├── file1.pdf                      ← Actual document
│   ├── file1.pdf.metadata.json        ← Bedrock KB metadata
│   ├── file2.docx
│   ├── file2.docx.metadata.json
│   └── ...
└── .ingestion_tracker/
    └── state.json                      ← ETag tracker
```

### PostgreSQL Database
```
chat_sessions
├── id (UUID)
├── user_id
├── title
├── created_at
└── updated_at

chat_messages
├── id (UUID)
├── session_id (FK)
├── role (user/assistant)
├── content (text)
├── citations (JSON)
├── language (JSON)
├── duration_ms
└── created_at
```

### OpenSearch Serverless (Managed by Bedrock)
```
bedrock-knowledge-base-default-index
├── document_id
├── chunk_text                          ← Document chunk
├── embedding_vector                    ← 1536 dimensions
├── metadata
│   ├── source_file
│   ├── doc_type
│   ├── topic
│   └── department
└── score                               ← Similarity score
```

---

## 🔐 Security & Access

### Authentication
- **Method:** Google OAuth 2.0
- **JWT Tokens:** 8-hour expiration
- **Session Storage:** PostgreSQL

### File Access
- **S3:** IAM credentials (temporary via AWS SSO)
- **Bedrock KB:** IAM role-based access
- **Database:** PostgreSQL connection string

### User Isolation
- Files tagged with `user_id`
- Chat sessions filtered by `user_id`
- No cross-user data access

---

## 🚨 Error Handling

### Upload Failures
- File too large → Show error before upload
- Network error → Retry logic
- S3 error → File safely rejected, user notified

### KB Sync Failures
- File in S3 but sync failed → Next scheduled sync retries
- Unsupported format → Marked as failed in tracker
- Timeout → Polling stops after 30 minutes

### Query Failures
- No results found → "I don't have information about that"
- Bedrock error → Fallback error message
- Translation error → Query in English only

---

## 📈 Monitoring & Logs

### Structured JSON Logs
```json
{
  "event": "document_uploaded_to_s3",
  "filename": "policy.pdf",
  "s3_key": "docs/policy.pdf",
  "etag": "abc123",
  "size_bytes": 125000,
  "user_id": "user@example.com",
  "duration_ms": 1234
}
```

### Key Events to Monitor
- `document_uploaded_to_s3` - File stored
- `kb_sync_triggered` - Ingestion started
- `kb_sync_skipped_duplicate` - ETag dedup working
- `kb_sync_completed` - Document indexed
- `query_executed` - User asked question

---

## 🎓 Summary in Simple Terms

1. **User uploads PDF** → File goes to S3
2. **AI reads the PDF** → Extracts info, tags it
3. **Bedrock indexes it** → Breaks into chunks, creates search index
4. **User asks question** → System searches indexed chunks
5. **Claude reads chunks** → Generates answer based on content
6. **User sees answer** → With sources cited
7. **Conversation saved** → Can continue later

**Key Benefit:** Users can upload any document and immediately ask questions about it in English, Sinhala, or Tamil, and get accurate answers based on the actual document content.

---

This is the complete system flow! Each step is designed to be fast, reliable, and user-friendly. 🚀
