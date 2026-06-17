# Environment Configuration Guide

## Overview

The `.env` file contains all AWS credentials and service configurations needed to run the ingestion pipeline.

**Location:** `backend/config/.env`

## Quick Setup

### Step 1: Create .env File

```bash
cd backend/config
cp .env.example .env
```

Then edit `.env` with your actual AWS credentials and resource ARNs.

### Step 2: Fill Required Values

Replace all `your-*` placeholders with actual values from your AWS account.

---

## Detailed Configuration

### 1. AWS Credentials

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**How to Get:**
1. Go to AWS Console → IAM → Users
2. Select your user or create a new one
3. Go to "Security credentials" tab
4. Click "Create access key"
5. Choose "Application running outside AWS"
6. Download the credentials

**Required IAM Permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket",
        "bedrock:InvokeModel",
        "bedrock:StartDataAutomationJob",
        "bedrock:GetDataAutomationJob",
        "bedrock-agent:StartIngestionJob",
        "bedrock-agent:GetIngestionJob",
        "bedrock-agent:Retrieve",
        "textract:DetectDocumentText",
        "textract:StartDocumentAnalysis",
        "textract:GetDocumentAnalysis",
        "transcribe:StartTranscriptionJob",
        "transcribe:GetTranscriptionJob",
        "transcribe:DeleteTranscriptionJob",
        "states:StartExecution",
        "states:DescribeExecution",
        "states:ListExecutions",
        "sqs:SendMessage",
        "sqs:GetQueueAttributes",
        "cloudwatch:PutMetricData",
        "cloudwatch:GetMetricStatistics",
        "sns:Publish"
      ],
      "Resource": "*"
    }
  ]
}
```

---

### 2. S3 Buckets

```env
S3_RAW_BUCKET=my-pipeline-raw-uploads
S3_PROCESSED_BUCKET=my-pipeline-processed-data
```

**How to Create:**
```bash
aws s3 mb s3://my-pipeline-raw-uploads --region us-east-1
aws s3 mb s3://my-pipeline-processed-data --region us-east-1
```

Or via AWS Console:
1. Go to S3 → Create bucket
2. Create two buckets with unique names
3. Keep default settings (private access)
4. Enable versioning (recommended)

**Bucket Structure:**
```
s3://my-pipeline-raw-uploads/
  ├── web_ui/
  │   └── 2026/06/16/123456/document.pdf
  ├── shared_drive/
  └── file_repo/

s3://my-pipeline-processed-data/
  ├── bda-output/
  ├── textract-output/
  └── transcribe-output/
