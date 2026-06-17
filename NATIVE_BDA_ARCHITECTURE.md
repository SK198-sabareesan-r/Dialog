# Native Bedrock KB with Built-in BDA Integration

## Architecture Overview

### ✅ **New Simplified Flow**

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER UPLOADS FILE                            │
│                     POST /api/v1/ingest/upload                       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FORMAT VALIDATION                                 │
│                     (format_detector.py)                             │
│  ✓ Validate file format is supported                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    UPLOAD TO S3 RAW ZONE                             │
│                      (s3_service.py)                                 │
│  • Store file with metadata                                         │
│  • user_id, team_id, format, etc.                                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│             TRIGGER BEDROCK KB INGESTION JOB                         │
│            (kb_native_ingestion.py)                                  │
│  • StartIngestionJob API call                                       │
│  • KB scans S3 data source                                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│          BEDROCK KB NATIVE PROCESSING (Fully Managed)                │
├─────────────────────────────────────────────────────────────────────┤
│  1. BDA PARSING (Built-in - No Lambda!)                             │
│     • PDF, DOCX, images, videos, audio                              │
│     • Multimodal content extraction                                 │
│     • Native BDA integration in data source                         │
│                                                                      │
│  2. CHUNKING (Automatic)                                            │
│     • Fixed size chunking                                           │
│     • Configurable chunk size + overlap                             │
│                                                                      │
│  3. EMBEDDING GENERATION (Titan)                                    │
│     • Amazon Titan Embeddings v1/v2                                 │
│     • 1536 dimensions                                               │
│                                                                      │
│  4. INDEXING TO OPENSEARCH (Automatic)                              │
│     • Vector storage with KNN                                       │
│     • Metadata filtering support                                    │
│     • IAM-based access control                                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ✓ INGESTION COMPLETE                             │
│               Document ready for retrieval                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## What Was Removed

### ❌ **Components No Longer Needed**

1. **Lambda Functions** - No custom parsing logic needed
2. **Step Functions** - No orchestration state machine
3. **SQS Queues** - No retry/DLQ management
4. **Custom BDA Integration** - KB has built-in BDA
5. **Format-specific handlers** - BDA handles all formats
6. **Textract service** - BDA does OCR
7. **Transcribe service** - BDA does transcription
8. **Excel parser** - BDA handles spreadsheets
9. **CloudWatch custom metrics** - KB provides built-in metrics
10. **SNS alarms** - KB has native monitoring

---

## What AWS Manages for You

### ✅ **Bedrock KB Native Features**

#### **1. BDA Parsing (Built-in)**
- Configured at data source level
- Automatically detects file types
- Extracts text from all formats:
  - Documents: PDF, DOCX, PPTX, TXT, HTML
  - Images: JPG, PNG (OCR)
  - Audio: MP3, WAV (transcription)
  - Video: MP4, AVI (transcription)
  - Spreadsheets: XLSX, CSV
- No Lambda code required

#### **2. Automatic Chunking**
- Fixed-size chunking strategy
- Configurable chunk size (default: 300 tokens)
- Configurable overlap (default: 20%)
- Preserves context between chunks

#### **3. Embedding Generation**
- Amazon Titan Embeddings (default)
- Cohere embeddings (optional)
- Automatic batching
- Managed scaling

#### **4. Vector Indexing**
- OpenSearch Serverless integration
- Automatic index creation
- KNN vector search
- Metadata filtering
- Hybrid search (vector + keyword)

#### **5. Error Handling**
- Automatic retries
- Failed document tracking
- Per-document error reporting
- Ingestion job statistics

#### **6. Monitoring**
- CloudWatch metrics (built-in)
- Ingestion job status
- Document counts (scanned, indexed, failed)
- No custom metrics needed

---

## Setup Instructions

### **Step 1: Create Knowledge Base with BDA**

1. Go to AWS Console → Bedrock → Knowledge bases
2. Click "Create knowledge base"

3. **Configure KB:**
   - Name: `document-ingestion-kb`
   - Description: `Multi-format document ingestion`
   - IAM role: Auto-create or use existing

4. **Configure Data Source:**
   - Data source name: `s3-raw-documents`
   - Data source type: `S3`
   - S3 URI: `s3://your-raw-bucket/`
   
   **⭐ CRITICAL: Enable BDA Parsing**
   - Parsing strategy: `Bedrock Data Automation`
   - This is the key setting - KB will use BDA for all files

5. **Configure Vector Store:**
   - Vector database: `OpenSearch Serverless`
   - Create new collection: `kb-documents`
   - Index name: `document-embeddings`

