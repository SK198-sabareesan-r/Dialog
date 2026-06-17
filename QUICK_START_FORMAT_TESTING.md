# Quick Start: Testing Format Handlers

## Prerequisites

1. AWS credentials configured in `backend/config/.env`
2. IAM permissions for Textract and Transcribe
3. Python 3.8+ installed

## Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**New dependencies added:**
- `openpyxl` - Excel parsing
- `pandas` - Data manipulation
- `python-multipart` - File uploads

## Step 2: Start the API Server

```bash
cd backend/api
python main.py
```

Server starts at: `http://localhost:8000`

## Step 3: Check Supported Formats

```bash
curl http://localhost:8000/api/v1/formats/supported
```

**Expected Response:**
```json
{
  "formats_by_category": {
    "document": [...],
    "image": [...],
    "video": [...],
    "audio": [...],
    "spreadsheet": [...]
  },
  "all_extensions": [".pdf", ".docx", ".jpg", ".mp4", ".xlsx", ...],
  "total_formats": 21
}
```

## Step 4: Test Each Format Type

### Test 1: Upload a PDF (Document)

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/upload?source=web_ui&user_id=test123" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample.pdf"
```

**Expected:**
- Status: `202 Accepted`
- Format: `{"category": "document", "handler": "bda"}`
- Processing: Asynchronous via Bedrock Data Automation

### Test 2: Upload an Image (JPG/PNG)

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/upload?source=web_ui&user_id=test123" \
  -F "file=@image.jpg"
```

**Expected:**
- Status: `202 Accepted`
- Format: `{"category": "image", "handler": "textract"}`
- Processing: Synchronous via Amazon Textract OCR

### Test 3: Upload a Video (MP4)

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/upload?source=web_ui&user_id=test123" \
  -F "file=@video.mp4"
```

**Expected:**
- Status: `202 Accepted`
- Format: `{"category": "video", "handler": "transcribe"}`
- Processing: Asynchronous via Amazon Transcribe (audio extraction + transcription)

### Test 4: Upload a Spreadsheet (Excel)

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/upload?source=web_ui&user_id=test123" \
  -F "file=@data.xlsx"
```

**Expected:**
- Status: `202 Accepted`
- Format: `{"category": "spreadsheet", "handler": "excel_parser"}`
- Processing: Synchronous via local openpyxl parser

### Test 5: Upload Unsupported Format

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/upload?source=web_ui&user_id=test123" \
  -F "file=@data.xyz"
```

**Expected:**
- Status: `400 Bad Request`
- Error message with list of supported formats
- No processing initiated

## Step 5: Monitor Processing

### Check All Executions

```bash
curl http://localhost:8000/api/v1/ingest/executions?max_results=10
```

### Check Specific Execution Status

```bash
# Get execution_arn from upload response
curl "http://localhost:8000/api/v1/ingest/status/<execution_arn>"
```

### Check Dead Letter Queue

```bash
curl http://localhost:8000/api/v1/monitoring/dlq
```

## Step 6: Test Format Detection Programmatically

### Python Example

```python
import requests

# Test 1: Valid PDF
files = {'file': open('document.pdf', 'rb')}
response = requests.post(
    'http://localhost:8000/api/v1/ingest/upload',
    files=files,
    params={'source': 'web_ui', 'user_id': 'test123'}
)
print(f"PDF Upload: {response.status_code}")
print(f"Format: {response.json()['format']}")

# Test 2: Valid Image
files = {'file': open('image.jpg', 'rb')}
response = requests.post(
    'http://localhost:8000/api/v1/ingest/upload',
    files=files,
    params={'source': 'web_ui', 'user_id': 'test123'}
)
print(f"Image Upload: {response.status_code}")
print(f"Format: {response.json()['format']}")

# Test 3: Invalid Format
files = {'file': open('data.unknown', 'rb')}
response = requests.post(
    'http://localhost:8000/api/v1/ingest/upload',
    files=files,
    params={'source': 'web_ui', 'user_id': 'test123'}
)
print(f"Invalid Upload: {response.status_code}")
print(f"Error: {response.json()['detail']}")
```

## Expected Behavior by Format

| Format | Handler | Sync/Async | Output |
|--------|---------|------------|--------|
| PDF, DOCX, PPT | BDA | Async | Multimodal text extraction |
| JPG, PNG, TIFF | Textract | Sync | OCR text with confidence |
| MP4, AVI, MOV | Transcribe | Async | Speech-to-text transcript |
| MP3, WAV | Transcribe | Async | Speech-to-text transcript |
| XLSX, XLS, CSV | Excel Parser | Sync | Cell values + metadata |

## Troubleshooting

### Issue: "openpyxl not installed"
```bash
pip install openpyxl pandas
```

### Issue: "Textract/Transcribe permission denied"

Add IAM permissions:
```json
{
  "Effect": "Allow",
  "Action": [
    "textract:DetectDocumentText",
    "transcribe:StartTranscriptionJob",
    "transcribe:GetTranscriptionJob"
  ],
  "Resource": "*"
}
```

### Issue: "Format validation failed"

Check supported formats:
```bash
curl http://localhost:8000/api/v1/formats/supported
```

### Issue: "Processing stuck in IN_PROGRESS"

For async jobs (Transcribe, BDA), check:
1. Step Functions execution status
2. CloudWatch logs for job errors
3. AWS console for Transcribe/Bedrock job status

## Sample Test Files

Create these sample files for testing:

```bash
# Create a simple text file as PDF
echo "Test document content" > test.txt

# Create a CSV file
echo "Name,Age,City
John,30,NYC
Jane,25,LA" > test.csv

# Use any JPG/PNG image you have
# Use any MP4 video you have
```

## Verification Checklist

✅ All dependencies installed without errors
✅ API server starts successfully
✅ `/api/v1/formats/supported` returns 21+ formats
✅ PDF upload returns `handler: "bda"`
✅ Image upload returns `handler: "textract"`
✅ Video upload returns `handler: "transcribe"`
✅ Excel upload returns `handler: "excel_parser"`
✅ Invalid format returns HTTP 400 with error message
✅ Executions appear in `/api/v1/ingest/executions`
✅ No errors in console logs

## Next Steps

1. **Test with real files** - Upload actual PDFs, images, videos, spreadsheets
2. **Monitor CloudWatch** - Check metrics for each handler
3. **Test retrieval** - Query knowledge base after ingestion completes
4. **Test access control** - Verify user/team-based filtering works
5. **Load testing** - Test with multiple concurrent uploads

## API Documentation

Full interactive docs available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Support

For issues:
- Check `backend/FORMAT_HANDLING.md` for detailed documentation
- Check `IMPLEMENTATION_SUMMARY.md` for architecture overview
- Review CloudWatch logs for processing errors
- Check Step Functions execution history for failed steps
