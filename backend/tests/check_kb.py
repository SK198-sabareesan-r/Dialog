import boto3
import os
import sys
sys.path.insert(0, 'c:/Users/Dell/Desktop/demo/backend')

from dotenv import load_dotenv
load_dotenv('c:/Users/Dell/Desktop/demo/backend/config/.env')

client = boto3.client(
    'bedrock-agent',
    region_name=os.getenv('AWS_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    aws_session_token=os.getenv('AWS_SESSION_TOKEN')
)

kb_id = os.getenv('BEDROCK_KB_ID')
ds_id = os.getenv('BEDROCK_DATA_SOURCE_ID')

print(f"KB ID: {kb_id}")
print(f"DS ID: {ds_id}")
print("---")

resp = client.list_ingestion_jobs(
    knowledgeBaseId=kb_id,
    dataSourceId=ds_id,
    maxResults=5
)

jobs = resp.get('ingestionJobSummaries', [])
if not jobs:
    print("No ingestion jobs found.")
else:
    # Get details of the most recent job
    latest = jobs[0]
    job_id = latest['ingestionJobId']
    print(f"Latest Job: {job_id} | Status: {latest['status']}")
    print(f"Stats: {latest.get('statistics', {})}")
    print("---")
    # Get full details including failure reasons
    detail = client.get_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
        ingestionJobId=job_id
    )
    job = detail['ingestionJob']
    print(f"Failure reasons: {job.get('failureReasons', 'None')}")
