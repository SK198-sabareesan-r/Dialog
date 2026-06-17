# Setup Guide - Simplified Knowledge Base

## Quick Start (5 Steps)

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
cp config/.env.example config/.env
```

Edit `config/.env`:

```env
# AWS Credentials
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# S3 Bucket (you'll create this in Step 3)
S3_RAW_BUCKET=my-knowledge-base-bucket

# Bedrock KB (you'll get these in Step 4)
BEDROCK_KB_ID=XXXXXXXXXX
BEDROCK_DATA_SOURCE_ID=XXXXXXXXXX
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v1

# Google Drive (Optional - skip if not using Drive)
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=xxxxx
```

### Step 3: Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://my-knowledge-base-bucket --region us-east-1

# Verify
aws s3 ls | grep knowledge-base
```

### Step 4: Create Bedrock Knowledge Base

**Option A: AWS Console (Recommended for first time)**

1. Open AWS Console → **Bedrock** → **Knowledge bases**
2. Click **"Create knowledge base"**
3. **Basic information:**
   - Name: `MyKnowledgeBase`
   - Description: `Multi-source knowledge base with metadata`
   - IAM role: Create new role (or select existing)
4. **Configure data source:**
   - Data source name: `S3DataSource`
   - Data source type: **Amazon S3**
   - S3 URI: `s3://my-knowledge-base-bucket/`
   - Chunking strategy: **Default chunking**
     - Max tokens: 300
     - Overlap: 20%
5. **Select embeddings model:**
   - Embeddings model: **Titan Embeddings G1 - Text**
   - Dimensions: 1536
6. **Vector database:**
   - Quick create a new vector store (managed by AWS)
7. **Sync schedule:**
   - Select: **Hourly** (or **On-demand**)
8. Click **Create**
9. **IMPORTANT:** Copy these values to your `.env`:
   - Knowledge Base ID (looks like: `XXXXXXXXXX`)
   - Data Source ID (looks like: `XXXXXXXXXX`)

**Option B: AWS CLI**

```bash
# 1. Create IAM role (one-time)
aws iam create-role \
  --role-name BedrockKBRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "bedrock.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# 2. Attach policies
aws iam attach-role-policy \
  --role-name BedrockKBRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# 3. Create Knowledge Base
KB_RESPONSE=$(aws bedrock-agent create-knowledge-base \
  --name "MyKnowledgeBase" \
  --role-arn "arn:aws:iam::ACCOUNT_ID:role/BedrockKBRole" \
  --knowledge-base-configuration '{
    "type": "VECTOR",
    "vectorKnowledgeBaseConfiguration": {
      "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
    }
  }' \
  --storage-configuration '{
    "type": "OPENSEARCH_SERVERLESS",
    "opensearchServerlessConfiguration": {
      "collectionArn": "arn:aws:aoss:us-east-1:ACCOUNT_ID:collection/kb-collection",
      "vectorIndexName": "bedrock-knowledge-base-index",
      "fieldMapping": {
        "vectorField": "bedrock-knowledge-base-default-vector",
        "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
        "metadataField": "AMAZON_BEDROCK_METADATA"
      }
    }
  }')

# Extract KB ID
KB_ID=$(echo $KB_RESPONSE | jq -r '.knowledgeBase.knowledgeBaseId')
echo "Knowledge Base ID: $KB_ID"

# 4. Add S3 Data Source
DS_RESPONSE=$(aws bedrock-agent create-data-source \
  --knowledge-base-id "$KB_ID" \
  --name "S3DataSource" \
  --data-source-configuration '{
    "type": "S3",
    "s3Configuration": {
      "bucketArn": "arn:aws:s3:::my-knowledge-base-bucket",
      "inclusionPrefixes": ["users/"]
    }
  }')

# Extract Data Source ID
DS_ID=$(echo $DS_RESPONSE | jq -r '.dataSource.dataSourceId')
echo "Data Source ID: $DS_ID"

# Add these to your .env file!
```

### Step 5: Run the API

```bash
python api/app.py
```

Server starts on `http://localhost:8000`

Test it:
```bash
curl http://localhost:8000/
```

---

## Test the Complete Flow

### 1. Upload a Test File

```bash
curl -X POST http://localhost:8000/api/upload/direct \
  -F "file=@test.pdf" \
  -F "user_id=testuser" \
  -F "department=Engineering" \
  -F "tags=test,demo"
```

**Expected response:**
```json
{
  "message": "File uploaded successfully",
  "s3_key": "users/testuser/2024/06/16/123456/test.pdf",
  "metadata": {
    "extracted": {
      "author": "John Doe",
      "title": "Test Document",
      "page_count": 5
    },
    "custom": {
      "user_id": "testuser",
      "department": "Engineering",
      "tags": "test,demo"
    }
  }
}
```

### 2. Trigger KB Sync

