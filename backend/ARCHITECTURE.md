# Architecture Documentation

## System Overview

Simplified multi-source knowledge base with automatic metadata extraction, powered by AWS Bedrock.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Web Upload  │  │ Google Drive │  │    Query     │          │
│  │  Interface   │  │    Picker    │  │  Interface   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                   │                  │
└─────────┼─────────────────┼───────────────────┼──────────────────┘
          │                 │                   │
          └─────────────────┴───────────────────┘
                            │
                   ┌────────▼────────┐
                   │   HTTPS / REST  │
                   └────────┬────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                      Backend Layer                                │
│                    FastAPI Application                            │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    API Endpoints                           │  │
│  │                                                            │  │
│  │  • POST /api/upload/direct                                │  │
│  │  • POST /api/upload/get-presigned-url                     │  │
│  │  • POST /api/google-drive/import                          │  │
│  │  • POST /api/kb/sync                                      │  │
│  │  • POST /api/kb/query                                     │  │
│  │  • GET  /api/documents                                    │  │
│  │  • GET  /api/metadata/{s3_key}                            │  │
│  └────────────────────────────────────────────────────────────┘  │
│                            │                                      │
│  ┌─────────────────────────┼────────────────────────────────┐   │
│  │          Service Layer                                    │   │
│  │                         │                                 │   │
│  │  ┌──────────────┐  ┌───▼────────────┐  ┌──────────────┐ │   │
│  │  │   Metadata   │  │     Upload     │  │  KB Query    │ │   │
│  │  │  Extractor   │  │    Service     │  │   Service    │ │   │
│  │  │              │  │                │  │              │ │   │
│  │  │ • PDF        │  │ • Pre-signed   │  │ • Retrieve   │ │   │
│  │  │ • DOCX       │  │   URLs         │  │ • Filter     │ │   │
│  │  │ • Images     │  │ • Direct       │  │ • Access     │ │   │
│  │  │ • EXIF       │  │   upload       │  │   control    │ │   │
│  │  └──────────────┘  │ • KB sync      │  └──────────────┘ │   │
│  │                    └────────────────┘                    │   │
│  │                                                           │   │
│  │  ┌──────────────────────────────────────────────┐       │   │
│  │  │       Google Drive Service                    │       │   │
│  │  │       • OAuth authentication                  │       │   │
│  │  │       • File download                         │       │   │
│  │  └──────────────────────────────────────────────┘       │   │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                      │
└────────────────────────────┼──────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │                                        │
┌───────▼────────┐                    ┌─────────▼────────┐
│  Google Drive  │                    │    Amazon S3     │
│      API       │                    │                  │
│                │                    │  Bucket Structure:│
│ • OAuth 2.0    │                    │  └── users/      │
│ • File list    │                    │      ├── user1/  │
│ • Download     │                    │      │   └── ... │
└────────────────┘                    │      └── user2/  │
                                      │          └── ... │
                                      │                  │
                                      │  Object Metadata:│
                                      │  • user_id       │
                                      │  • author        │
                                      │  • title         │
                                      │  • tags          │
                                      └──────┬───────────┘
                                             │
                                    (Auto-sync: Hourly)
                                             │
                        ┌────────────────────▼────────────────────┐
                        │   AWS Bedrock Knowledge Base            │
                        │                                          │
                        │  ┌────────────────────────────────────┐ │
                        │  │   Bedrock Data Automation (BDA)    │ │
                        │  │                                    │ │
                        │  │  • PDF text extraction             │ │
                        │  │  • DOCX/PPTX parsing              │ │
                        │  │  • Image OCR                      │ │
                        │  │  • Video transcription            │ │
                        │  │  • Audio transcription            │ │
                        │  └────────────────────────────────────┘ │
                        │             │                            │
                        │  ┌──────────▼─────────────────────────┐ │
                        │  │      Content Processing            │ │
                        │  │                                    │ │
                        │  │  • Intelligent chunking            │ │
                        │  │  • Metadata indexing              │ │
                        │  │  • Context preservation           │ │
                        │  └────────────────────────────────────┘ │
                        │             │                            │
                        │  ┌──────────▼─────────────────────────┐ │
                        │  │   Embedding Generation             │ │
                        │  │   (Amazon Titan Embeddings)        │ │
                        │  │                                    │ │
                        │  │  • 1536-dimensional vectors        │ │
                        │  │  • Semantic representation         │ │
                        │  └────────────────────────────────────┘ │
                        │             │                            │
                        │  ┌──────────▼─────────────────────────┐ │
                        │  │    Managed Vector Store            │ │
                        │  │    (OpenSearch Serverless)         │ │
                        │  │                                    │ │
                        │  │  • K-NN indexing                   │ │
                        │  │  • Metadata filtering              │ │
                        │  │  • Hybrid search                   │ │
                        │  └────────────────────────────────────┘ │
                        │                                          │
                        └──────────────┬───────────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  Query Results  │
                              │  with Citations │
                              └─────────────────┘