6. **Configure Embeddings:**
   - Model: `Amazon Titan Embeddings G1 - Text`
   - Dimensions: 1536

7. **Review and Create**

8. **Copy IDs:**
   ```
   Knowledge Base ID: XYZABC123
   Data Source ID: ABCDEF456
   ```

---

### **Step 2: Configure Environment**

Edit `backend/config/.env`:

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# S3 Buckets
S3_RAW_BUCKET=your-raw-bucket-name
S3_PROCESSED_BUCKET=your-processed-bucket-name  # Not used in native flow

# Bedrock KB Configuration (REQUIRED)
BEDROCK_KB_ID=XYZABC123
BEDROCK_DATA_SOURCE_ID=ABCDEF456
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v1

# These are now OPTIONAL (not used in native flow)
# BEDROCK_DATA_AUTOMATION_JOB_ARN=...
# OPENSEARCH_ENDPOINT=...  # Auto-managed by KB
# STEP_FUNCTION_ARN=...  # Not needed
# SQS_DLQ_URL=...  # Not needed
# SQS_RETRY_QUEUE_URL=...  # Not needed
```

**Minimum Required:**
- AWS credentials
- S3 raw bucket
- BEDROCK_KB_ID
- BEDROCK_DATA_SOURCE_ID

---

### **Step 3: Start the Simplified API**

```bash
cd backend/api
python main_native.py
```

API runs at: `http://localhost:8000`

---

## API Endpoints

### **Upload File**
```bash
POST /api/v1/ingest/upload

# Upload and trigger KB ingestion
curl -X POST "http://localhost:8000/api/v1/ingest/upload?source=web_ui&user_id=user123" \
  -F "file=@document.pdf"

# Response:
{
  "message": "File uploaded successfully. KB ingestion started.",
  "s3_key": "web_ui/2026/06/16/123456/document.pdf",
  "s3_uri": "s3://my-bucket/web_ui/2026/06/16/123456/document.pdf",
  "ingestion_job_id": "JOB123456",
  "ingestion_status": "STARTING",
  "format": {
    "mime_type": "application/pdf",
    "category": "document"
  },
  "note": "Bedrock KB will automatically parse using BDA, chunk, embed, and index"
}
```

### **Check Ingestion Status**
```bash
GET /api/v1/ingest/status/{ingestion_job_id}

curl http://localhost:8000/api/v1/ingest/status/JOB123456

# Response:
{
  "ingestion_job_id": "JOB123456",
  "status": "COMPLETE",
  "statistics": {
    "documents_scanned": 1,
    "documents_indexed": 1,
    "documents_failed": 0
  }
}
```

### **List Recent Jobs**
```bash
GET /api/v1/ingest/jobs

curl http://localhost:8000/api/v1/ingest/jobs?max_results=10
```

### **Manual Trigger**
```bash
POST /api/v1/ingest/trigger

# Manually trigger KB to scan S3
curl -X POST http://localhost:8000/api/v1/ingest/trigger
```

### **Retrieve Documents**
```bash
POST /api/v1/retrieve

curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning best practices",
    "user_id": "user123",
    "max_results": 10
  }'
```

---

## Comparison: Old vs New

| Aspect | Old Architecture | New Architecture |
|--------|-----------------|------------------|
| **Lambda Functions** | 3-5 functions | **0 functions** ✅ |
| **Step Functions** | 1 state machine | **None** ✅ |
| **SQS Queues** | 2 queues (retry + DLQ) | **None** ✅ |
| **Custom Code** | Format handlers, orchestrator | **None** ✅ |
| **Parsing Logic** | Multiple services (Textract, Transcribe, Excel) | **BDA (built-in)** ✅ |
| **Error Handling** | Custom retry + DLQ | **KB managed** ✅ |
| **Monitoring** | Custom CloudWatch metrics | **KB metrics** ✅ |
| **Operational Overhead** | High | **Low** ✅ |
| **Cold Starts** | Yes (Lambda) | **None** ✅ |
| **Complexity** | High | **Low** ✅ |
| **Setup Time** | Hours | **Minutes** ✅ |
| **Cost** | Higher (Lambda invocations, Step Functions transitions) | **Lower** ✅ |

---

## Benefits

### 🚀 **Simplified Architecture**
- No Lambda functions to manage
- No Step Functions state machines
- No SQS queue configuration
- No custom orchestration logic
- Single API call triggers everything

### 💰 **Lower Costs**
- No Lambda invocations ($0.20 per million)
- No Step Functions transitions ($25 per million)
- No SQS message charges ($0.40 per million)
- Only pay for KB usage (document processing)