```

---

### 3. Bedrock Configuration

```env
BEDROCK_DATA_AUTOMATION_JOB_ARN=arn:aws:bedrock:us-east-1:123456789012:data-automation-project/abc123
BEDROCK_KB_ID=XYZABC123
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v1
```

#### **A. Bedrock Data Automation (BDA)**

**How to Get BDA ARN:**
1. Go to AWS Console → Bedrock → Data Automation
2. Create a new Data Automation project
3. Configure input/output S3 locations
4. Copy the project ARN from the project details

**Example ARN format:**
```
arn:aws:bedrock:us-east-1:123456789012:data-automation-project/abc123def456
```

#### **B. Knowledge Base ID**

**How to Create Knowledge Base:**
1. Go to AWS Console → Bedrock → Knowledge bases
2. Click "Create knowledge base"
3. Configure:
   - Name: "Document Ingestion KB"
   - Data source: S3 (point to processed bucket)
   - Embeddings model: Amazon Titan Embeddings G1 - Text
   - Vector database: OpenSearch Serverless (create new)
4. Copy the Knowledge Base ID (e.g., `XYZABC123`)

#### **C. Embedding Model**

**Available Models:**
- `amazon.titan-embed-text-v1` - Default, 1536 dimensions
- `amazon.titan-embed-text-v2` - Latest version
- `cohere.embed-english-v3` - Cohere embeddings
- `cohere.embed-multilingual-v3` - Multilingual support

**Recommendation:** Use `amazon.titan-embed-text-v1` (default, tested)

---

### 4. OpenSearch Configuration

```env
OPENSEARCH_ENDPOINT=https://search-mydomain-abc123.us-east-1.es.amazonaws.com
OPENSEARCH_INDEX=document-embeddings
```

**How to Get:**

If you created Knowledge Base with OpenSearch Serverless:
1. Go to AWS Console → OpenSearch Service → Collections
2. Find your collection (created with KB)
3. Copy the endpoint URL

If using managed OpenSearch:
1. Go to AWS Console → OpenSearch Service → Domains
2. Create a new domain or use existing
3. Copy the domain endpoint

**Note:** If you used Knowledge Base setup, OpenSearch is auto-configured. The endpoint is in the KB data source settings.

---

### 5. Step Functions

```env
STEP_FUNCTION_ARN=arn:aws:states:us-east-1:123456789012:stateMachine:ingestion-pipeline
```

**How to Create:**

1. Go to AWS Console → Step Functions → State machines
2. Click "Create state machine"
3. Choose "Write your workflow in code"
4. Use this basic definition:

```json
{
  "Comment": "Document Ingestion Pipeline",
  "StartAt": "ProcessFile",
  "States": {
    "ProcessFile": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-file",
      "Next": "IngestToKB"
    },
    "IngestToKB": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:ingest-to-kb",
      "End": true
    }
  }
}
```

5. Name it: `ingestion-pipeline`
6. Copy the ARN from the state machine details

**Note:** Full Step Functions implementation requires Lambda functions. For initial testing, you can skip this and call the orchestrator directly.

---

### 6. SQS Queues

```env
SQS_DLQ_URL=https://sqs.us-east-1.amazonaws.com/123456789012/ingestion-dlq
SQS_RETRY_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/ingestion-retry
```

**How to Create:**

```bash
# Create retry queue
aws sqs create-queue --queue-name ingestion-retry --region us-east-1

# Create dead-letter queue
aws sqs create-queue --queue-name ingestion-dlq --region us-east-1
```

Or via AWS Console:
1. Go to SQS → Create queue
2. Create two Standard queues:
   - `ingestion-retry` - For retry attempts
   - `ingestion-dlq` - For failed items after retry exhaustion
3. Copy the queue URLs

**Configure DLQ on Retry Queue:**
1. Edit `ingestion-retry` queue
2. Set Dead-letter queue: `ingestion-dlq`
3. Maximum receives: 3

---

### 7. CloudWatch & SNS

```env
CLOUDWATCH_LOG_GROUP=/aws/ingestion-pipeline
ALARM_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:ingestion-alarms
```

#### **CloudWatch Log Group**

**Auto-created** - The application will create this log group automatically.

Or create manually:
```bash
aws logs create-log-group --log-group-name /aws/ingestion-pipeline --region us-east-1
```

#### **SNS Topic for Alarms**

**How to Create:**
```bash
aws sns create-topic --name ingestion-alarms --region us-east-1
```

**Subscribe to get email notifications:**
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:ingestion-alarms \
  --protocol email \
  --notification-endpoint your-email@example.com
```

Check your email and confirm the subscription.

---

### 8. Application Settings

