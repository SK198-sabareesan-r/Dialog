# Quick Reference Card

## Essential Commands

### Start Server
```bash
python api/app.py
```
Server: http://localhost:8000  
Docs: http://localhost:8000/docs

### Test Upload
```bash
curl -X POST http://localhost:8000/api/upload/direct \
  -F "file=@test.pdf" \
  -F "user_id=user123"
```

### Trigger Sync
```bash
curl -X POST http://localhost:8000/api/kb/sync \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

### Query KB
```bash
curl -X POST http://localhost:8000/api/kb/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "user_id": "user123", "max_results": 5}'
```

---

## Required Configuration (.env)

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_RAW_BUCKET=your-bucket
BEDROCK_KB_ID=your_kb_id
BEDROCK_DATA_SOURCE_ID=your_ds_id
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/` | Health check |
| `POST` | `/api/upload/direct` | Upload file |
| `POST` | `/api/upload/get-presigned-url` | Get S3 upload URL |
| `POST` | `/api/google-drive/import` | Import from Drive |
| `POST` | `/api/kb/sync` | Trigger KB sync |
| `GET` | `/api/kb/sync/status/{id}` | Check sync status |
| `POST` | `/api/kb/query` | Query KB |
| `GET` | `/api/documents?user_id=X` | List documents |
| `GET` | `/api/metadata/{s3_key}` | Get file metadata |
| `GET` | `/api/supported-formats` | List formats |

---

## Supported Formats

✅ PDF, DOCX, PPTX, XLSX  
✅ JPG, PNG  
✅ MP4, AVI  
✅ MP3, WAV  
✅ TXT, HTML, MD  

All processed by Bedrock KB with BDA!

---

## Architecture Flow

```
Upload → S3 → Bedrock KB → Query
```

That's it! No Lambda, no Step Functions, no SQS.

---

## Metadata Extraction

**Automatic extraction:**
- PDF: author, title, keywords, page count
- DOCX: author, title, company, creation date
- Images: EXIF data (camera, location, timestamp)
- Videos: Transcription (by Bedrock KB)

**Custom metadata:**
- user_id, team_id, department, tags

---

## Troubleshooting

### Files not queryable?
1. Check sync status: `GET /api/kb/sync/status/{job_id}`
2. Wait 5-10 minutes for processing
3. Trigger manual sync: `POST /api/kb/sync`

### Metadata not extracted?
```bash
pip install PyPDF2 python-docx Pillow
```

### Access denied?
```bash
aws sts get-caller-identity
```
Check IAM permissions: S3 + Bedrock

---

## AWS Setup

### Create S3 Bucket
```bash
aws s3 mb s3://my-kb-bucket
```

### Create Knowledge Base
1. AWS Console → Bedrock → Knowledge bases
2. Create with S3 data source
3. Copy KB ID and Data Source ID to `.env`

---

## Python Code Examples

### Upload
```python
import requests

with open('file.pdf', 'rb') as f:
    requests.post(
        'http://localhost:8000/api/upload/direct',
        files={'file': f},
        data={'user_id': 'user123'}
    )
```

### Query
```python
import requests

response = requests.post(
    'http://localhost:8000/api/kb/query',
    json={
        'query': 'project proposal',
        'user_id': 'user123',
        'max_results': 10
    }
)
print(response.json())
```

---

## Google Drive Setup

1. Create Google Cloud project
2. Enable Drive API + Picker API
3. Create OAuth credentials
4. Add Client ID/Secret to `.env`
5. Frontend uses Google Picker to select files
6. Backend downloads and uploads to S3

---

## Cost Estimate

| Service | Cost/month |
|---------|-----------|
| S3 (10GB) | $0.23 |
| Bedrock KB | $30-80 |
| Queries (1K/day) | $30-60 |
| **Total** | **$60-140** |

Much cheaper than Lambda + OpenSearch!

---

## Key Files

```
backend/
├── api/app.py                      # Main API
├── services/
│   ├── upload_service.py           # S3 + KB sync
│   ├── metadata_extractor.py       # Extract metadata
│   ├── kb_query_service.py         # Query KB
│   └── google_drive_service.py     # Drive import
├── config/
│   ├── settings.py                 # Config loader
│   └── .env                        # Your credentials
├── requirements.txt                # Dependencies
├── README.md                       # Full docs
├── SETUP_GUIDE.md                  # Setup steps
└── QUICK_REFERENCE.md              # This file
```

---

## Access Control

Query filters documents by metadata:

```python
# User isolation
metadata_filter = {
    'equals': {'key': 'user_id', 'value': 'user123'}
}

# Team sharing
metadata_filter = {
    'orAll': [
        {'equals': {'key': 'user_id', 'value': 'user123'}},
        {'equals': {'key': 'team_id', 'value': 'team456'}}
    ]
}
```

---

## Testing Workflow

1. Upload: `POST /api/upload/direct`
2. Sync: `POST /api/kb/sync`
3. Wait: 5 minutes
4. Query: `POST /api/kb/query`
5. ✅ Should return your document

---

## Production Checklist

- [ ] Update CORS in `app.py`
- [ ] Use AWS Secrets Manager (not .env)
- [ ] Enable CloudWatch logs
- [ ] Set up auto-scaling
- [ ] Configure S3 backup
- [ ] Test with production data

---

## Need Help?

- Docs: `README.md` (full guide)
- Setup: `SETUP_GUIDE.md` (step-by-step)
- Changes: `CHANGES.md` (what's new)
- API: http://localhost:8000/docs (interactive)

---

**That's all you need to know! 🚀**
