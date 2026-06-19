# BDA Knowledge Base Ingestion Pipeline

Production-grade AWS ingestion pipeline with Bedrock Data Automation, Knowledge Base, and OpenSearch, featuring a stunning 3D React frontend.

## Architecture

```
Sources → S3 Raw → Step Functions → BDA Parser → S3 Processed → Knowledge Base → OpenSearch → Retrieval
                                       ↓ (failure)
                                  Retry Queue → DLQ
```

## Project Structure

```
demo/
├── backend/              # Python FastAPI backend
│   ├── config/          # Settings and environment
│   ├── services/        # AWS service integrations
│   ├── orchestrator/    # Pipeline orchestration
│   ├── api/            # REST API endpoints
│   └── utils/          # Utilities
│
└── frontend/            # React 3D frontend
    ├── src/
    │   ├── components/ # Reusable components
    │   ├── pages/     # Page components
    │   └── App.js
    └── package.json
```

## Features

### Backend
- ✅ Multi-source ingestion (Web UI, Shared Drive, File Repo, S3)
- ✅ Bedrock Data Automation for multimodal parsing
- ✅ Step Functions orchestration
- ✅ Retry logic with exponential backoff
- ✅ Dead-letter queue handling
- ✅ Knowledge Base ingestion
- ✅ OpenSearch vector store
- ✅ IAM + metadata-based access control
- ✅ CloudWatch monitoring and alarms

### Frontend
- ✅ Real-time Dashboard with Live Metrics
- ✅ Drag-and-drop File Upload
- ✅ Document Retrieval with Filtering
- ✅ Monitoring and Metrics
- ✅ Modern Clean UI Design
- ✅ Responsive Layout

## Quick Start

### Backend Setup

1. **Navigate to backend**
   ```bash
   cd backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example config/.env
   # Edit config/.env with your AWS credentials
   ```

4. **Run the API**
   ```bash
   cd api
   python main.py
   ```

   Backend runs at `http://localhost:8001`

### Frontend Setup

1. **Navigate to frontend**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start the app**
   ```bash
   npm start
   ```

   Frontend runs at `http://localhost:3000`

## API Documentation

Once the backend is running, visit:
- API Docs: `http://localhost:8001/docs`
- Interactive API: `http://localhost:8001/redoc`

## Environment Configuration

Edit `backend/config/.env`:

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# S3 Buckets
S3_RAW_BUCKET=your-raw-bucket
S3_PROCESSED_BUCKET=your-processed-bucket

# Bedrock
BEDROCK_DATA_AUTOMATION_JOB_ARN=arn:aws:bedrock:...
BEDROCK_KB_ID=your-kb-id

# OpenSearch
OPENSEARCH_ENDPOINT=https://your-domain.region.es.amazonaws.com

# Step Functions
STEP_FUNCTION_ARN=arn:aws:states:...

# SQS
SQS_DLQ_URL=https://sqs.region.amazonaws.com/account/dlq
```

## Usage Examples

### Upload a Document (Frontend)

1. Go to Upload page
2. Drag and drop a file or click to browse
3. Select source type
4. Enter User ID (required) and Team ID (optional)
5. Click "Upload & Start Ingestion"

### Search Documents (Frontend)

1. Go to Retrieve page
2. Enter your search query
3. Provide User ID (required for access control)
4. Click "Search Knowledge Base"
5. View results with metadata

### Monitor Pipeline (Frontend)

1. Go to Monitoring page
2. View real-time execution status
3. Check DLQ message counts
4. Filter executions by status

### Upload via API (Python)

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
        'http://localhost:8001/api/v1/ingest/upload',
        files=files,
        params=params
    )
    print(response.json())
```

### Retrieve via API (Python)

```python
import requests

payload = {
    'query': 'machine learning best practices',
    'user_id': 'user123',
    'team_id': 'team456',
    'max_results': 10
}

response = requests.post(
    'http://localhost:8001/api/v1/retrieve',
    json=payload
)
print(response.json())
```

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

## Development

### Backend Structure

```
backend/
├── config/settings.py       # Configuration management
├── services/
│   ├── s3_service.py       # S3 operations
│   ├── bedrock_service.py  # BDA + Knowledge Base
│   ├── opensearch_service.py # Vector store
│   ├── stepfunctions_service.py
│   ├── sqs_service.py      # Retry + DLQ
│   └── monitoring_service.py # CloudWatch
├── orchestrator/
│   └── pipeline_orchestrator.py # Main pipeline logic
└── api/main.py             # FastAPI endpoints
```

### Frontend Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── Sidebar.jsx
│   └── pages/
│       ├── Dashboard.jsx
│       ├── Upload.jsx
│       ├── Retrieve.jsx
│       └── Monitoring.jsx
```

## Troubleshooting

### Backend Issues

- Verify AWS credentials in `config/.env`
- Check all ARNs and endpoints are correct
- Ensure S3 buckets exist
- Verify IAM permissions for all services

### Frontend Issues

- Make sure backend is running on port 8001
- Check browser console for errors
- Clear browser cache if styles don't load
- Verify CORS settings if API calls fail

## Technologies

### Backend
- Python 3.8+
- FastAPI
- Boto3 (AWS SDK)
- OpenSearch Python Client
- Pydantic

### Frontend
- React 18
- React Router
- Tailwind CSS
- Axios
- Lucide Icons

## License

MIT

## Support

For issues and questions:
- Backend: Check `backend/README.md`
- Frontend: Check `frontend/README.md`
- Architecture: See SVG diagram