```

---

## Component Details

### 1. Frontend Layer

**Responsibilities:**
- File selection and upload
- Google Drive integration (OAuth + Picker)
- Query interface
- Results display

**Technologies:**
- React/Vue.js (recommended)
- Google Picker API
- Axios/Fetch for API calls

### 2. Backend Layer (FastAPI)

**Responsibilities:**
- Upload coordination
- Metadata extraction
- Google Drive file download
- KB sync management
- Query orchestration
- Access control

**Key Files:**
- `api/app.py` - Main application
- `services/upload_service.py` - S3 & sync
- `services/metadata_extractor.py` - Auto extraction
- `services/kb_query_service.py` - Query & filter
- `services/google_drive_service.py` - Drive API

### 3. Storage Layer (S3)

**Structure:**
```
s3://my-kb-bucket/
└── users/
    ├── user123/
    │   ├── 2024/06/16/143000/
    │   │   ├── document1.pdf
    │   │   └── presentation.pptx
    │   └── 2024/06/17/091500/
    │       └── image.jpg
    └── user456/
        └── 2024/06/16/150000/
            └── video.mp4
```

**Metadata Storage:**
Each S3 object has metadata:
```json
{
  "user_id": "user123",
  "team_id": "team456",
  "department": "Engineering",
  "author": "John Doe",
  "title": "Project Proposal",
  "creation_date": "2024-01-15",
  "tags": "proposal,budget,2024",
  "source": "web_ui"
}
```

### 4. Processing Layer (Bedrock KB)

**Auto-processing includes:**

| Input Format | BDA Processing | Output |
|-------------|----------------|---------|
| PDF | Text extraction + metadata | Structured text chunks |
| DOCX | Document parsing | Text + formatting |
| PPTX | Slide text extraction | Text per slide |
| Images | OCR (Textract) | Extracted text |
| Videos | Transcribe audio | Text transcript |
| Audio | Transcribe | Text transcript |

**Chunking Strategy:**
- Default: 300 tokens per chunk
- Overlap: 20% (60 tokens)
- Preserves context across chunks

**Embeddings:**
- Model: Amazon Titan Embeddings G1
- Dimensions: 1536
- Type: Dense vectors

### 5. Vector Store

**Managed by Bedrock KB:**
- OpenSearch Serverless (auto-scaled)
- K-NN indexing for similarity search
- Metadata filtering support
- High availability

---

## Data Flow Diagrams

### Upload Flow (Web UI)

```
┌─────────┐
│  User   │
└────┬────┘
     │ 1. Select file
     ▼
┌─────────────┐
│  Frontend   │
└────┬────────┘
     │ 2. POST /api/upload/direct
     │    (file + metadata)
     ▼
┌──────────────────┐
│  Backend API     │
│  ┌────────────┐  │
│  │ Extract    │  │ 3. Extract metadata
│  │ Metadata   │  │    (author, title, etc.)
│  └────────────┘  │
└────┬─────────────┘
     │ 4. Upload to S3 (with metadata)
     ▼
┌─────────────┐
│     S3      │
└─────────────┘
     │ 5. Auto-sync (hourly)
     ▼
┌─────────────┐
│ Bedrock KB  │ 6. BDA processing
└─────────────┘    Chunking, embeddings
     │ 7. Index
     ▼
┌─────────────┐
│ Vector DB   │
└─────────────┘
```

### Google Drive Import Flow

```
┌─────────┐
│  User   │
└────┬────┘
     │ 1. Click "Import from Drive"
     ▼
