"""
Upload Service - Handles file uploads to S3 and KB sync
"""

import json
import boto3
from datetime import datetime
from typing import Dict, Any, Optional, List
from config import settings
from utils.logger import get_logger
from .ingestion_tracker import ingestion_tracker

logger = get_logger(__name__)

class UploadService:
    """Service for handling file uploads and KB synchronization"""

    def __init__(self):
        # Build AWS credentials dict (supports SSO session tokens)
        aws_credentials = {
            'region_name': settings.AWS_REGION,
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY
        }

        # Add session token if present (for SSO/temporary credentials)
        if settings.AWS_SESSION_TOKEN:
            aws_credentials['aws_session_token'] = settings.AWS_SESSION_TOKEN

        self.s3_client = boto3.client('s3', **aws_credentials)
        self.bedrock_agent_client = boto3.client('bedrock-agent', **aws_credentials)
        self.bucket = settings.S3_RAW_BUCKET
        self.kb_id = settings.BEDROCK_KB_ID
        self.data_source_id = settings.BEDROCK_DATA_SOURCE_ID

    def generate_presigned_url(
        self,
        file_name: str,
        file_type: str,
        user_id: str,
        custom_metadata: Dict[str, str],
        expires_in: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate pre-signed URL for direct S3 upload

        This allows frontend to upload directly to S3 without going through backend.
        """
        # Generate S3 key with user isolation
        timestamp = datetime.utcnow().strftime('%Y/%m/%d/%H%M%S')
        s3_key = f"users/{user_id}/{timestamp}/{file_name}"

        # Sanitize metadata to ASCII (S3 requirement)
        ascii_metadata = {
            k: str(v).encode('ascii', errors='replace').decode('ascii')
            for k, v in custom_metadata.items()
        }

        try:
            # Generate pre-signed URL
            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': s3_key,
                    'ContentType': file_type,
                    'Metadata': ascii_metadata
                },
                ExpiresIn=expires_in
            )

            logger.info(f"Generated pre-signed URL for {s3_key}")

            return {
                'upload_url': url,
                's3_key': s3_key,
                's3_uri': f"s3://{self.bucket}/{s3_key}"
            }

        except Exception as e:
            logger.error(f"Failed to generate pre-signed URL: {str(e)}")
            raise

    def upload_to_s3(
        self,
        file_content: bytes,
        file_name: str,
        user_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload file to S3 with metadata

        Metadata is stored as S3 object metadata and will be available to Bedrock KB.
        """
        # Generate S3 key with user isolation
        timestamp = datetime.utcnow().strftime('%Y/%m/%d/%H%M%S')
        s3_key = f"users/{user_id}/{timestamp}/{file_name}"

        # Convert all metadata values to strings (S3 requirement)
        # S3 metadata keys and values must be ASCII only — strip/replace non-ASCII chars
        string_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (dict, list)):
                raw = json.dumps(value)
            else:
                raw = str(value)
            # Encode to ASCII, replacing any non-ASCII characters with '?'
            string_metadata[key] = raw.encode('ascii', errors='replace').decode('ascii')

        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_content,
                Metadata=string_metadata
            )

            logger.info(f"Uploaded file to S3: s3://{self.bucket}/{s3_key}")
            logger.info(f"Metadata: {string_metadata}")

            # Get the ETag of the uploaded object for incremental tracking
            head = self.s3_client.head_object(Bucket=self.bucket, Key=s3_key)
            etag = head["ETag"].strip('"')

            # Trigger Bedrock KB sync immediately so the new file is ingested
            try:
                sync_result = self.trigger_kb_sync()
                logger.info(f"KB sync triggered after upload: job={sync_result['ingestion_job_id']}")
            except Exception as sync_err:
                logger.warning(f"KB sync trigger failed after upload (file is in S3): {sync_err}")
                sync_result = {}

            # Record in ingestion tracker AFTER triggering sync
            ingestion_tracker.record_ingested(s3_key, etag)

            return {
                's3_key': s3_key,
                's3_uri': f"s3://{self.bucket}/{s3_key}",
                'metadata': string_metadata,
                'ingestion_job_id': sync_result.get('ingestion_job_id')
            }

        except Exception as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            raise

    def trigger_kb_sync(self, force: bool = False) -> Dict[str, Any]:
        """
        Trigger manual KB sync

        This starts an ingestion job that scans S3 and ingests all new/updated files.
        """
        try:
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                description=f"Manual sync triggered at {datetime.utcnow().isoformat()}"
            )

            ingestion_job = response['ingestionJob']

            logger.info(f"Started KB ingestion job: {ingestion_job['ingestionJobId']}")

            return {
                'ingestion_job_id': ingestion_job['ingestionJobId'],
                'status': ingestion_job['status'],
                'kb_id': self.kb_id,
                'data_source_id': self.data_source_id,
                'started_at': ingestion_job.get('startedAt', datetime.utcnow()).isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to trigger KB sync: {str(e)}")
            raise

    def get_sync_status(self, ingestion_job_id: str) -> Dict[str, Any]:
        """Get status of KB ingestion job"""
        try:
            response = self.bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                ingestionJobId=ingestion_job_id
            )

            job = response['ingestionJob']

            return {
                'ingestion_job_id': ingestion_job_id,
                'status': job['status'],
                'started_at': job.get('startedAt'),
                'completed_at': job.get('completedAt'),
                'updated_at': job.get('updatedAt'),
                'statistics': job.get('statistics', {}),
                'failure_reasons': job.get('failureReasons', [])
            }

        except Exception as e:
            logger.error(f"Failed to get sync status: {str(e)}")
            raise

    def get_file_metadata(self, s3_key: str) -> Dict[str, Any]:
        """Get metadata for a specific S3 object"""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket,
                Key=s3_key
            )

            return {
                'metadata': response.get('Metadata', {}),
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified').isoformat() if response.get('LastModified') else None,
                'etag': response.get('ETag')
            }

        except Exception as e:
            logger.error(f"Failed to get file metadata: {str(e)}")
            raise

    def list_user_documents(
        self,
        user_id: str,
        team_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List documents uploaded by a user

        Returns list of documents with their metadata.
        """
        prefix = f"users/{user_id}/"

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=limit
            )

            documents = []

            for obj in response.get('Contents', []):
                # Get object metadata
                head = self.s3_client.head_object(
                    Bucket=self.bucket,
                    Key=obj['Key']
                )

                doc_metadata = head.get('Metadata', {})

                # Filter by team_id if specified
                if team_id and doc_metadata.get('team_id') != team_id:
                    continue

                documents.append({
                    's3_key': obj['Key'],
                    'filename': doc_metadata.get('filename', obj['Key'].split('/')[-1]),
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'metadata': doc_metadata
                })

            logger.info(f"Found {len(documents)} documents for user {user_id}")

            return documents

        except Exception as e:
            logger.error(f"Failed to list user documents: {str(e)}")
            raise

# Singleton instance
upload_service = UploadService()