```env
MAX_RETRY_ATTEMPTS=3
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

**These are optional** - defaults are already set in code.

- **MAX_RETRY_ATTEMPTS**: Number of retry attempts before DLQ (default: 3)
- **CHUNK_SIZE**: Token size for document chunking (default: 512)
- **CHUNK_OVERLAP**: Overlapping tokens between chunks (default: 50)

---

## Minimal Configuration (For Testing)

If you just want to test the format handling without full AWS setup:

### Required (Minimal):
```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_RAW_BUCKET=test-raw-bucket
S3_PROCESSED_BUCKET=test-processed-bucket
```

### Optional (Can use dummy values for testing):
```env
BEDROCK_DATA_AUTOMATION_JOB_ARN=arn:aws:bedrock:us-east-1:000000000000:data-automation-project/test
BEDROCK_KB_ID=TEST123
OPENSEARCH_ENDPOINT=https://test.us-east-1.es.amazonaws.com
STEP_FUNCTION_ARN=arn:aws:states:us-east-1:000000000000:stateMachine:test
SQS_DLQ_URL=https://sqs.us-east-1.amazonaws.com/000000000000/test-dlq
```

**Note:** With minimal config, only file upload and S3 storage will work. Format detection and validation will work, but processing will fail.

---

## Testing Your Configuration

### 1. Validate Settings

```bash
cd backend
python -c "from config.settings import settings; settings.validate()"
```

If successful, no output. If missing required fields, you'll see an error.

### 2. Test AWS Credentials

```bash
aws s3 ls --region us-east-1
```

Should list your S3 buckets.

### 3. Test Format Detection (No AWS needed)

```bash
cd backend
python -c "
from services.format_detector import format_detector
print(format_detector.get_supported_extensions())
"
```

Should print list of supported file extensions.

### 4. Start the API

```bash
cd backend/api
python main.py
```

Visit: `http://localhost:8000/api/v1/formats/supported`

---

## Common Issues

### Issue: "Missing required configuration"

**Solution:** Run validation to see which fields are missing:
```bash
python -c "from config.settings import settings; settings.validate()"
```

### Issue: "Access Denied" errors

**Solution:** Check IAM permissions. Your user/role needs permissions for all services.

### Issue: "Bucket does not exist"

**Solution:** Create the S3 buckets:
```bash
aws s3 mb s3://your-bucket-name --region us-east-1
```

### Issue: "Knowledge Base not found"

**Solution:** Create a Knowledge Base in AWS Bedrock console first.

---

## Security Best Practices

1. **Never commit .env to git**
   - Already in `.gitignore`
   - Use `.env.example` as template

2. **Use IAM roles instead of access keys** (for EC2/ECS)
   - Remove `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
   - Attach IAM role to your EC2 instance

3. **Rotate credentials regularly**
   - Create new access keys every 90 days
   - Delete old keys

4. **Use least privilege principle**
   - Only grant permissions your application needs
   - Restrict to specific resources when possible

---

## Quick Start Commands

```bash
# 1. Copy example to .env
cd backend/config
cp .env.example .env

# 2. Edit with your values
nano .env  # or use any text editor

# 3. Test configuration
cd ../..
python -c "from config.settings import settings; settings.validate()"

# 4. Start the API
cd api
python main.py
```

---

## Example Complete .env File

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

# S3 Buckets
S3_RAW_BUCKET=my-company-raw-uploads-2026
S3_PROCESSED_BUCKET=my-company-processed-data-2026

# Bedrock Configuration
BEDROCK_DATA_AUTOMATION_JOB_ARN=arn:aws:bedrock:us-east-1:123456789012:data-automation-project/abc123def456
BEDROCK_KB_ID=XYZABC123DEF
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v1

# OpenSearch Configuration
OPENSEARCH_ENDPOINT=https://search-kb-collection-abc123.us-east-1.aoss.amazonaws.com
OPENSEARCH_INDEX=document-embeddings

# Step Functions
STEP_FUNCTION_ARN=arn:aws:states:us-east-1:123456789012:stateMachine:ingestion-pipeline-v1

# SQS Configuration
SQS_DLQ_URL=https://sqs.us-east-1.amazonaws.com/123456789012/ingestion-dlq
SQS_RETRY_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/ingestion-retry

# CloudWatch Configuration
CLOUDWATCH_LOG_GROUP=/aws/ingestion-pipeline
ALARM_SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:ingestion-alarms

# Application Settings
MAX_RETRY_ATTEMPTS=3
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

---

## Next Steps

After setting up `.env`:

1. ✅ Validate configuration
2. ✅ Test AWS credentials
3. ✅ Start backend API
4. ✅ Test format detection endpoint
5. ✅ Upload test files
6. ✅ Monitor CloudWatch logs

For detailed testing instructions, see `QUICK_START_FORMAT_TESTING.md`.
