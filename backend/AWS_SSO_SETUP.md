# AWS SSO Setup Guide

## Overview

AWS SSO (Single Sign-On) provides temporary credentials that are more secure than long-term access keys. This guide shows you how to use SSO credentials with this application.

---

## Quick Start

### Option 1: Automated Script (Easiest)

```bash
# Run the helper script
python get_sso_credentials.py --profile your-sso-profile

# Follow the prompts - it will:
# 1. Login to AWS SSO (opens browser)
# 2. Fetch temporary credentials
# 3. Update your .env file automatically
```

### Option 2: Manual Setup

```bash
# 1. Login to AWS SSO
aws sso login --profile your-sso-profile

# 2. Get credentials in env format
aws configure export-credentials --profile your-sso-profile --format env

# 3. Copy the output to your .env file
```

---

## Detailed Setup

### Step 1: Configure AWS SSO Profile

If you haven't set up your SSO profile yet:

```bash
aws configure sso
```

**You'll be prompted for:**
```
SSO start URL: https://your-company.awsapps.com/start
SSO region: ap-south-1
SSO account ID: 106611079163
SSO role name: YourRole
CLI default region: ap-south-1
CLI default output format: json
CLI profile name: your-profile-name
```

This creates a profile in `~/.aws/config`:
```ini
[profile your-profile-name]
sso_start_url = https://your-company.awsapps.com/start
sso_region = ap-south-1
sso_account_id = 106611079163
sso_role_name = YourRole
region = ap-south-1
output = json
```

### Step 2: Login to AWS SSO

```bash
aws sso login --profile your-profile-name
```

**What happens:**
1. Opens browser to SSO login page
2. You authenticate with your company credentials
3. AWS CLI caches the session
4. Session typically lasts 1-12 hours

### Step 3: Get Temporary Credentials

```bash
# Export credentials as environment variables
aws configure export-credentials --profile your-profile-name --format env
```

**Output example:**
```
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=FwoGZXIvYXdzEBYaDCvTMU...very long token...
```

### Step 4: Update `.env` File

Copy the credentials to `config/.env`:

```env
# AWS Credentials (SSO - Temporary)
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=FwoGZXIvYXdzEBYaDCvTMU...your-long-token...

# S3 Storage
S3_RAW_BUCKET=test-video-transcript

# Bedrock Knowledge Base
BEDROCK_KB_ID=K92XMJHZLR
BEDROCK_DATA_SOURCE_ID=your-data-source-id
BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v1
```

---

## Using the Helper Script

### Basic Usage

```bash
# Use default profile
python get_sso_credentials.py

# Use specific profile
python get_sso_credentials.py --profile dev
python get_sso_credentials.py --profile production
```

### What the Script Does

1. **Checks login status**
   ```
   [1/3] Checking SSO login status for profile 'your-profile'...
   ✅ Already logged in as: arn:aws:iam::123456789012:user/yourname
   ```

2. **Fetches credentials**
   ```
   [2/3] Fetching temporary credentials...
   ✅ Credentials retrieved successfully!
   ```

3. **Displays & updates**
   ```
   [3/3] Your temporary AWS credentials:
   ================================================================================
   AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
   AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
   AWS_SESSION_TOKEN=FwoGZXIvYXdzEBYaDCvTMU...
   ================================================================================

   📝 Update config/.env? (y/n): y
   ✅ Updated config/.env
   ```

---

## Credential Expiration

### How Long Do Credentials Last?

SSO temporary credentials typically expire after:
- **1 hour** (default for most organizations)
- **4 hours** (extended session)
- **12 hours** (maximum)

### What Happens When They Expire?

You'll see errors like:
```
ExpiredToken: The security token included in the request is expired
```

### Solution: Refresh Credentials

```bash
# Re-run the helper script
python get_sso_credentials.py --profile your-profile

# Or manually
aws sso login --profile your-profile
aws configure export-credentials --profile your-profile --format env
# Then update .env
```

---

## Automated Credential Refresh

### Option 1: Cron Job (Linux/Mac)

```bash
# Edit crontab
crontab -e

# Add line to refresh every hour
0 * * * * cd /path/to/backend && python get_sso_credentials.py --profile your-profile
```

### Option 2: Task Scheduler (Windows)

1. Open **Task Scheduler**
2. Create new task
3. Trigger: Every 1 hour
4. Action: Run Python script
   ```
   Program: python
   Arguments: C:\path\to\backend\get_sso_credentials.py --profile your-profile
   ```

### Option 3: Watch Script

Create `watch_credentials.sh`:
```bash
#!/bin/bash
while true; do
    echo "Checking credentials..."
    aws sts get-caller-identity --profile your-profile > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Credentials expired! Refreshing..."
        python get_sso_credentials.py --profile your-profile
    fi
    sleep 3600  # Check every hour
done
```

---

## Environment Variables vs .env File

### Using .env File (Current Approach)

**Pros:**
- Simple to use
- Works with docker-compose
- Easy to update

