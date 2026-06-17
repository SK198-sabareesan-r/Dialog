# Format Processing Flow Architecture

## Complete End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER UPLOADS FILE                            │
│                     POST /api/v1/ingest/upload                       │
│                  (filename, content_type, file_data)                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FORMAT DETECTION & VALIDATION                     │
│                     (format_detector.py)                             │
├─────────────────────────────────────────────────────────────────────┤
│  1. Check content_type against SUPPORTED_FORMATS                    │
│  2. Fallback to filename extension detection                        │
│  3. Validate format is supported                                    │
│                                                                      │
│  ✓ Valid → Continue with format_info                                │
│  ✗ Invalid → Return HTTP 400 + supported formats list               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ENRICH METADATA                               │
├─────────────────────────────────────────────────────────────────────┤
│  metadata = {                                                       │
│    filename, content_type, size,                                    │
│    format_category, format_handler, mime_type,                      │
│    user_id, team_id                                                 │
│  }                                                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    UPLOAD TO S3 RAW ZONE                             │
│                      (s3_service.py)                                 │
├─────────────────────────────────────────────────────────────────────┤
│  s3://{raw_bucket}/{source}/{YYYY/MM/DD/HHMMSS}/{filename}         │
│  + Store metadata as S3 object metadata                             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              START STEP FUNCTIONS ORCHESTRATION                      │
│                 (stepfunctions_service.py)                           │
├─────────────────────────────────────────────────────────────────────┤
│  Input: {source_key, source_type, metadata, retry_count: 0}        │
│  Returns: execution_arn                                             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STEP FUNCTIONS: PROCESSING TASK                         │
│            Calls orchestrator.process_file()                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FORMAT PROCESSOR ROUTER                           │
│                    (format_processor.py)                             │
├─────────────────────────────────────────────────────────────────────┤
│  Routes based on format_info['handler']:                            │
│                                                                      │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐     │
│  │   Document   │     Image    │  Audio/Video │ Spreadsheet  │     │
│  │   (handler:  │  (handler:   │  (handler:   │  (handler:   │     │
│  │     bda)     │  textract)   │ transcribe)  │excel_parser) │     │
│  └──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┘     │
│         │              │              │              │              │
└─────────┼──────────────┼──────────────┼──────────────┼──────────────┘
          │              │              │              │
          ▼              ▼              ▼              ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   BEDROCK   │  │   TEXTRACT  │  │ TRANSCRIBE  │  │    EXCEL    │
│    DATA     │  │     OCR     │  │ AUDIO→TEXT  │  │   PARSER    │
│ AUTOMATION  │  │             │  │             │  │  (LOCAL)    │
├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ • PDF       │  │ • JPG       │  │ • MP4       │  │ • XLSX      │
│ • DOCX      │  │ • PNG       │  │ • AVI       │  │ • XLS       │
│ • PPTX      │  │ • TIFF      │  │ • MOV       │  │ • CSV       │
│ • HTML      │  │ • BMP       │  │ • MP3       │  │             │
│ • TXT       │  │             │  │ • WAV       │  │             │
│             │  │             │  │ • M4A       │  │             │
├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ ASYNC       │  │ SYNC        │  │ ASYNC       │  │ SYNC        │
│ Returns:    │  │ Returns:    │  │ Returns:    │  │ Returns:    │
│ job_id      │  │ text        │  │ job_name    │  │ text        │
│ status:     │  │ blocks      │  │ status:     │  │ sheets_data │
│ IN_PROGRESS │  │ status:     │  │ IN_PROGRESS │  │ status:     │
│             │  │ SUCCESS     │  │             │  │ SUCCESS     │
└─────┬───────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
      │                 │                │                 │
      │   ASYNC JOBS    │   SYNC JOBS    │   ASYNC JOBS    │   SYNC JOBS
      │   (polling)     │   (immediate)  │   (polling)     │   (immediate)
      │                 │                │                 │
      ▼                 ▼                ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│              RESULT AGGREGATION & METADATA ENRICHMENT                │
├─────────────────────────────────────────────────────────────────────┤
│  Common fields:                                                     │
│    • text (extracted content)                                       │
│    • metadata (enriched with processor-specific fields)             │
│    • status (SUCCESS / IN_PROGRESS / FAILED)                        │
│                                                                      │
│  Handler-specific metadata:                                         │
│    • Textract: text_blocks_count, page_count                        │
│    • Transcribe: transcribe_job_name, language_code                 │
│    • Excel: sheet_count, total_rows, sheet_names                    │
│    • BDA: bda_job_id                                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                     ┌─────────────────┐
                     │  Status Check   │
                     └────────┬────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
    ┌──────────────────┐            ┌──────────────────┐
    │  ASYNC (Polling) │            │  SYNC (Complete) │
    │  IN_PROGRESS     │            │  SUCCESS         │
    └────────┬─────────┘            └────────┬─────────┘
             │                               │
             │ Step Functions                │
             │ waits & polls                 │
             │ job status                    │
             │                               │
             ▼                               │
    ┌──────────────────┐                    │
    │  Job Complete?   │                    │
    │  Poll service:   │                    │
    │  • BDA job       │                    │
    │  • Transcribe    │                    │
    └────────┬─────────┘                    │
             │                               │
             │ Status: COMPLETED             │
             └───────────────┬───────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 SAVE PROCESSED OUTPUT TO S3                          │
