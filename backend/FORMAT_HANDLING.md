# Format Handling & Processing

This document describes how different file formats are detected, validated, and processed in the ingestion pipeline.

## Overview

The pipeline now supports **format-aware processing** with automatic routing to specialized handlers based on file type.

## Architecture

```
File Upload
    ↓
Format Detection & Validation (format_detector.py)
    ↓
Format-Specific Processing (format_processor.py)
    ↓
    ├── Documents (PDF, DOCX, PPT, TXT) → Bedrock Data Automation
    ├── Images (JPG, PNG, TIFF) → Amazon Textract
    ├── Videos (MP4, AVI, MOV) → Amazon Transcribe
    ├── Audio (MP3, WAV, M4A) → Amazon Transcribe
    └── Spreadsheets (XLSX, XLS, CSV) → Excel Parser (openpyxl/pandas)
    ↓
Knowledge Base Ingestion
    ↓
OpenSearch Indexing
```

## Supported Formats

### Documents (Handler: Bedrock Data Automation)
- **PDF** (`.pdf`) - `application/pdf`
- **Word** (`.docx`, `.doc`) - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- **PowerPoint** (`.pptx`, `.ppt`) - `application/vnd.openxmlformats-officedocument.presentationml.presentation`
- **Text** (`.txt`) - `text/plain`
- **HTML** (`.html`, `.htm`) - `text/html`

**Processing:** Multimodal content extraction using Bedrock Data Automation

### Images (Handler: Amazon Textract)
- **JPEG** (`.jpg`, `.jpeg`) - `image/jpeg`
- **PNG** (`.png`) - `image/png`
- **TIFF** (`.tiff`, `.tif`) - `image/tiff`
- **BMP** (`.bmp`) - `image/bmp`

**Processing:** OCR and document analysis with text, table, and form extraction

### Videos (Handler: Amazon Transcribe)
- **MP4** (`.mp4`) - `video/mp4`
- **AVI** (`.avi`) - `video/x-msvideo`
- **MOV** (`.mov`) - `video/quicktime`
- **MKV** (`.mkv`) - `video/x-matroska`

**Processing:** Audio track extraction + speech-to-text transcription

### Audio (Handler: Amazon Transcribe)
- **MP3** (`.mp3`) - `audio/mpeg`
- **WAV** (`.wav`) - `audio/wav`
- **M4A** (`.m4a`) - `audio/x-m4a`

**Processing:** Speech-to-text transcription with speaker labels

### Spreadsheets (Handler: Excel Parser)
- **Excel (Modern)** (`.xlsx`) - `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- **Excel (Legacy)** (`.xls`) - `application/vnd.ms-excel`
- **CSV** (`.csv`) - `text/csv`

**Processing:** Cell-by-cell parsing with sheet/column metadata extraction

## Format Detection

### Detection Strategy (Priority Order)

1. **Content-Type Header** - MIME type from HTTP upload
2. **File Extension** - Fallback to extension-based detection
3. **Extension Mapping** - Direct extension-to-format lookup

### Validation

Before processing, files are validated:

```python
from services.format_detector import format_detector

is_valid, message = format_detector.validate_format(
    filename="document.pdf",
    content_type="application/pdf"
)
```

**Validation Checks:**
- File extension is recognized
- MIME type is supported
- Format is in supported formats list

**Unsupported formats** are rejected with HTTP 400 error listing supported extensions.

## Processing Flow

### 1. Upload with Validation

```python
# API validates format before accepting upload
POST /api/v1/ingest/upload
Content-Type: multipart/form-data

# Returns:
{
  "s3_key": "web_ui/2026/06/16/123456/document.pdf",
  "format": {
    "mime_type": "application/pdf",
    "category": "document",
    "handler": "bda"
  },
  "execution": {...}
}
```

### 2. Format-Aware Processing

The `FormatProcessor` routes files to appropriate handlers:

```python
from services.format_processor import format_processor

result = format_processor.process_file(
    source_key=s3_key,
    filename=filename,
    content_type=content_type,
    metadata=metadata
)
```

### 3. Handler-Specific Processing

#### Textract (Images)
- Synchronous processing for single-page images
- Extracts text blocks with confidence scores
- Returns structured text + geometry information

#### Transcribe (Audio/Video)
- **Asynchronous processing**
- Returns job ID immediately
- Step Functions polls for completion
- Supports speaker labels (up to 10 speakers)
- Language: English (en-US) by default

#### Excel Parser (Spreadsheets)
- Synchronous processing
- Parses all sheets
- Extracts cell values as text
- Returns metadata: sheet count, row/column counts, sheet names

#### BDA (Documents)
- **Asynchronous processing**
- Returns job ARN immediately
- Step Functions polls for completion
- Multimodal extraction (text, images, tables)

### 4. Metadata Enrichment

Each handler adds format-specific metadata:

```json
{
  "processor": "textract",
  "format": "image/jpeg",
  "category": "image",
  "processing_timestamp": "2026-06-16T10:30:00Z",
  "text_blocks_count": 42,
  "page_count": 1
}
```

## API Endpoints

### Check Supported Formats

```bash
GET /api/v1/formats/supported

