# Knowledge Base Backend - Simplified Architecture

## Overview

Simplified backend for multi-source document ingestion with **automatic metadata extraction**, powered by **AWS Bedrock Knowledge Base**.

### Key Features

✅ **Multi-format support**: PDF, DOCX, PPTX, Excel, Images, Videos, Audio  
✅ **Multi-source ingestion**: Web UI upload, Google Drive, S3  
✅ **Automatic metadata extraction**: From file properties (author, date, EXIF, etc.)  
✅ **Access control**: User/team/department-based filtering  
✅ **No Lambda required**: Direct S3 → Bedrock KB flow  
✅ **Fully managed**: Bedrock KB handles parsing, chunking, embeddings, vector storage  

---

## Architecture

```
Frontend (Web UI / Google Drive Picker)
            ↓
    FastAPI Backend
    ├── Upload Service
    ├── Metadata Extractor  (Automatic: PDF, DOCX, Images, etc.)
    ├── Google Drive Service
    └── KB Query Service
            ↓
      Amazon S3 (with metadata)
            ↓ (Auto-sync)
  Bedrock Knowledge Base
    ├── BDA Parsing (all formats)
    ├── Video transcription
    ├── Image OCR
    ├── Chunking
    ├── Embeddings (Titan)
    └── Vector indexing
            ↓
    Query with Filtering
    (user_id, team_id, department)
```

**What's NOT included:**
- ❌ Lambda functions
- ❌ Step Functions
- ❌ SQS queues
- ❌ SNS alarms
- ❌ Self-managed OpenSearch

**Why? Bedrock KB handles everything internally!**

---

## Project Structure

```
demo/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Settings loaded from .env
│   └── .env                 # Environment variables (create from .env.example)
├── services/
│   ├── __init__.py
│   ├── aws_client.py        # AWS client manager
│   ├── s3_service.py        # S3 operations
│   ├── bedrock_service.py   # BDA and Knowledge Base
│   ├── opensearch_service.py # Vector store operations
│   ├── stepfunctions_service.py # Orchestration
│   ├── sqs_service.py       # Retry and DLQ
│   └── monitoring_service.py # CloudWatch metrics and alarms
├── orchestrator/
│   ├── __init__.py
│   └── pipeline_orchestrator.py # Main pipeline logic
├── api/
│   └── main.py              # FastAPI REST API
├── utils/
│   ├── __init__.py
│   └── logger.py            # Logging configuration
├── .env.example             # Example environment variables
├── requirements.txt         # Python dependencies
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `config/.env` and fill in your AWS credentials and resource ARNs:

```bash
cp .env.example config/.env
```

Edit `config/.env` with your AWS configuration:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

S3_RAW_BUCKET=your-raw-bucket-name
S3_PROCESSED_BUCKET=your-processed-bucket-name

BEDROCK_DATA_AUTOMATION_JOB_ARN=arn:aws:bedrock:...
BEDROCK_KB_ID=your-knowledge-base-id
OPENSEARCH_ENDPOINT=https://your-domain.region.es.amazonaws.com

STEP_FUNCTION_ARN=arn:aws:states:...
SQS_DLQ_URL=https://sqs.region.amazonaws.com/account/ingestion-dlq
```

### 3. Run the API Server

```bash
cd api
python main.py
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## API Endpoints

### Upload and Ingest
```bash
POST /api/v1/ingest/upload
- Upload file to raw zone and trigger ingestion
- Body: multipart/form-data with file
- Query params: source, user_id, team_id
```

### Start Ingestion
```bash
POST /api/v1/ingest/start
- Start ingestion for existing S3 file
- Body: {"source_key": "...", "source_type": "...", "metadata": {...}}
```

### Check Status
```bash
GET /api/v1/ingest/status/{execution_arn}
- Get status of ingestion execution
```

### List Executions
```bash
GET /api/v1/ingest/executions?status=RUNNING&max_results=20
- List recent executions
```

### Retrieve Documents
```bash
POST /api/v1/retrieve
- Query knowledge base with access control
- Body: {"query": "...", "user_id": "...", "team_id": "...", "max_results": 10}
```

### Monitor DLQ
```bash
GET /api/v1/monitoring/dlq
- Get dead-letter queue status
```

### View Metrics
```bash
GET /api/v1/monitoring/metrics?metric_name=IngestionSuccess&hours=24
- Get CloudWatch metrics
```

## Usage Examples

### Upload a file via Web UI

```python
import requests

with open('document.pdf', 'rb') as f:
    files = {'file': f}
    params = {
        'source': 'web_ui',
        'user_id': 'user123',
        'team_id': 'team456'
    }
    response = requests.post(
        'http://localhost:8000/api/v1/ingest/upload',
        files=files,
        params=params
    )
    print(response.json())
```

### Retrieve documents with access control

```python
import requests

payload = {
    'query': 'machine learning best practices',
    'user_id': 'user123',
    'team_id': 'team456',
    'max_results': 10
}

response = requests.post(
    'http://localhost:8000/api/v1/retrieve',
    json=payload
)
print(response.json())
```

## Services

### S3 Service
- Upload to raw zone with metadata
- Save processed output
- Copy between buckets

### Bedrock Service
- Invoke Data Automation for multimodal parsing
- Ingest to Knowledge Base
- Retrieve with metadata filtering

### OpenSearch Service
- Create vector index
- Index documents with embeddings
- KNN search with filters

### Step Functions Service
- Start/stop executions
- Monitor execution status
- List executions

### SQS Service
- Retry queue with exponential backoff
- Dead-letter queue for exhausted retries
- Message count monitoring

### Monitoring Service
- CloudWatch metrics
- SNS alarms
- DLQ threshold alerts

## Configuration

All configuration is loaded from `config/.env`:

- **AWS credentials**: Access key, secret key, region
- **S3 buckets**: Raw and processed zones
- **Bedrock**: Data Automation job ARN, Knowledge Base ID, embedding model
- **OpenSearch**: Endpoint and index name
- **Step Functions**: State machine ARN
- **SQS**: DLQ and retry queue URLs
- **CloudWatch**: Log group and alarm topic
- **Application**: Retry attempts, chunk size, overlap

## Monitoring

### CloudWatch Metrics

- `IngestionSuccess`: Successful ingestions by source
- `IngestionFailure`: Failed ingestions by error type
- `ProcessingDuration`: Processing time by stage
- `DLQMessageCount`: Messages in dead-letter queue

### Alarms

- DLQ threshold exceeded (>10 messages)
- Individual ingestion failures
- Sent via SNS to configured topic

## Error Handling

1. **Retry Logic**: Exponential backoff (2^n * 60s, max 900s)
2. **Max Retries**: 3 attempts (configurable)
3. **Dead Letter Queue**: Failed items after retry exhaustion
4. **Alarms**: SNS notifications on DLQ threshold

## Access Control

Documents are retrieved with IAM + metadata-based filtering:

- User-level: Filter by `user_id`
- Team-level: Filter by `team_id`
- Custom metadata: Extensible filtering

## License

MIT
