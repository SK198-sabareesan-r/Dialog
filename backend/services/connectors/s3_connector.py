"""
S3 Connector — Fetches files from an external S3 bucket using user-provided credentials.
"""

import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from typing import List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class S3Connector:
    """Connects to a user's external S3 bucket and lists/downloads files."""

    def test_connection(self, credentials: dict) -> dict:
        """
        Test that the provided credentials can access the bucket.

        credentials:
            bucket: str (required)
            prefix: str (optional, default "")
            aws_access_key_id: str (required)
            aws_secret_access_key: str (required)
            aws_session_token: str (optional — for SSO/temporary credentials)
            region: str (optional, default "ap-south-1")
        """
        try:
            client = self._get_client(credentials)
            bucket = credentials["bucket"]
            prefix = credentials.get("prefix", "")

            # Try listing (limit 1) to verify access
            response = client.list_objects_v2(
                Bucket=bucket, Prefix=prefix, MaxKeys=1
            )
            return {
                "success": True,
                "message": f"Connected to s3://{bucket}/{prefix}",
                "file_count_sample": response.get("KeyCount", 0),
            }
        except ClientError as e:
            code = e.response["Error"]["Code"]
            msg = e.response["Error"]["Message"]
            return {"success": False, "message": f"{code}: {msg}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def list_files(
        self, credentials: dict, target_path: str, since: Optional[datetime] = None
    ) -> List[dict]:
        """
        List files in the external bucket under target_path prefix.
        If `since` is provided, only return files modified after that time.
        """
        client = self._get_client(credentials)
        bucket = credentials["bucket"]
        prefix = target_path or credentials.get("prefix", "")

        files = []
        paginator = client.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]

                # Skip "directories" (keys ending in /)
                if key.endswith("/"):
                    continue

                last_modified = obj["LastModified"]

                # Filter by modification time
                if since and last_modified.replace(tzinfo=None) <= since:
                    continue

                files.append({
                    "id": key,  # S3 key is the unique ID
                    "name": key.split("/")[-1],
                    "path": key,
                    "size": obj["Size"],
                    "modified": last_modified.isoformat(),
                    "etag": obj["ETag"].strip('"'),
                })

        logger.info(f"S3 connector: found {len(files)} files in s3://{bucket}/{prefix}")
        return files

    def download_file(self, credentials: dict, file_id: str) -> bytes:
        """Download a file by its S3 key."""
        client = self._get_client(credentials)
        bucket = credentials["bucket"]

        response = client.get_object(Bucket=bucket, Key=file_id)
        content = response["Body"].read()

        logger.debug(f"Downloaded s3://{bucket}/{file_id} ({len(content)} bytes)")
        return content

    def get_deterministic_key(self, user_id: str, file_info: dict) -> str:
        """Generate a deterministic S3 key for the centralized bucket."""
        filename = file_info["name"]
        source_path = file_info.get("path", filename)
        # Flatten path: replace / with _ to avoid deep nesting
        safe_path = source_path.replace("/", "_").lstrip("_")
        return f"documents/{user_id}/s3/{safe_path}"

    def _get_client(self, credentials: dict):
        """Create an S3 client from user credentials."""
        return boto3.client(
            "s3",
            region_name=credentials.get("region", "ap-south-1"),
            aws_access_key_id=credentials["aws_access_key_id"],
            aws_secret_access_key=credentials["aws_secret_access_key"],
            aws_session_token=credentials.get("aws_session_token"),
        )
