import json
from datetime import datetime
from typing import Dict, Any, Optional
from .aws_client import aws_clients
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class S3Service:
    """Service for S3 operations"""

    def __init__(self):
        self.s3_client = aws_clients.get_s3_client()
        self.raw_bucket = settings.S3_RAW_BUCKET
        self.processed_bucket = settings.S3_PROCESSED_BUCKET

    def upload_to_raw_zone(
        self,
        file_content: bytes,
        file_name: str,
        source: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload file to S3 raw zone"""
        timestamp = datetime.utcnow().strftime('%Y/%m/%d/%H%M%S')
        s3_key = f"{source}/{timestamp}/{file_name}"

        upload_metadata = metadata or {}
        upload_metadata.update({
            'source': source,
            'upload_timestamp': datetime.utcnow().isoformat(),
            'original_filename': file_name
        })

        try:
            self.s3_client.put_object(
                Bucket=self.raw_bucket,
                Key=s3_key,
                Body=file_content,
                Metadata=upload_metadata
            )

            logger.info(f"File uploaded to raw zone: s3://{self.raw_bucket}/{s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"Failed to upload to raw zone: {str(e)}")
            raise

    def get_object(self, bucket: str, key: str) -> bytes:
        """Get object from S3"""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response['Body'].read()
        except Exception as e:
            logger.error(f"Failed to get object {key} from {bucket}: {str(e)}")
            raise

    def put_processed_output(
        self,
        output_data: Dict[str, Any],
        source_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Save processed output to S3 processed zone"""
        processed_key = source_key.replace('raw', 'processed') + '.json'

        upload_metadata = metadata or {}
        upload_metadata.update({
            'processing_timestamp': datetime.utcnow().isoformat(),
            'source_key': source_key
        })

        try:
            self.s3_client.put_object(
                Bucket=self.processed_bucket,
                Key=processed_key,
                Body=json.dumps(output_data, indent=2),
                ContentType='application/json',
                Metadata=upload_metadata
            )

            logger.info(f"Processed output saved: s3://{self.processed_bucket}/{processed_key}")
            return processed_key

        except Exception as e:
            logger.error(f"Failed to save processed output: {str(e)}")
            raise

    def list_objects(
        self,
        bucket: str,
        prefix: str = '',
        max_keys: int = 1000
    ) -> list:
        """List objects in S3 bucket"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            return response.get('Contents', [])
        except Exception as e:
            logger.error(f"Failed to list objects in {bucket}/{prefix}: {str(e)}")
            raise

    def copy_object(
        self,
        source_bucket: str,
        source_key: str,
        dest_bucket: str,
        dest_key: str
    ) -> None:
        """Copy object between S3 buckets"""
        try:
            copy_source = {'Bucket': source_bucket, 'Key': source_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=dest_key
            )
            logger.info(f"Object copied from {source_bucket}/{source_key} to {dest_bucket}/{dest_key}")
        except Exception as e:
            logger.error(f"Failed to copy object: {str(e)}")
            raise

s3_service = S3Service()
