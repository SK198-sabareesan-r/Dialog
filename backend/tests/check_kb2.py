import boto3, os, time
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

# Trigger a fresh sync
print("Triggering KB sync...")
resp = client.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)
job_id = resp['ingestionJob']['ingestionJobId']
print(f"Job started: {job_id}")

# Poll until complete
for i in range(20):
    time.sleep(5)
    detail = client.get_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id, ingestionJobId=job_id)
    job = detail['ingestionJob']
    status = job['status']
    print(f"  [{i*5}s] Status: {status}")
    if status in ('COMPLETE', 'FAILED', 'STOPPED'):
        print(f"  Stats: {job.get('statistics', {})}")
        print(f"  Failures: {job.get('failureReasons', 'None')}")
        break
