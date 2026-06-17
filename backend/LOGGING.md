# Backend Logging System Documentation

## Overview

The BDA Pipeline backend implements a comprehensive logging system that monitors all activities across the application. Logs are written to both console (with colors) and rotating log files for persistence and analysis.

## Features

✅ **Multi-destination logging** - Console (colored) + File (rotating)  
✅ **Structured logging** - JSON format support for log aggregation  
✅ **Activity tracking** - All API requests, uploads, queries, and KB operations  
✅ **Performance monitoring** - Request duration tracking and slow request alerts  
✅ **Error tracking** - Detailed error logs with stack traces  
✅ **Log rotation** - Size-based and time-based rotation to manage disk space  
✅ **Configurable levels** - DEBUG, INFO, WARNING, ERROR, CRITICAL  

## Log Files

All log files are stored in `backend/logs/`:

| File | Purpose | Rotation | Retention |
|------|---------|----------|-----------|
| `application.log` | All application logs | 10MB per file | 5 backups |
| `errors.log` | Only ERROR and CRITICAL logs | 10MB per file | 5 backups |
| `activity.log` | User activity and operations | Daily at midnight | 30 days |

## Configuration

Configure logging via environment variables in `backend/config/.env`:

```bash
# LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# LOG_FORMAT: detailed (colored console), json (structured), simple (minimal)
LOG_FORMAT=detailed
```

### Log Levels

- **DEBUG**: Detailed debugging information (use in development)
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages for unusual situations
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical errors that may cause system failure

### Log Formats

#### 1. Detailed (Default)
Colored console output with full context:
```
2025-01-15 10:30:45 | INFO     | api.app:upload_direct:268 | Uploading file: document.pdf for user: user123
```

#### 2. JSON
Structured JSON for log aggregation tools (ELK, CloudWatch, etc.):
```json
{
  "timestamp": "2025-01-15T10:30:45.123456",
  "level": "INFO",
  "logger": "api.app",
  "message": "Uploading file: document.pdf for user: user123",
  "module": "app",
  "function": "upload_direct",
  "line": 268,
  "extra": {
    "type": "upload",
    "filename": "document.pdf",
    "user_id": "user123",
    "file_size": 1048576,
    "source": "web_ui"
  }
}
```

#### 3. Simple
Minimal format for basic logging:
```
2025-01-15 10:30:45 - INFO - Uploading file: document.pdf for user: user123
```

## Logged Activities

### 1. API Requests
Every API request is logged with:
- HTTP method and path
- User ID (if available)
- Response status code
- Duration in milliseconds
- Client IP and user agent

```python
log_api_request(
    logger=logger,
    method='POST',
    path='/api/upload/direct',
    user_id='user123',
    status_code=202,
    duration_ms=456.78
)
```

### 2. File Uploads
All file uploads are tracked:
- Filename and size
- User ID
- Source (web_ui, google_drive, etc.)
- Success/failure status
- S3 key or error message

```python
log_upload(
    logger=logger,
    filename='document.pdf',
    user_id='user123',
    file_size=1048576,
    source='web_ui',
    success=True,
    s3_key='uploads/user123/document.pdf'
)
```

### 3. Metadata Extraction
Metadata extraction results:
- Filename
- Extracted fields
- Success/failure
- Warnings or errors

```python
log_metadata_extraction(
    logger=logger,
    filename='document.pdf',
    extracted_fields={'author': 'John Doe', 'pages': 10},
    success=True
)
```

### 4. Knowledge Base Operations
KB sync and ingestion jobs:
- Operation type
- KB ID and job ID
- Status
- Errors

```python
log_kb_operation(
    logger=logger,
    operation='manual_sync',
    kb_id='RTG6PKX6VX',
    job_id='job-123',
    status='IN_PROGRESS'
)
```

### 5. Queries
User queries with results:
- Query text
- User ID
- Number of results
- Duration
- Applied filters

```python
log_query(
    logger=logger,
    query='machine learning best practices',
    user_id='user123',
    results_count=5,
    duration_ms=234.56,
    filters={'team_id': 'team456'}
)
```

### 6. S3 Operations
S3 upload/download operations:
- Operation type (upload, download, delete)
- Bucket and key
- Success/failure
- Error message

```python
log_s3_operation(
    logger=logger,
    operation='upload',
    bucket='test-video-transcript',
    key='uploads/user123/document.pdf',
    success=True
)
```

### 7. Sync Jobs
Scheduled and manual sync jobs:
- Job type (incremental, full)
- Number of files processed
- Duration
- Success/failure

```python
log_sync_job(
    logger=logger,
    job_type='incremental',
    files_count=5,
    success=True,
    duration_s=12.34
)
```

## Usage in Code

### Basic Logging

```python
from utils.logger import get_logger

logger = get_logger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
```