┌─────────────┐
│  Frontend   │
└────┬────────┘
     │ 2. Google OAuth popup
     ▼
┌─────────────┐
│  Google     │ 3. User authenticates
│  OAuth      │    Grants permissions
└────┬────────┘
     │ 4. Returns access token
     ▼
┌─────────────┐
│  Frontend   │ 5. Opens Google Picker
└────┬────────┘    User selects files
     │ 6. POST /api/google-drive/import
     │    (file IDs + token)
     ▼
┌──────────────────┐
│  Backend API     │
│  ┌────────────┐  │ 7. Download from Drive
│  │  Google    │  │    using token
│  │  Drive API │  │
│  └────────────┘  │
│  ┌────────────┐  │ 8. Extract metadata
│  │  Metadata  │  │
│  │  Extractor │  │
│  └────────────┘  │
└────┬─────────────┘
     │ 9. Upload to S3
     ▼
┌─────────────┐
│     S3      │
└─────────────┘
     │ 10. Auto-sync
     ▼
┌─────────────┐
│ Bedrock KB  │
└─────────────┘
```

### Query Flow

```
┌─────────┐
│  User   │
└────┬────┘
     │ 1. Enter query
     ▼
┌─────────────┐
│  Frontend   │
└────┬────────┘
     │ 2. POST /api/kb/query
     │    {query, user_id, team_id}
     ▼
┌──────────────────┐
│  Backend API     │
│  ┌────────────┐  │ 3. Build metadata filter
│  │ KB Query   │  │    (user_id OR team_id)
│  │ Service    │  │
│  └────────────┘  │
└────┬─────────────┘
     │ 4. bedrock_agent.retrieve()
     │    with filter
     ▼
┌─────────────────┐
│  Bedrock KB     │ 5. Semantic search
│                 │    + metadata filter
│  ┌───────────┐  │
│  │ Vector DB │  │ 6. K-NN search
│  └───────────┘  │
└────┬────────────┘
     │ 7. Retrieve top-K chunks
     ▼
┌──────────────────┐
│  Backend API     │ 8. Format results
└────┬─────────────┘
     │ 9. Return results + metadata
     ▼
┌─────────────┐
│  Frontend   │ 10. Display results
└─────────────┘     with citations
```

---

## Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────────────────┐
│               Frontend Layer                     │
│  • User login (your auth system)                │
│  • Session management                           │
│  • Google OAuth (for Drive)                     │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼ Bearer token / Session
┌─────────────────────────────────────────────────┐
│               Backend Layer                      │
│  • Validate user session                        │
│  • Extract user_id                              │
│  • Add to all operations                        │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼ user_id in metadata
┌─────────────────────────────────────────────────┐
│                   S3 Layer                       │
│  • Files organized by user_id                   │
│  • Metadata includes user_id, team_id           │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              Bedrock KB Layer                    │
│  • Retrieval filtered by user_id                │
│  • Can only see own + team documents            │
└─────────────────────────────────────────────────┘
```

### Access Control Patterns

**User Isolation:**
```python
filter = {'equals': {'key': 'user_id', 'value': current_user}}
# User only sees their documents
```

**Team Sharing:**
```python
filter = {
    'orAll': [
        {'equals': {'key': 'user_id', 'value': current_user}},
        {'equals': {'key': 'team_id', 'value': user_team}}
    ]
}
# User sees their docs + team docs
```

**Department Access:**
```python
filter = {'equals': {'key': 'department', 'value': user_dept}}
# All department members see department docs
```

---

## Scalability

### Current Architecture Scales:

| Component | Max Scale |
|-----------|-----------|
| **S3** | Unlimited objects |
| **Bedrock KB** | Millions of documents |
| **Backend API** | Horizontal scaling (add instances) |
| **Vector Store** | Auto-scales (managed) |

### Scaling Strategy:

1. **Low traffic** (< 100 users):
   - Single backend instance
   - On-demand KB sync

2. **Medium traffic** (100-1000 users):
   - Auto-scaling backend (2-5 instances)
   - Hourly KB sync
   - CloudFront CDN for API

