"""
File Repository Service - Import files from external S3 buckets
into the centralised KB bucket.

Flow:
  User provides source bucket + prefix
      → Backend lists all files under that prefix
      → Downloads each file from source bucket
      → Uploads to centralised KB bucket under file_repo/ folder
      → Extracts metadata
      → Records in ingestion tracker
      → KB incremental sync picks it up automatically
"""

import boto3
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import settings
from utils.logger import get_logger
from .ingestion_tracker import ingestion_tracker
from .metadata_extractor import metadata_extractor

logger = get_logger(__name__)


class FileRepositoryService:
    """
    Handles importing files from external S3 buckets
    into the centralised S3 bucket for KB ingestion.
    """

    def __init__(self):
        aws_credentials = {
            "region_name": settings.AWS_REGION,
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        }
        if settings.AWS_SESSION_TOKEN:
            aws_credentials["aws_session_token"] = settings.AWS_SESSION_TOKEN

        self.s3_client = boto3.client("s3", **aws_credentials)
        self.central_bucket = settings.S3_RAW_BUCKET

    # ------------------------------------------------------------------
    # List files in source bucket
    # ------------------------------------------------------------------

    def list_source_files(
        self,
        source_bucket: str,
        prefix: str = "",
        max_files: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List files available in a source S3 bucket under a given prefix.

        Args:
            source_bucket: Name of the source S3 bucket
            prefix:        Folder path to list (e.g. 'hr-policies/')
            max_files:     Maximum number of files to list

        Returns:
            List of file info dicts
        """
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=source_bucket,
                Prefix=prefix,
                PaginationConfig={"MaxItems": max_files}
            )

            files = []
            for page in pages:
                for obj in page.get("Contents", []):
                    # Skip folder placeholders
                    if obj["Key"].endswith("/"):
                        continue

                    files.append({
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "etag": obj["ETag"].strip('"'),
                        "s3_uri": f"s3://{source_bucket}/{obj['Key']}"
                    })

            logger.info(
                f"Found {len(files)} files in "
                f"s3://{source_bucket}/{prefix}"
            )
            return files

        except Exception as e:
            logger.error(f"Failed to list source files: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # Import single file
    # ------------------------------------------------------------------

    def import_file(
        self,
        source_bucket: str,
        source_key: str,
        user_id: str,
        team_id: Optional[str] = None,
        department: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Copy a single file from source bucket to centralised KB bucket.

        Args:
            source_bucket: Source S3 bucket name
            source_key:    Source file key (path in source bucket)
            user_id:       User importing the file
            team_id:       Optional team ID
            department:    Optional department

        Returns:
            Import result with destination S3 key
        """
        try:
            # If source is already the central bucket — no copy needed,
            # just register in tracker and let KB sync pick it up
            if source_bucket == self.central_bucket:
                logger.info(
                    f"Source is already the central bucket — "
                    f"skipping copy, registering directly"
                )
                head = self.s3_client.head_object(
                    Bucket=self.central_bucket, Key=source_key
                )
                etag = head["ETag"].strip('"')
                ingestion_tracker.record_ingested(source_key, etag)

                return {
                    "status": "success",
                    "filename": filename,
                    "source_uri": f"s3://{source_bucket}/{source_key}",
                    "dest_key": source_key,
                    "dest_uri": f"s3://{self.central_bucket}/{source_key}",
                    "size": head["ContentLength"],
                    "note": "File already in central bucket — registered for KB sync",
                    "metadata": {},
                }

            # Download file content from source bucket
            logger.info(f"Downloading s3://{source_bucket}/{source_key}")
            response = self.s3_client.get_object(
                Bucket=source_bucket,
                Key=source_key
            )
            file_content = response["Body"].read()
            filename = source_key.split("/")[-1]

            # Extract metadata from file content
            content_type = response.get(
                "ContentType", "application/octet-stream"
            )
            extracted_metadata = metadata_extractor.extract_metadata(
                file_content=file_content,
                filename=filename,
                content_type=content_type
            )

            # Build destination key in centralised bucket
            # Preserve the original folder structure under file_repo/
            timestamp = datetime.utcnow().strftime("%Y/%m/%d/%H%M%S")
            dest_key = f"file_repo/{source_bucket}/{source_key}"

            # Build combined metadata
            import json
            combined_metadata = {}
            for k, v in extracted_metadata.items():
                if isinstance(v, (dict, list)):
                    combined_metadata[k] = json.dumps(v)
                else:
                    combined_metadata[k] = str(v)

            combined_metadata.update({
                "source": "file_repository",
                "source_bucket": source_bucket,
                "source_key": source_key,
                "source_uri": f"s3://{source_bucket}/{source_key}",
                "user_id": user_id,
                "import_date": datetime.utcnow().isoformat(),
                "filename": filename,
            })

            if team_id:
                combined_metadata["team_id"] = team_id
            if department:
                combined_metadata["department"] = department

            # Upload to centralised bucket
            self.s3_client.put_object(
                Bucket=self.central_bucket,
                Key=dest_key,
                Body=file_content,
                ContentType=content_type,
                Metadata=combined_metadata,
            )

            # Get ETag of uploaded file and record in tracker
            head = self.s3_client.head_object(
                Bucket=self.central_bucket, Key=dest_key
            )
            etag = head["ETag"].strip('"')
            ingestion_tracker.record_ingested(dest_key, etag)

            logger.info(
                f"Imported s3://{source_bucket}/{source_key} "
                f"→ s3://{self.central_bucket}/{dest_key}"
            )

            return {
                "status": "success",
                "filename": filename,
                "source_uri": f"s3://{source_bucket}/{source_key}",
                "dest_key": dest_key,
                "dest_uri": f"s3://{self.central_bucket}/{dest_key}",
                "size": len(file_content),
                "metadata": combined_metadata,
            }

        except Exception as e:
            logger.error(
                f"Failed to import s3://{source_bucket}/{source_key}: {str(e)}"
            )
            raise

    # ------------------------------------------------------------------
    # Bulk import
    # ------------------------------------------------------------------

    def import_prefix(
        self,
        source_bucket: str,
        prefix: str,
        user_id: str,
        team_id: Optional[str] = None,
        department: Optional[str] = None,
        max_files: int = 1000,
    ) -> Dict[str, Any]:
        """
        Import all files under a prefix from source bucket
        into the centralised KB bucket.

        Args:
            source_bucket: Source S3 bucket name
            prefix:        Folder path (e.g. 'hr-policies/')
            user_id:       User importing the files
            team_id:       Optional team ID
            department:    Optional department
            max_files:     Maximum files to import in one call

        Returns:
            Summary of import results
        """
        files = self.list_source_files(source_bucket, prefix, max_files)

        if not files:
            return {
                "message": "No files found at the given path",
                "source": f"s3://{source_bucket}/{prefix}",
                "imported": 0,
                "failed": 0,
                "results": [],
            }

        results = []
        failed = []

        for file_info in files:
            try:
                result = self.import_file(
                    source_bucket=source_bucket,
                    source_key=file_info["key"],
                    user_id=user_id,
                    team_id=team_id,
                    department=department,
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to import {file_info['key']}: {str(e)}"
                )
                failed.append({
                    "key": file_info["key"],
                    "error": str(e)
                })

        logger.info(
            f"Bulk import complete: {len(results)} succeeded, "
            f"{len(failed)} failed"
        )

        return {
            "message": f"Import complete: {len(results)} files imported",
            "source": f"s3://{source_bucket}/{prefix}",
            "imported": len(results),
            "failed": len(failed),
            "results": results,
            "failures": failed,
        }


# Singleton instance
file_repository_service = FileRepositoryService()
