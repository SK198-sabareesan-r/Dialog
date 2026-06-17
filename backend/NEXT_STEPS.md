# Next Steps - Getting Your Knowledge Base Running

## Current Status ✅

You have:
- ✅ Simplified architecture (no Lambda, no Step Functions)
- ✅ Updated code with automatic metadata extraction
- ✅ AWS SSO support (session tokens)
- ✅ Knowledge Base created (ID: K92XMJHZLR)
- ✅ S3 bucket name: test-video-transcript
- ✅ Region: ap-south-1 (Mumbai)

---

## What You Need to Do Now

### Step 1: Get Your AWS SSO Credentials

**Option A: Using the Helper Script (Easiest)**

```bash
# Run the automated script
python get_sso_credentials.py --profile your-sso-profile

# It will:
# 1. Login to AWS SSO (opens browser)
# 2. Fetch temporary credentials
# 3. Automatically update your .env file
```

**Option B: Manual Method**

```bash
# 1. Login to SSO
aws sso login --profile your-sso-profile

# 2. Get credentials
aws configure export-credentials --profile your-sso-profile --format env

# 3. Copy output to config/.env:
#    AWS_ACCESS_KEY_ID=ASIA...
#    AWS_SECRET_ACCESS_KEY=...
#    AWS_SESSION_TOKEN=...
```

**Your `.env` should look like:**
```env
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=FwoGZXIvYXdzEBYaDCvTMU...very-long-token...

S3_RAW_BUCKET=test-video-transcript
BEDROCK_KB_ID=K92XMJHZLR
BEDROCK_DATA_SOURCE_ID=your-data-source-id
```

---

### Step 2: Create S3 Bucket

```bash
# Create the bucket
aws s3 mb s3://test-video-transcript --region ap-south-1

# Verify it was created
aws s3 ls | grep test-video-transcript
```

**Expected output:**
```
2024-06-16 14:30:00 test-video-transcript
```

---

### Step 3: Add S3 Data Source to Knowledge Base

```bash
# Add S3 as a data source
aws bedrock-agent create-data-source \
  --knowledge-base-id K92XMJHZLR \
  --region ap-south-1 \
  --name "S3DataSource" \
  --data-source-configuration '{
    "type": "S3",
    "s3Configuration": {
      "bucketArn": "arn:aws:s3:::test-video-transcript",
      "inclusionPrefixes": ["users/"]
    }
  }'
```

**Copy the Data Source ID from output:**
```json
{
  "dataSource": {
    "dataSourceId": "ABCDEF123456",  ← Copy this!
    "name": "S3DataSource",
    "status": "AVAILABLE"
  }
}
```

**Update `.env` with the Data Source ID:**
```env
BEDROCK_DATA_SOURCE_ID=ABCDEF123456
```

---

### Step 4: Test Your Credentials

```bash
# Test if everything is configured correctly
python test_credentials.py
```

**Expected output:**
```
================================================================================
AWS Credentials Test
================================================================================

[1/5] Checking configuration...
   ✅ Configuration looks good

[2/5] Testing AWS credentials...
   ✅ Authenticated as: arn:aws:sts::106611079163:assumed-role/YourRole/yourname
   
[3/5] Testing S3 access...
   ✅ S3 bucket exists: test-video-transcript
   ✅ Can list objects (found 0 objects)
   
[4/5] Testing Bedrock Agent access...
   ✅ Knowledge Base found: MyKnowledgeBase
   Status: ACTIVE
   ✅ Data Source found: S3DataSource
   Status: AVAILABLE
   
[5/5] Testing Bedrock Runtime access...
   ✅ Bedrock Agent Runtime client created
   Ready to query KB: K92XMJHZLR

================================================================================
Summary
================================================================================
✅ AWS credentials are valid
✅ S3 bucket configured: test-video-transcript
✅ Bedrock KB configured: K92XMJHZLR
✅ Data Source configured: ABCDEF123456

🚀 You're ready to start the API!
   Run: python api/app.py
================================================================================
```

---

### Step 5: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

---

### Step 6: Start the API

```bash
python api/app.py
```

**Expected output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Test it:**
```bash
curl http://localhost:8000/
```

---

### Step 7: Test Complete Flow

#### 1. Upload a Test File

```bash
curl -X POST http://localhost:8000/api/upload/direct \
  -F "file=@test.pdf" \
  -F "user_id=testuser" \
  -F "department=Engineering" \
  -F "tags=test,demo"
```