3. **High traffic** (1000+ users):
   - Load balanced backend cluster
   - Multiple KB instances (per region)
   - Continuous sync
   - Edge caching

---

## Monitoring & Observability

### What to Monitor:

1. **Upload Success Rate**
   - Track failed uploads
   - Alert if > 5% fail

2. **KB Sync Status**
   - Monitor ingestion jobs
   - Alert if job fails

3. **Query Latency**
   - P50, P95, P99 response times
   - Target: < 500ms

4. **Metadata Extraction**
   - Success rate per format
   - Track errors

### Logging Strategy:

```python
# Application logs
logger.info(f"File uploaded: {filename} by {user_id}")
logger.error(f"Metadata extraction failed: {error}")

# Access logs
logger.info(f"Query: {query} by {user_id} returned {count} results")

# Performance logs
logger.info(f"Upload took {duration}ms")
```

---

## Cost Optimization

### Current Cost Drivers:

1. **Bedrock KB** (40-50% of cost)
   - Ingestion: $0.10 per 1000 docs
   - Storage: $0.30 per GB/month
   - Query: $0.002 per query

2. **Bedrock Embeddings** (20-30%)
   - Titan: $0.0001 per 1000 tokens

3. **S3** (5-10%)
   - Storage: $0.023 per GB/month
   - Requests: minimal

4. **Backend** (10-20%)
   - EC2/Fargate: $15-50/month

### Optimization Tips:

- Use on-demand sync (not hourly) for low-traffic
- Implement caching for frequent queries
- Use S3 Intelligent-Tiering for old files
- Batch uploads when possible
- Monitor and set budget alerts

---

## Disaster Recovery

### Backup Strategy:

1. **S3 Versioning**: Enabled
2. **Cross-region replication**: Optional
3. **KB snapshot**: Not needed (can rebuild from S3)

### Recovery Plan:

1. **S3 data loss**: Restore from versioning
2. **KB corruption**: Recreate KB, trigger full sync
3. **Backend failure**: Deploy new instance (stateless)

### RTO/RPO:

- **RTO** (Recovery Time): 30 minutes
- **RPO** (Recovery Point): 0 (S3 versioning)

---

## Future Enhancements

### Potential Additions:

1. **Real-time sync**: S3 event → Lambda → immediate KB sync
2. **Advanced analytics**: Query patterns, popular documents
3. **Multi-language**: Tamil/Sinhala support (Transcribe → Translate)
4. **Scheduled ingestion**: Automated imports from external sources
5. **Document versioning**: Track changes over time
6. **Collaborative features**: Comments, annotations
7. **Advanced search**: Filters, date ranges, fuzzy search

### Not Recommended:

- ❌ Custom embedding models (Titan works well)
- ❌ Self-hosted vector DB (managed is better)
- ❌ Complex orchestration (keep it simple)

---

## Comparison with Alternatives

### vs. Lambda-based Architecture:

| Aspect | This (Bedrock KB) | Lambda-based |
|--------|------------------|--------------|
| **Complexity** | Low | High |
| **Components** | 2 (S3 + KB) | 12+ |
| **Maintenance** | Minimal | High |
| **Cost** | $60-140/mo | $140-385/mo |
| **Latency** | 2-10 min (sync) | Real-time |
| **Scalability** | Auto | Manual |

### vs. OpenAI + Pinecone:

| Aspect | This (Bedrock KB) | OpenAI + Pinecone |
|--------|------------------|-------------------|
| **AWS native** | Yes | No |
| **Setup** | Simpler | More config |
| **Cost** | Similar | Similar |
| **Vendor lock-in** | AWS | Multi-vendor |

---

## Summary

**This architecture is optimized for:**
- ✅ Simplicity (2 main components)
- ✅ Cost-effectiveness (60% cheaper than Lambda)
- ✅ Maintainability (minimal code)
- ✅ Scalability (managed services)
- ✅ Security (metadata-based access control)

**Trade-offs:**
- ⏱️ Slightly slower (sync vs real-time)
- 🔒 Less customization (managed service)

**Best for:**
- Internal knowledge bases
- Document management systems
- Multi-tenant SaaS applications
- Customer support portals

---

**Questions? Check README.md or SETUP_GUIDE.md!**
