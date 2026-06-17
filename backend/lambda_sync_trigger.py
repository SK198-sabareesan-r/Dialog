"""
AWS Lambda function — triggered by EventBridge Scheduler.

Calls the FastAPI /api/kb/incremental-sync endpoint to kick off
incremental ingestion of new/changed S3 files into Bedrock KB.

Deploy steps:
1. Zip this file: zip lambda_sync_trigger.zip lambda_sync_trigger.py
2. Upload to Lambda (runtime: Python 3.11, handler: lambda_sync_trigger.lambda_handler)
3. Set environment variables:
     API_URL = https://your-deployed-api.example.com
     API_KEY = your-secret-key  (optional)
4. Create EventBridge schedule targeting this Lambda
"""

import json
import os
import urllib.request
import urllib.error


def lambda_handler(event, context):
    """
    Lambda handler called by EventBridge Scheduler.

    Environment variables:
        API_URL — base URL of the deployed FastAPI app
        API_KEY — optional secret for x-api-key header
    """
    api_url = os.environ.get("API_URL", "").rstrip("/")
    api_key = os.environ.get("API_KEY", "")

    if not api_url:
        raise ValueError("API_URL environment variable is not set")

    endpoint = f"{api_url}/api/kb/incremental-sync"
    payload = json.dumps({"source": "eventbridge_scheduler"}).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            print(f"[SUCCESS] Incremental sync triggered: {body}")
            return {"statusCode": 200, "body": body}

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"[ERROR] HTTP {e.code}: {error_body}")
        raise RuntimeError(f"API returned HTTP {e.code}: {error_body}")

    except urllib.error.URLError as e:
        print(f"[ERROR] Failed to reach API: {str(e)}")
        raise RuntimeError(f"Failed to reach API at {endpoint}: {str(e)}") from e
