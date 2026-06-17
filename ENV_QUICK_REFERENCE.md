# .env Configuration - Quick Reference

## 📍 Location
**File:** `backend/config/.env`

## 🚀 Quick Setup

```bash
# The .env file is already created at backend/config/.env
# Edit it with your AWS credentials
```

## 📋 What You Need to Fill

### 1️⃣ **AWS Credentials** (REQUIRED)
```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCY
```
**Get from:** AWS Console → IAM → Users → Security credentials → Create access key

---

### 2️⃣ **S3 Buckets** (REQUIRED)
```env
S3_RAW_BUCKET=my-pipeline-raw
S3_PROCESSED_BUCKET=my-pipeline-processed
```
**Create with:**
```bash
aws s3 mb s3://my-pipeline-raw --region us-east-1
aws s3 mb s3://my-pipeline-processed --region us-east-1
```

---

### 3️⃣ **Bedrock Data Automation** (REQUIRED for document processing)
```env
BEDROCK_DATA_AUTOMATION_JOB_ARN=arn:aws:bedrock:us-east-1:123456789012:data-automation-project/abc123
```
**Get from:** AWS Console → Bedrock → Data Automation → Create project → Copy ARN

---

### 4️⃣ **Knowledge Base** (REQUIRED for retrieval)
```env
BEDROCK_KB_ID=XYZABC123
```
**Get from:** AWS Console → Bedrock → Knowledge bases → Create KB → Copy ID

---

### 5️⃣ **OpenSearch** (REQUIRED for vector storage)
```env
OPENSEARCH_ENDPOINT=https://search-kb-abc123.us-east-1.aoss.amazonaws.com
```
**Get from:** Created automatically with Knowledge Base, or create OpenSearch domain

---

### 6️⃣ **Step Functions** (REQUIRED for orchestration)
```env
STEP_FUNCTION_ARN=arn:aws:states:us-east-1:123456789012:stateMachine:pipeline
```
**Get from:** AWS Console → Step Functions → Create state machine → Copy ARN

---

### 7️⃣ **SQS Queues** (REQUIRED for error handling)
```env
SQS_DLQ_URL=https://sqs.us-east-1.amazonaws.com/123456789012/ingestion-dlq
SQS_RETRY_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/ingestion-retry
```
**Create with:**
```bash
aws sqs create-queue --queue-name ingestion-dlq
aws sqs create-queue --queue-name ingestion-retry
```

---

## ⚡ Minimal Setup (For Testing Format Detection Only)

Only fill these to test format detection without full AWS setup:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_RAW_BUCKET=test-bucket
S3_PROCESSED_BUCKET=test-bucket-processed
```

Leave others as placeholder values. Format detection will work, but actual processing will fail.

---

## 🧪 Test Your Configuration

```bash
cd backend
python -c "from config.settings import settings; settings.validate()"
```

✅ No output = Configuration valid  
❌ Error message = Missing required fields

---

## 📚 Detailed Guide

For step-by-step instructions on getting each value, see:
- **Full Guide:** `backend/ENV_SETUP_GUIDE.md`
- **Testing:** `QUICK_START_FORMAT_TESTING.md`

---

## 🔑 Where to Get AWS Resources

| Resource | AWS Console Path |
|----------|-----------------|
| Access Keys | IAM → Users → Security credentials |
| S3 Buckets | S3 → Create bucket |
| Bedrock BDA | Bedrock → Data Automation |
| Knowledge Base | Bedrock → Knowledge bases |
| OpenSearch | OpenSearch Service → Domains/Collections |
| Step Functions | Step Functions → State machines |
| SQS Queues | SQS → Create queue |
| SNS Topics | SNS → Topics → Create topic |

---

## 🛡️ Security Reminder

- ✅ `.env` is in `.gitignore` (don't commit it)
- ✅ Use `.env.example` as template for sharing
- ✅ Rotate access keys every 90 days
- ✅ Use IAM roles on EC2/ECS (no keys needed)

---

## ❓ Common Questions

**Q: Do I need all these services to test format detection?**  
A: No, just AWS credentials + S3 buckets. Format detection works locally.

**Q: What if I don't have Bedrock access?**  
A: You can test format detection and S3 upload. Processing will fail but validation works.

**Q: Can I use existing S3 buckets?**  
A: Yes, just put the bucket names in `.env`

**Q: How much will this cost?**  
A: 
- S3: $0.023/GB
- Bedrock: $0.30 per 1000 images
- Textract: $1.50 per 1000 pages
- Transcribe: $0.024 per minute
- OpenSearch: $0.24/hour (Serverless)

---

## 🎯 Next Steps

1. ✅ Edit `backend/config/.env` with your values
2. ✅ Run validation test
3. ✅ Start backend: `cd backend/api && python main.py`
4. ✅ Test endpoint: `http://localhost:8000/api/v1/formats/supported`
5. ✅ Upload test file via frontend or curl
