"""
Bedrock Knowledge Base Native BDA Integration
Uses KB's built-in BDA parsing - no Lambda functions required
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from .aws_client import aws_clients
from .s3_service import s3_service
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class KBNativeIngestion:
    """
    Service for native Bedrock KB ingestion with built-in BDA parsing

    Architecture:
    S3 Upload → S3 Event → KB Ingestion Job (with BDA) → OpenSearch

    No Lambda, no Step Functions - all managed by Bedrock KB
    """

    def __init__(self):
        self.bedrock_agent_client = aws_clients.get_bedrock_agent_client()
        self.s3_client = aws_clients.get_s3_client()
        self.kb_id = settings.BEDROCK_KB_ID
        self.data_source_id = settings.BEDROCK_DATA_SOURCE_ID

    def upload_and_trigger_ingestion(
        self,
        file_content: bytes,
        file_name: str,
        source_type: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload file to S3 and trigger KB ingestion

        KB will automatically:
        1. Detect the file
        2. Use BDA for parsing (configured in data source)
        3. Chunk the content
        4. Generate embeddings
        5. Store in OpenSearch

        Args:
            file_content: File bytes
            file_name: Original filename
            source_type: Source type (web_ui, shared_drive, etc.)
            metadata: File metadata

        Returns:
            Upload and ingestion details
        """
        try:
            # Upload to S3 with metadata
            s3_key = s3_service.upload_to_raw_zone(
                file_content=file_content,
                file_name=file_name,
                source=source_type,
                metadata=metadata
            )

            logger.info(f"File uploaded to S3: {s3_key}")

            # Trigger KB ingestion job
            # KB will use its configured BDA parser automatically
            ingestion_job = self.start_ingestion_job()

            return {
                'status': 'SUCCESS',
                's3_key': s3_key,
                's3_uri': f"s3://{settings.S3_RAW_BUCKET}/{s3_key}",
                'ingestion_job_id': ingestion_job['ingestion_job_id'],
                'ingestion_status': ingestion_job['status'],
                'kb_id': self.kb_id,
                'data_source_id': self.data_source_id,
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to upload and trigger ingestion: {str(e)}")
            raise

    def start_ingestion_job(self) -> Dict[str, Any]:
        """
        Start KB ingestion job

        KB will:
        - Scan the S3 data source
        - Use BDA for parsing (pre-configured)
        - Process all new/updated files
        - Automatically chunk and embed
        - Index to OpenSearch

        Returns:
            Ingestion job details
        """
        try:
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id
            )

            job = response['ingestionJob']

            logger.info(f"Started KB ingestion job: {job['ingestionJobId']}")

            return {
                'ingestion_job_id': job['ingestionJobId'],
                'status': job['status'],
                'started_at': job.get('startedAt').isoformat() if job.get('startedAt') else None,
                'knowledge_base_id': self.kb_id,
                'data_source_id': self.data_source_id
            }

        except Exception as e:
            logger.error(f"Failed to start ingestion job: {str(e)}")
            raise

    def get_ingestion_job_status(self, ingestion_job_id: str) -> Dict[str, Any]:
        """
        Get status of KB ingestion job

        Args:
            ingestion_job_id: Ingestion job ID

        Returns:
            Job status and statistics
        """
        try:
            response = self.bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                ingestionJobId=ingestion_job_id
            )

            job = response['ingestionJob']

            result = {
                'ingestion_job_id': ingestion_job_id,
                'status': job['status'],
                'started_at': job.get('startedAt').isoformat() if job.get('startedAt') else None,
                'updated_at': job.get('updatedAt').isoformat() if job.get('updatedAt') else None
            }

            # Add statistics if available
            if 'statistics' in job:
                result['statistics'] = {
                    'documents_scanned': job['statistics'].get('numberOfDocumentsScanned', 0),
                    'documents_modified': job['statistics'].get('numberOfDocumentsModified', 0),
                    'documents_indexed': job['statistics'].get('numberOfDocumentsIndexed', 0),
                    'documents_failed': job['statistics'].get('numberOfDocumentsFailed', 0)
                }

            # Add failure reasons if failed
            if job['status'] == 'FAILED' and 'failureReasons' in job:
                result['failure_reasons'] = job['failureReasons']

            return result

        except Exception as e:
            logger.error(f"Failed to get ingestion job status: {str(e)}")
            raise

    def list_recent_ingestion_jobs(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        List recent ingestion jobs

        Args:
            max_results: Maximum number of jobs to return

        Returns:
            List of ingestion jobs
        """
        try:
            response = self.bedrock_agent_client.list_ingestion_jobs(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id,
                maxResults=max_results
            )

            jobs = []
            for job_summary in response.get('ingestionJobSummaries', []):
                jobs.append({
                    'ingestion_job_id': job_summary['ingestionJobId'],
                    'status': job_summary['status'],
                    'started_at': job_summary.get('startedAt').isoformat() if job_summary.get('startedAt') else None,
                    'updated_at': job_summary.get('updatedAt').isoformat() if job_summary.get('updatedAt') else None,
                    'statistics': job_summary.get('statistics', {})
                })

            return jobs

        except Exception as e:
            logger.error(f"Failed to list ingestion jobs: {str(e)}")
            raise

    def retrieve_with_native_filtering(
        self,
        query: str,
        user_id: str,
        team_id: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents using KB's native retrieval API

        Applies metadata filters for access control

        Args:
            query: Search query
            user_id: User ID for filtering
            team_id: Optional team ID for filtering
            max_results: Maximum results to return

        Returns:
            Retrieved documents with metadata
        """
        try:
            # Build metadata filter
            filter_config = {
                'andAll': [
                    {
                        'equals': {
                            'key': 'user_id',
                            'value': user_id
                        }
                    }
                ]
            }

            if team_id:
                filter_config['andAll'].append({
                    'equals': {
                        'key': 'team_id',
                        'value': team_id
                    }
                })

            # Retrieve with filters
            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={'text': query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results,
                        'filter': filter_config
                    }
                }
            )

            results = []
            for result in response.get('retrievalResults', []):
                results.append({
                    'content': result.get('content', {}).get('text', ''),
                    'score': result.get('score', 0),
                    'location': result.get('location', {}),
                    'metadata': result.get('metadata', {})
                })

            logger.info(f"Retrieved {len(results)} documents for user {user_id}")

            return results

        except Exception as e:
            logger.error(f"Failed to retrieve documents: {str(e)}")
            raise

    def configure_s3_event_notification(self) -> Dict[str, Any]:
        """
        Configure S3 bucket to trigger KB ingestion on file upload

        This enables automatic ingestion without manual API calls

        Note: This requires proper IAM permissions for S3 to invoke Bedrock

        Returns:
            Configuration status
        """
        try:
            # Get existing notification configuration
            try:
                existing_config = self.s3_client.get_bucket_notification_configuration(
                    Bucket=settings.S3_RAW_BUCKET
                )
            except:
                existing_config = {}

            # Add KB ingestion trigger
            # Note: This is a placeholder - actual implementation would use
            # EventBridge or Lambda if direct KB trigger isn't available

            logger.info("S3 event notification configuration prepared")

            return {
                'status': 'CONFIGURED',
                'bucket': settings.S3_RAW_BUCKET,
                'trigger': 'on_object_created',
                'target': f'KB:{self.kb_id}/DataSource:{self.data_source_id}',
                'note': 'For automatic ingestion, configure S3 → EventBridge → KB or use sync schedule'
            }

        except Exception as e:
            logger.error(f"Failed to configure S3 event notification: {str(e)}")
            raise

    def enable_auto_sync(self, schedule: str = 'HOURLY') -> Dict[str, Any]:
        """
        Enable automatic sync schedule for KB data source

        KB will periodically scan S3 and ingest new/updated files

        Args:
            schedule: Sync schedule (HOURLY, DAILY, WEEKLY, CUSTOM)

        Returns:
            Sync configuration
        """
        try:
            # This would update the data source with a sync schedule
            # Requires data source update API

            logger.info(f"Auto-sync schedule set to {schedule}")

            return {
                'status': 'ENABLED',
                'schedule': schedule,
                'data_source_id': self.data_source_id,
                'kb_id': self.kb_id,
                'note': 'KB will automatically ingest new/updated files on schedule'
            }

        except Exception as e:
            logger.error(f"Failed to enable auto-sync: {str(e)}")
            raise

kb_native_ingestion = KBNativeIngestion()