**Response:**
```json
{
  "message": "File uploaded successfully",
  "s3_key": "users/testuser/2024/06/16/143000/test.pdf",
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

#### 2. Verify File in S3

```bash
aws s3 ls s3://test-video-transcript/users/testuser/ --recursive
```

#### 3. Trigger Knowledge Base Sync

```bash
curl -X POST http://localhost:8000/api/kb/sync \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

**Response:**
```json
{
  "message": "Knowledge Base sync started",
  "ingestion_job_id": "JOB123456",
  "status": "STARTING"
}
```

#### 4. Check Sync Status

```bash
curl http://localhost:8000/api/kb/sync/status/JOB123456
```

Wait until `status` is `COMPLETE` (usually 2-5 minutes).

#### 5. Query the Knowledge Base

```bash
curl -X POST http://localhost:8000/api/kb/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test document",
    "user_id": "testuser",
    "max_results": 5
  }'
```

**Response:**
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
        "author": "John Doe",
        "filename": "test.pdf"
      }
    }
  ]
}
```

---

## Troubleshooting

### Issue: "Token has expired"

**Solution:**
```bash
# Refresh SSO credentials
python get_sso_credentials.py --profile your-sso-profile
```

### Issue: "Bucket does not exist"

**Solution:**
```bash
# Create the bucket
aws s3 mb s3://test-video-transcript --region ap-south-1
```

### Issue: "Knowledge Base not found"

**Solution:**
Check your KB ID in AWS Console:
1. Go to Bedrock → Knowledge bases
2. Find your KB
3. Copy the correct ID to `.env`

### Issue: "Data Source not found"

**Solution:**
```bash
# List data sources
aws bedrock-agent list-data-sources \
  --knowledge-base-id K92XMJHZLR \
  --region ap-south-1

# Add one if needed (see Step 3)
```

---

## Important Notes

### 1. SSO Credentials Expire

Your SSO credentials typically expire in **1-12 hours**. When they expire:

```bash
# Just re-run the helper script
python get_sso_credentials.py --profile your-sso-profile
```

### 2. Knowledge Base Sync

- **Auto-sync**: Bedrock KB syncs hourly by default
- **Manual sync**: Use `POST /api/kb/sync` endpoint
- **Processing time**: 2-10 minutes depending on file size

### 3. Metadata Storage

Metadata is stored in:
- **S3 object metadata** - Attached to each file
- **OpenSearch** - Indexed by Bedrock KB (automatic)
- **Accessible via queries** - Returned with search results

---

## File Organization

Your files will be organized like this:

```
s3://test-video-transcript/
└── users/
    ├── user123/
    │   ├── 2024/06/16/143000/
    │   │   ├── document.pdf
    │   │   ├── video.mp4
    │   │   └── image.jpg
    │   └── 2024/06/17/091500/
    │       └── presentation.pptx
    └── user456/
        └── 2024/06/16/150000/
            └── report.docx
```

---

## What's Next?

After completing the above steps:

1. ✅ Backend is running
2. ✅ Files can be uploaded
3. ✅ Metadata is extracted automatically
4. ✅ Bedrock KB processes everything
5. ✅ Queries return filtered results

**Next phases:**
- 🔄 Build frontend (React/Vue)
- 🔄 Integrate Google Drive OAuth
- 🔄 Add user authentication
- 🔄 Deploy to production (ECS/Fargate)

---

## Quick Commands Reference

```bash
# Get SSO credentials
python get_sso_credentials.py --profile your-profile

# Test credentials
python test_credentials.py

# Start API
python api/app.py

# Upload test file
curl -X POST http://localhost:8000/api/upload/direct \
  -F "file=@test.pdf" -F "user_id=testuser"

# Trigger sync
curl -X POST http://localhost:8000/api/kb/sync \
  -H "Content-Type: application/json" -d '{"force": false}'

# Query KB
curl -X POST http://localhost:8000/api/kb/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "user_id": "testuser", "max_results": 5}'
```

---

## Documentation

- **README.md** - Full documentation
- **SETUP_GUIDE.md** - Step-by-step setup
- **AWS_SSO_SETUP.md** - SSO credential management
- **ARCHITECTURE.md** - Architecture diagrams
- **QUICK_REFERENCE.md** - Command cheatsheet
- **CHANGES.md** - What changed in simplified architecture

---

## Support

If you run into issues:
1. Check logs: `tail -f logs/app.log` (if configured)
2. Test credentials: `python test_credentials.py`
3. Verify AWS resources in Console
4. Check the troubleshooting sections in docs

---

**You're almost there! Just complete Steps 1-7 above and you'll have a working knowledge base! 🚀**