# Response:
{
  "formats_by_category": {
    "document": [...],
    "image": [...],
    "video": [...],
    "audio": [...],
    "spreadsheet": [...]
  },
  "all_extensions": [".pdf", ".docx", ".jpg", ...],
  "total_formats": 21
}
```

### Upload with Format Validation

```bash
POST /api/v1/ingest/upload
Content-Type: multipart/form-data

# File: document.mp4
# source=web_ui
# user_id=user123

# Success (202):
{
  "message": "File uploaded and ingestion started",
  "format": {
    "category": "video",
    "handler": "transcribe"
  }
}

# Error (400):
{
  "error": "Unsupported file format",
  "supported_formats": [".pdf", ".docx", ...]
}
```

## Orchestration Integration

The `PipelineOrchestrator` now uses format-aware processing:

```python
from orchestrator import orchestrator

result = orchestrator.process_file(
    source_key=s3_key,
    filename=filename,
    content_type=content_type,
    metadata=metadata,
    retry_count=0
)
```

**Synchronous handlers** (Textract for images, Excel Parser):
- Return extracted text immediately
- Status: `SUCCESS`

**Asynchronous handlers** (Transcribe, BDA):
- Return job ID/ARN
- Status: `IN_PROGRESS`
- Requires polling via Step Functions

## Error Handling

### Format Validation Errors
- **HTTP 400** - Unsupported format
- **No retry** - Sent directly to DLQ
- User notified of supported formats

### Processing Errors
- **Transient errors** - Retry with exponential backoff (3 attempts)
- **Permanent errors** - Sent to DLQ after retries exhausted
- CloudWatch alarms triggered

## Monitoring

### CloudWatch Metrics

Format-specific metrics are logged:

```python
monitoring_service.log_processing_duration('textract', duration)
monitoring_service.log_processing_duration('transcribe', duration)
monitoring_service.log_processing_duration('excel_parser', duration)
monitoring_service.log_processing_duration('bda', duration)
```

**Dimensions:**
- `handler` - Processing handler used
- `category` - File category (document, image, video, etc.)
- `format` - MIME type

## Dependencies

### Python Packages
```
openpyxl      # Excel (.xlsx) parsing
pandas        # Excel (.xls) and CSV parsing
python-multipart  # FastAPI file uploads
```

### AWS Services
- **Amazon Textract** - Image OCR
- **Amazon Transcribe** - Audio/video transcription
- **Bedrock Data Automation** - Document processing

## Configuration

No additional configuration needed. Services use existing AWS credentials from `config/.env`:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

## IAM Permissions Required

Add these permissions to your IAM role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "textract:DetectDocumentText",
        "textract:StartDocumentAnalysis",
        "textract:GetDocumentAnalysis"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "transcribe:StartTranscriptionJob",
        "transcribe:GetTranscriptionJob",
        "transcribe:DeleteTranscriptionJob"
      ],
      "Resource": "*"
    }
  ]
}
```

## Testing

### Test Format Detection

```python
from services.format_detector import format_detector

# Valid format
format_info = format_detector.detect_format("report.pdf", "application/pdf")
# Returns: {'mime_type': 'application/pdf', 'category': 'document', 'handler': 'bda'}

# Invalid format
try:
    format_detector.detect_format("data.xyz", None)
except ValueError as e:
    print(e)  # "Unsupported file format..."
```

### Test Format Processing

```bash
# Upload different formats via API
curl -X POST "http://localhost:8000/api/v1/ingest/upload?source=web_ui&user_id=test" \
  -F "file=@document.pdf"

curl -X POST "http://localhost:8000/api/v1/ingest/upload?source=web_ui&user_id=test" \
  -F "file=@image.jpg"

curl -X POST "http://localhost:8000/api/v1/ingest/upload?source=web_ui&user_id=test" \
  -F "file=@video.mp4"

curl -X POST "http://localhost:8000/api/v1/ingest/upload?source=web_ui&user_id=test" \
  -F "file=@spreadsheet.xlsx"
```

## Future Enhancements

### Language Support (Not Yet Implemented)
- Tamil language support (ta-IN) via Transcribe
- Sinhala language support (si-LK) via Transcribe
- Amazon Translate integration for non-English content

### Additional Formats
- Archive files (.zip, .tar.gz)
- Code files (.py, .js, .java)
- Markdown (.md)
- JSON/XML data files

### Advanced Features
- Format-specific chunking strategies
- Custom metadata extractors per format
- Format conversion pipeline (e.g., video → audio → text)