### With Extra Context

```python
logger.info(
    "Processing file",
    extra={
        'extra_data': {
            'filename': 'document.pdf',
            'user_id': 'user123',
            'file_size': 1048576
        }
    }
)
```

### Exception Logging

```python
try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {str(e)}", exc_info=True)
```

## Monitoring and Alerts

### Slow Requests
Requests taking >1 second are automatically flagged:
```
WARNING: Slow request: POST /api/upload/direct took 1234.56ms
```

### Error Rate
Monitor `errors.log` for increased error rates:
```bash
# Count errors in the last hour
grep "ERROR" logs/errors.log | grep "$(date +%Y-%m-%d\ %H)" | wc -l
```

### Activity Statistics
```bash
# Count uploads today
grep "Upload -" logs/activity.log | grep "$(date +%Y-%m-%d)" | wc -l

# Count queries today
grep "Query -" logs/activity.log | grep "$(date +%Y-%m-%d)" | wc -l
```

## Integration with Monitoring Tools

### CloudWatch Logs
Push logs to AWS CloudWatch:
```python
import watchtower

cloudwatch_handler = watchtower.CloudWatchLogHandler(
    log_group='/bda-pipeline/application',
    stream_name='{machine_name}'
)
logger.addHandler(cloudwatch_handler)
```

### ELK Stack
Use JSON format for Elasticsearch ingestion:
```bash
LOG_FORMAT=json
```

Then ship logs with Filebeat or Logstash.

### Grafana
Query logs in Grafana using Loki or CloudWatch data source.

## Log Analysis

### Find Errors
```bash
# All errors today
grep "ERROR" logs/errors.log | grep "$(date +%Y-%m-%d)"

# Specific error pattern
grep -A 5 "Upload failed" logs/errors.log
```

### Performance Analysis
```bash
# Find slow requests
grep "Slow request" logs/application.log

# Average response time for an endpoint
grep "POST /api/upload/direct" logs/application.log | \
  grep -oP "Duration: \K[0-9.]+" | \
  awk '{sum+=$1; count++} END {print sum/count}'
```

### User Activity
```bash
# All activity for a specific user
grep "user123" logs/activity.log

# Upload count per user
grep "Upload -" logs/activity.log | \
  grep -oP "by \K[^ ]+" | \
  sort | uniq -c | sort -rn
```

## Troubleshooting

### Logs Not Appearing
1. Check `LOG_LEVEL` in `.env` (set to `DEBUG` for maximum detail)
2. Verify logs directory exists: `backend/logs/`
3. Check file permissions

### Log Files Too Large
1. Reduce `BACKUP_COUNT` in `utils/logger.py`
2. Decrease `MAX_BYTES` for more frequent rotation
3. Use log cleanup cron job:
```bash
# Delete logs older than 30 days
find backend/logs -name "*.log.*" -mtime +30 -delete
```

### Performance Impact
Logging has minimal performance impact (<5ms per request). If concerned:
1. Use `LOG_LEVEL=WARNING` in production
2. Disable console logging: `log_to_console=False`
3. Use asynchronous handlers for high-throughput scenarios

## Best Practices

1. **Use appropriate log levels**: DEBUG for development, INFO for production
2. **Include context**: Always add user_id, filename, etc. to logs
3. **Log exceptions**: Use `exc_info=True` for stack traces
4. **Structured data**: Use `extra={'extra_data': {...}}` for queryable logs
5. **Sensitive data**: Never log passwords, tokens, or PII
6. **Regular cleanup**: Implement log rotation and archival strategy

## Example Log Output

```
2025-01-15 10:30:45 | INFO     | middleware.logging_middleware:dispatch:41 | → POST /api/upload/direct
2025-01-15 10:30:45 | INFO     | api.app:upload_direct:268 | Uploading file: document.pdf for user: user123
2025-01-15 10:30:45 | INFO     | services.metadata_extractor:extract_metadata:45 | Extracting metadata from document.pdf
2025-01-15 10:30:46 | INFO     | api.app:upload_direct:280 | Metadata Extraction - document.pdf - 8 fields
2025-01-15 10:30:46 | INFO     | services.upload_service:upload_to_s3:67 | Uploading to S3: uploads/user123/document.pdf
2025-01-15 10:30:47 | INFO     | api.app:upload_direct:295 | Upload - document.pdf (1048576 bytes) by user123 from web_ui - S3: uploads/user123/document.pdf
2025-01-15 10:30:47 | INFO     | api.app:upload_direct:298 | Upload completed in 1234.56ms - S3: uploads/user123/document.pdf
2025-01-15 10:30:47 | INFO     | middleware.logging_middleware:dispatch:52 | API POST /api/upload/direct - Status: 202 - Duration: 1234.56ms
```