**Cons:**
- Need to refresh .env when credentials expire
- Credentials stored in file (less secure)

### Using Environment Variables (Alternative)

Set credentials directly in your shell:

```bash
# Export credentials
export AWS_ACCESS_KEY_ID=ASIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_SESSION_TOKEN=FwoGZXIvYXdzEBYaDCvTMU...

# Then run your app
python api/app.py
```

**To use environment variables instead of .env:**

Remove credentials from `.env` and the app will automatically use environment variables:

```env
# Don't set these - use environment variables instead
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_SESSION_TOKEN=

# Still set region and other configs
AWS_REGION=ap-south-1
S3_RAW_BUCKET=test-video-transcript
```

---

## Using AWS Profile Directly

### Option 3: Let Boto3 Use AWS Profile

If you have SSO configured in `~/.aws/config`, boto3 can use it directly:

**Update `settings.py`:**
```python
class Settings:
    # Option 1: Explicit credentials (current)
    AWS_REGION = os.getenv('AWS_REGION', 'ap-south-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_SESSION_TOKEN = os.getenv('AWS_SESSION_TOKEN')
    
    # Option 2: Use profile name
    AWS_PROFILE = os.getenv('AWS_PROFILE', 'default')
```

**Update service initialization:**
```python
# Use profile instead of explicit credentials
if settings.AWS_PROFILE:
    session = boto3.Session(profile_name=settings.AWS_PROFILE)
    self.s3_client = session.client('s3')
else:
    # Fall back to explicit credentials
    self.s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN
    )
```

**Then in `.env`:**
```env
AWS_PROFILE=your-sso-profile
```

**Pros:**
- Automatic credential refresh (boto3 handles it)
- No need to manually update .env

**Cons:**
- Requires AWS CLI to be configured
- User must run `aws sso login` manually

---

## Troubleshooting

### Error: "Token has expired"

```
botocore.exceptions.ClientError: An error occurred (ExpiredToken) when calling the operation: The security token included in the request is expired
```

**Solution:**
```bash
# Refresh credentials
python get_sso_credentials.py --profile your-profile
```

### Error: "SSO session has expired"

```
Error when retrieving credentials from sso: Token has expired and refresh failed
```

**Solution:**
```bash
# Re-login to SSO
aws sso login --profile your-profile

# Then get credentials
python get_sso_credentials.py --profile your-profile
```

### Error: "Profile not found"

```
The config profile (your-profile) could not be found
```

**Solution:**
```bash
# Configure SSO profile
aws configure sso
```

### Error: "Unable to locate credentials"

```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solution:**
```bash
# Check .env file has credentials
cat config/.env | grep AWS_

# Or set environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
```

---

## Security Best Practices

### 1. Never Commit Credentials

Add to `.gitignore`:
```
config/.env
.env
*.env
```

### 2. Use Short-Lived Credentials

SSO temporary credentials are more secure than long-term access keys.

### 3. Rotate Regularly

Even though they expire automatically, rotate them frequently:
```bash
# Every 1 hour
python get_sso_credentials.py --profile your-profile
```

### 4. Use IAM Roles When Possible

In production (EC2, ECS, Lambda), use IAM roles instead of SSO:
- EC2 instance roles
- ECS task roles
- Lambda execution roles

### 5. Limit Permissions

Ensure your SSO role has minimal permissions:
- S3: PutObject, GetObject on specific bucket
- Bedrock: InvokeModel, ManageKnowledgeBase on specific KB
- No admin permissions

---

## Production Deployment

### Using EC2 Instance Roles (Recommended)

**No credentials needed!**

1. Attach IAM role to EC2 instance
2. Remove credentials from `.env`:
   ```env
   # No credentials needed - EC2 role provides them
   AWS_REGION=ap-south-1
   S3_RAW_BUCKET=test-video-transcript
   ```
3. Boto3 automatically uses instance role

### Using ECS Task Roles (Recommended)

Similar to EC2:
1. Define task role in ECS task definition
2. No credentials in `.env`
3. ECS provides credentials automatically

### Using Secrets Manager (Alternative)

Store credentials in AWS Secrets Manager:

```python
import boto3
import json

def get_credentials():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='kb-api-credentials')
    return json.loads(response['SecretString'])

# Then use in settings
creds = get_credentials()
AWS_ACCESS_KEY_ID = creds['access_key_id']
```

---

## Summary

### Development (SSO)

```bash
# Every time credentials expire (1-12 hours)
python get_sso_credentials.py --profile your-profile

# Or set up auto-refresh
crontab -e  # Add hourly refresh
```

### Production (IAM Roles)

```
No manual credential management needed!
Use EC2/ECS instance/task roles.
```

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `aws configure sso` | Setup SSO profile |
| `aws sso login --profile X` | Login to SSO |
| `aws configure export-credentials --profile X` | Get temp credentials |
| `python get_sso_credentials.py --profile X` | Automated login + update .env |
| `aws sts get-caller-identity` | Verify credentials work |

---

**Need help?** Check the main `README.md` or `SETUP_GUIDE.md`