```bash
curl -X POST http://localhost:8000/api/kb/sync \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

**Expected response:**
```json
{
  "message": "Knowledge Base sync started",
  "ingestion_job_id": "JOB123456",
  "status": "STARTING"
}
```

### 3. Check Sync Status

```bash
curl http://localhost:8000/api/kb/sync/status/JOB123456
```

Wait until `status` is `COMPLETE` (usually 2-5 minutes).

### 4. Query the Knowledge Base

```bash
curl -X POST http://localhost:8000/api/kb/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test document",
    "user_id": "testuser",
    "max_results": 5
  }'
```

**Expected response:**
```json
{
  "query": "test document",
  "results_count": 1,
  "results": [
    {
      "content": "...relevant text from your document...",
      "score": 0.95,
      "metadata": {
        "user_id": "testuser",
        "department": "Engineering",
        "filename": "test.pdf"
      }
    }
  ]
}
```

---

## Optional: Google Drive Integration

### 1. Create Google Cloud Project

1. Go to https://console.cloud.google.com
2. Create new project: `KnowledgeBase-Drive`
3. Enable **Google Drive API**
4. Enable **Google Picker API**

### 2. Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client ID**
3. Application type: **Web application**
4. Name: `Knowledge Base App`
5. Authorized JavaScript origins:
   - `http://localhost:3000` (development)
   - `https://yourdomain.com` (production)
6. Authorized redirect URIs:
   - `http://localhost:3000/auth/google/callback`
   - `https://yourdomain.com/auth/google/callback`
7. Click **Create**
8. Copy **Client ID** and **Client Secret** to `.env`:
   ```env
   GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=xxxxx
   ```

### 3. Test Google Drive Import

Frontend will use Google Picker API to let users select files.
Backend endpoint: `POST /api/google-drive/import`

---

## Troubleshooting

### Issue: "Missing required configuration"

**Solution:**
```bash
# Check your .env file
cat config/.env

# Ensure these are set:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY  
# - S3_RAW_BUCKET
# - BEDROCK_KB_ID
# - BEDROCK_DATA_SOURCE_ID
```

### Issue: "Access Denied" when uploading to S3

**Solution:**
```bash
# Test AWS credentials
aws sts get-caller-identity

# Ensure IAM user has S3 permissions:
# - s3:PutObject
# - s3:GetObject
# - s3:ListBucket
```

### Issue: "Knowledge Base not found"

**Solution:**
```bash
# List your Knowledge Bases
aws bedrock-agent list-knowledge-bases

# Verify KB ID matches .env file
```

### Issue: Files uploaded but not queryable

**Solution:**
1. Check ingestion job status
2. Trigger manual sync: `POST /api/kb/sync`
3. Wait 5-10 minutes for processing
4. Check Bedrock KB console for errors

### Issue: Metadata not extracted

**Solution:**
```bash
# Install metadata extraction libraries
pip install PyPDF2 python-docx python-pptx openpyxl Pillow

# Some files may not have metadata - check logs
tail -f logs/app.log
```

---

## Verify Everything Works

Run this test script:

```bash
# Test 1: Health check
curl http://localhost:8000/

# Test 2: Check supported formats
curl http://localhost:8000/api/supported-formats

# Test 3: Upload file
curl -X POST http://localhost:8000/api/upload/direct \
  -F "file=@sample.pdf" \
  -F "user_id=testuser"

# Test 4: Trigger sync
curl -X POST http://localhost:8000/api/kb/sync \
  -H "Content-Type: application/json" \
  -d '{"force": false}'

# Test 5: Wait 5 minutes, then query
sleep 300
curl -X POST http://localhost:8000/api/kb/query \
  -H "Content-Type: application/json" \
  -d '{"query": "sample", "user_id": "testuser", "max_results": 5}'
```

---

## Next Steps

1. ✅ Backend is running
2. 🔄 Build frontend (React/Vue)
3. 🔄 Integrate Google Drive OAuth
4. 🔄 Deploy to production (AWS Fargate/ECS)

---

## Production Checklist

Before deploying to production:

- [ ] Update CORS origins in `api/app.py`
- [ ] Use secrets manager for credentials (not .env)
- [ ] Enable CloudWatch logging
- [ ] Set up auto-scaling
- [ ] Configure backup for S3 bucket
- [ ] Set up monitoring/alerts
- [ ] Test with production data
- [ ] Document API for frontend team

---

## Cost Optimization

- Use S3 Intelligent-Tiering for old files
- Set Bedrock KB sync to on-demand (not hourly) for low-traffic
- Use reserved capacity for high-volume
- Monitor Bedrock API usage

---

## Support

- AWS Bedrock Documentation: https://docs.aws.amazon.com/bedrock/
- Check logs: `tail -f logs/app.log`
- Test AWS: `aws bedrock-agent list-knowledge-bases`

Done! Your knowledge base is ready. 🎉
