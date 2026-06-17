# EventBridge Deployment Guide
## Activating Scheduled Incremental Sync in Production

This guide explains what you need to do when deploying to production
to switch from the local APScheduler to AWS EventBridge.

---

## What You Are Setting Up

```
Every 1 hour (or your chosen schedule)
        ↓
AWS EventBridge Scheduler
        ↓
AWS Lambda (lambda_sync_trigger.py)
        ↓
POST https://your-api.com/api/kb/incremental-sync
        ↓
Scans S3 → finds new/changed files → triggers Bedrock KB ingestion
```

---

## Before You Start

Make sure you have:
- [ ] Your FastAPI app deployed and running (EC2 / ECS / Elastic Beanstalk)
- [ ] The public URL of your deployed app (e.g. `https://your-api.example.com`)
- [ ] AWS Console access with permissions for Lambda and EventBridge

---

## Step 1 — Update Your Production .env

In your deployed app's `.env` file, change these two values:

```
USE_EVENTBRIDGE=true        # disables APScheduler
SYNC_INTERVAL_MINUTES=60    # no longer used, but keep it for reference
```

Then restart your app. APScheduler will no longer run.

---

## Step 2 — Create the Lambda Function

1. Go to **AWS Console → Lambda → Create function**

2. Fill in:
   - **Function name:** `kb-incremental-sync-trigger`
   - **Runtime:** Python 3.11
   - **Architecture:** x86_64

3. Click **Create function**

4. In the **Code** tab, delete the default code and paste the
   contents of `backend/lambda_sync_trigger.py` from this repo

5. Click **Deploy**

---

## Step 3 — Set Lambda Environment Variables

Still in Lambda, go to **Configuration → Environment variables → Edit**

Add these:

| Key | Value |
|-----|-------|
| `API_URL` | `https://your-api.example.com` (your deployed app URL, no trailing slash) |
| `API_KEY` | leave empty for now (optional security header) |

Click **Save**

---

## Step 4 — Set Lambda Timeout

By default Lambda times out in 3 seconds. Increase it:

Go to **Configuration → General configuration → Edit**
- **Timeout:** 30 seconds
- Click **Save**

---

## Step 5 — Create the EventBridge Schedule

1. Go to **AWS Console → EventBridge → Schedules → Create schedule**

2. Fill in:
   - **Schedule name:** `kb-incremental-sync-hourly`
   - **Schedule pattern:** Recurring schedule
   - **Rate expression:** `rate(1 hour)`
     - For every 30 mins: `rate(30 minutes)`
     - For a specific time daily: `cron(0 9 * * ? *)` (9am UTC every day)

3. Click **Next**

4. On the Target screen:
   - **Target type:** AWS Lambda
   - **Lambda function:** select `kb-incremental-sync-trigger`

5. Click **Next → Next → Create schedule**

---

## Step 6 — Test It Manually

Before waiting for the schedule, test it right now:

1. Go to **Lambda → kb-incremental-sync-trigger → Test**
2. Create a new test event with this payload:
   ```json
   { "source": "manual_test" }
   ```
3. Click **Test**
4. You should see a green success response in the output
5. Check your app logs — you should see "Incremental sync triggered"

---

## Step 7 — Verify in CloudWatch

1. Go to **CloudWatch → Log groups**
2. Find `/aws/lambda/kb-incremental-sync-trigger`
3. Open the latest log stream
4. You should see either:
   - `[SUCCESS] Incremental sync triggered` — everything working
   - `[ERROR]` — check the error message and verify `API_URL` is correct

---

## Summary of AWS Resources Created

| Resource | Name |
|----------|------|
| Lambda function | `kb-incremental-sync-trigger` |
| EventBridge schedule | `kb-incremental-sync-hourly` |
| Lambda env var | `API_URL` = your app URL |

---

## Switching Back to APScheduler (if needed)

If you want to go back to APScheduler for any reason:

1. In your app's `.env`:
   ```
   USE_EVENTBRIDGE=false
   SYNC_INTERVAL_MINUTES=60
   ```
2. Restart the app
3. APScheduler takes over automatically
4. You can disable (not delete) the EventBridge schedule in the console

---

## Common Issues

| Problem | Fix |
|---------|-----|
| Lambda times out | Increase timeout to 30s (Step 4) |
| `API_URL not set` error | Check Lambda environment variables (Step 3) |
| `Connection refused` | Your app is not publicly accessible, check deployment |
| `HTTP 422` error | API_URL has a trailing slash — remove it |
| Nothing happening | Check EventBridge schedule is **enabled** not paused |