### ⚡ **Better Performance**
- No Lambda cold starts
- No Step Functions state transitions
- Native AWS service integration
- Optimized BDA processing

### 🔧 **Easier Maintenance**
- Less code to maintain
- Fewer components to monitor
- Native error handling
- Built-in retry logic

### 📊 **Built-in Monitoring**
- KB provides metrics out of the box
- Ingestion job statistics
- Document-level error tracking
- No custom dashboards needed

---

## Migration Path

### **From Old to New Architecture**

#### **Phase 1: Setup KB with BDA**
1. Create Knowledge Base
2. Configure S3 data source with BDA parsing
3. Create OpenSearch collection
4. Configure embeddings model

#### **Phase 2: Update Code**
1. Install new service: `kb_native_ingestion.py`
2. Switch API: `main.py` → `main_native.py`
3. Update .env with KB ID and data source ID

#### **Phase 3: Test**
1. Upload test files
2. Verify KB ingestion works
3. Test retrieval with access control
4. Monitor ingestion job statistics

#### **Phase 4: Decommission Old**
1. Stop old API (`main.py`)
2. Delete Lambda functions (optional)
3. Delete Step Functions state machine (optional)
4. Delete SQS queues (optional)
5. Remove old services (optional - keep for reference)

---

## IAM Permissions

### **Required Permissions**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-raw-bucket",
        "arn:aws:s3:::your-raw-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:Retrieve"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:StartIngestionJob",
        "bedrock:GetIngestionJob",
        "bedrock:ListIngestionJobs",
        "bedrock:Retrieve"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:knowledge-base/*"
      ]
    }
  ]
}
```

**No longer needed:**
- Lambda execution role
- Step Functions execution role
- SQS send/receive permissions
- Textract permissions
- Transcribe permissions

---

## Monitoring

### **KB Provides Built-in Metrics**

1. **Ingestion Job Status:**
   - `STARTING` → `IN_PROGRESS` → `COMPLETE` / `FAILED`

2. **Document Statistics:**
   - Documents scanned
   - Documents indexed
   - Documents failed
   - Indexing failures (with reasons)

3. **CloudWatch Metrics (Auto-created):**
   - `IngestedDocuments`
   - `FailedDocuments`
   - `IndexingDuration`

4. **Access via API:**
   ```python
   kb_native_ingestion.get_ingestion_job_status(job_id)
   ```

---

## Troubleshooting

### **Issue: "Knowledge Base not found"**
**Solution:** Check BEDROCK_KB_ID in .env matches your KB ID

### **Issue: "Data source not found"**
**Solution:** Check BEDROCK_DATA_SOURCE_ID in .env

### **Issue: "Documents not indexed"**
**Solution:**
1. Check S3 permissions (KB needs read access)
2. Verify BDA is enabled in data source settings
3. Check ingestion job status for error details

### **Issue: "Retrieval returns no results"**
**Solution:**
1. Wait for ingestion to complete (check status)
2. Verify metadata filters (user_id, team_id)
3. Test with broader query

---

## Automatic Ingestion (Optional)

### **Schedule-based Sync**

KB can automatically scan S3 on a schedule:

1. Go to KB → Data Sources → Edit
2. Enable "Sync schedule"
3. Choose frequency: Hourly, Daily, Weekly
4. KB will automatically ingest new/updated files

### **Event-driven (Advanced)**

For real-time ingestion:

1. S3 → EventBridge → Lambda (tiny trigger function)
2. Lambda calls `start_ingestion_job()`
3. KB ingests the file

But for most use cases, schedule-based sync is sufficient!

---

## Cost Estimate

### **New Architecture Costs**

| Service | Usage | Cost |
|---------|-------|------|
| S3 Storage | 100 GB | $2.30/month |
| Bedrock KB Ingestion | 1000 documents | $3.00 |
| Titan Embeddings | 1M tokens | $0.10 |
| OpenSearch Serverless | OCU hours | $7.20/day |
| **Total** | | **~$250/month** |

**Savings vs Old Architecture:**
- No Lambda costs ✅
- No Step Functions costs ✅
- No SQS costs ✅
- Estimated savings: **30-40%**

---

## Next Steps

1. ✅ Create Knowledge Base with BDA in AWS Console
2. ✅ Copy KB ID and Data Source ID
3. ✅ Update `backend/config/.env`
4. ✅ Start simplified API: `python main_native.py`
5. ✅ Test upload via frontend or curl
6. ✅ Monitor ingestion jobs
7. ✅ Test retrieval

The architecture is now **production-ready and simplified**! 🎉