│                   (s3_processed_bucket)                              │
├─────────────────────────────────────────────────────────────────────┤
│  JSON format with:                                                  │
│    • Extracted text                                                 │
│    • Enriched metadata                                              │
│    • Processing timestamps                                          │
│    • Handler information                                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              INGEST TO BEDROCK KNOWLEDGE BASE                        │
│                    (bedrock_service.py)                              │
├─────────────────────────────────────────────────────────────────────┤
│  • Automatic chunking (512 tokens with 50 token overlap)            │
│  • Titan embeddings generation                                      │
│  • Metadata tagging (user_id, team_id, format, etc.)                │
│  • Returns: ingestion_job_id                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    OPENSEARCH VECTOR INDEXING                        │
│                  (opensearch_service.py)                             │
├─────────────────────────────────────────────────────────────────────┤
│  • KNN vector storage                                               │
│  • Metadata fields for filtering                                    │
│  • IAM-based access control                                         │
│  • Index: document-embeddings                                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ✓ INGESTION COMPLETE                         │
│                   Document ready for retrieval                       │
└─────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════
                         ERROR HANDLING FLOWS
═══════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│                     FORMAT VALIDATION ERROR                          │
│                    (Unsupported file type)                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  Return HTTP 400 │
                    │  with supported  │
                    │  formats list    │
                    └──────────────────┘
                               │
                               ▼
                    ✗ NO PROCESSING ✗
                    (User must upload valid format)


┌─────────────────────────────────────────────────────────────────────┐
│                    PROCESSING ERROR (Transient)                      │
│              (AWS service error, network timeout, etc.)              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  Retry Count < 3?│
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │ YES                         │ NO
              ▼                             ▼
    ┌──────────────────┐          ┌──────────────────┐
    │  Send to Retry   │          │  Send to Dead    │
    │  Queue (SQS)     │          │  Letter Queue    │
    │  with exponential│          │  (DLQ)           │
    │  backoff         │          └────────┬─────────┘
    │  (2^n * 60s)     │                   │
    └────────┬─────────┘                   │
             │                             ▼
             │                  ┌──────────────────┐
             │                  │ CloudWatch Alarm │
             │                  │ + SNS Notification│
             │                  └──────────────────┘
             │                             │
             └──────────────┬──────────────┘
                            │
                            ▼
                 ┌──────────────────┐
                 │  Log Metrics:    │
                 │  • Source        │
                 │  • Error Type    │
                 │  • Retry Count   │
                 └──────────────────┘


═══════════════════════════════════════════════════════════════════════
                      RETRIEVAL FLOW (Access Control)
═══════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│                     USER QUERIES KNOWLEDGE BASE                      │
│                    POST /api/v1/retrieve                             │
│         {query, user_id, team_id (optional), max_results}            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   BUILD METADATA FILTER                              │
├─────────────────────────────────────────────────────────────────────┤
│  filter = {                                                         │
│    user_id: "user123",                                              │
│    team_id: "team456"  // optional                                  │
│  }                                                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              BEDROCK KNOWLEDGE BASE RETRIEVAL                        │
│           with IAM + Metadata-based filtering                        │
├─────────────────────────────────────────────────────────────────────┤
│  • Vector similarity search                                         │
│  • Apply user/team filters                                          │
│  • Rank by relevance                                                │
│  • Return top N results                                             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     RETURN FILTERED RESULTS                          │
│                    (Only accessible documents)                       │
└─────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════
                          MONITORING & METRICS
═══════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────────┐
│                       CLOUDWATCH METRICS                             │
├─────────────────────────────────────────────────────────────────────┤
│  By Handler:                                                        │
│    • textract - Processing duration                                 │
│    • transcribe - Processing duration                               │
│    • excel_parser - Processing duration                             │
│    • bda - Processing duration                                      │
│                                                                      │
│  By Source:                                                         │
│    • IngestionSuccess - Count by source                             │
│    • IngestionFailure - Count by error type                         │
│                                                                      │
│  Queue Metrics:                                                     │
│    • DLQMessageCount - Messages in dead letter queue                │
│    • RetryQueueDepth - Pending retries                              │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Decision Points

### 1. Format Detection (Entry Point)
- **Input:** filename, content_type
- **Output:** format_info (category, handler, mime_type)
- **Decision:** Route to appropriate handler

### 2. Sync vs Async Processing
- **Sync Handlers:** Textract (images), Excel Parser
  - Return results immediately
  - No polling required
  
- **Async Handlers:** Transcribe (audio/video), BDA (documents)
  - Return job ID
  - Step Functions polls for completion
  - Requires job status checking

### 3. Error Retry Strategy
- **Format Validation Errors:** No retry, immediate DLQ
- **Transient Processing Errors:** Retry up to 3 times with exponential backoff
- **Permanent Errors:** DLQ + CloudWatch alarm

### 4. Access Control Application
- Applied at retrieval time
- Metadata-based filtering (user_id, team_id)
- No direct document access without proper metadata

## Processing Times (Estimates)

| Format Category | Handler | Typical Duration | Type |
|----------------|---------|------------------|------|
| Image (1 page) | Textract | 2-5 seconds | Sync |
| Spreadsheet | Excel Parser | 1-3 seconds | Sync |
| Document (10 pages) | BDA | 30-60 seconds | Async |
| Audio (5 minutes) | Transcribe | 2-3 minutes | Async |
| Video (5 minutes) | Transcribe | 3-5 minutes | Async |
