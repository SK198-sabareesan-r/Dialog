import json
from datetime import datetime
from typing import Dict, Any, Optional
from services import (
    s3_service,
    bedrock_service,
    opensearch_service,
    stepfunctions_service,
    sqs_service,
    monitoring_service
)
from services.format_processor import format_processor
from services.format_detector import format_detector
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class PipelineOrchestrator:
    """Main orchestrator for the ingestion pipeline"""

    def __init__(self):
        self.max_retries = settings.MAX_RETRY_ATTEMPTS

    def start_ingestion(
        self,
        source_key: str,
        source_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start the ingestion pipeline for a file in S3 raw zone

        Args:
            source_key: S3 key in raw bucket
            source_type: Type of source (web_ui, shared_drive, file_repo, s3_direct)
            metadata: Additional metadata

        Returns:
            Execution details
        """
        start_time = datetime.utcnow()

        input_data = {
            'source_key': source_key,
            'source_type': source_type,
            'metadata': metadata or {},
            'timestamp': start_time.isoformat(),
            'retry_count': 0
        }

        try:
            execution = stepfunctions_service.start_execution(
                input_data=input_data,
                execution_name=f"{source_type}-{start_time.strftime('%Y%m%d%H%M%S')}"
            )

            monitoring_service.log_ingestion_success(source_type)
            logger.info(f"Started ingestion pipeline: {execution['execution_arn']}")

            return execution

        except Exception as e:
            monitoring_service.log_ingestion_failure(source_type, type(e).__name__)
            logger.error(f"Failed to start ingestion: {str(e)}")
            raise

    def process_file(
        self,
        source_key: str,
        filename: str,
        content_type: str,
        metadata: Dict[str, Any],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Process file with format-specific handler

        Args:
            source_key: S3 key in raw bucket
            filename: Original filename
            content_type: MIME type
            metadata: File metadata
            retry_count: Current retry attempt

        Returns:
            Processing result
        """
        start_time = datetime.utcnow()

        try:
            # Validate format first
            is_valid, message = format_detector.validate_format(filename, content_type)
            if not is_valid:
                raise ValueError(f"Format validation failed: {message}")

            logger.info(f"Format validation passed: {message}")

            # Process with appropriate handler
            result = format_processor.process_file(
                source_key=source_key,
                filename=filename,
                content_type=content_type,
                metadata=metadata
            )

            duration = (datetime.utcnow() - start_time).total_seconds()
            handler = result.get('handler', 'unknown')
            monitoring_service.log_processing_duration(handler, duration)

            return result

        except ValueError as e:
            # Format validation error - don't retry
            logger.error(f"Format validation failed: {str(e)}")
            return self.handle_dlq(source_key, retry_count, e)

        except Exception as e:
            logger.error(f"File processing failed: {str(e)}")

            if retry_count < self.max_retries:
                return self.handle_retry(source_key, retry_count, e)
            else:
                return self.handle_dlq(source_key, retry_count, e)

    def process_with_bda(
        self,
        source_key: str,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Legacy method - Process file with Bedrock Data Automation
        Use process_file() instead for format-aware processing

        Args:
            source_key: S3 key in raw bucket
            retry_count: Current retry attempt

        Returns:
            Job details
        """
        start_time = datetime.utcnow()
        s3_input_uri = f"s3://{settings.S3_RAW_BUCKET}/{source_key}"
        s3_output_uri = f"s3://{settings.S3_PROCESSED_BUCKET}/bda-output/{source_key}"

        try:
            job = bedrock_service.invoke_data_automation(
                s3_input_uri=s3_input_uri,
                s3_output_uri=s3_output_uri
            )

            duration = (datetime.utcnow() - start_time).total_seconds()
            monitoring_service.log_processing_duration('BDA', duration)

            return job

        except Exception as e:
            logger.error(f"BDA processing failed: {str(e)}")

            if retry_count < self.max_retries:
                return self.handle_retry(source_key, retry_count, e)
            else:
                return self.handle_dlq(source_key, retry_count, e)

    def handle_retry(
        self,
        source_key: str,
        retry_count: int,
        error: Exception
    ) -> Dict[str, Any]:
        """Handle retry logic"""
        retry_count += 1
        delay_seconds = min(2 ** retry_count * 60, 900)

        retry_message = {
            'source_key': source_key,
            'retry_count': retry_count,
            'error': str(error),
            'timestamp': datetime.utcnow().isoformat()
        }

        message_id = sqs_service.send_to_retry_queue(
            retry_message,
            delay_seconds=delay_seconds
        )

        logger.info(f"Scheduled retry {retry_count}/{self.max_retries} in {delay_seconds}s")

        return {
            'status': 'RETRY_SCHEDULED',
            'retry_count': retry_count,
            'message_id': message_id,
            'delay_seconds': delay_seconds
        }

    def handle_dlq(
        self,
        source_key: str,
        retry_count: int,
        error: Exception
    ) -> Dict[str, Any]:
        """Handle dead-letter queue after retry exhaustion"""
        error_details = {
            'error': str(error),
            'error_type': type(error).__name__,
            'timestamp': datetime.utcnow().isoformat()
        }

        message_body = {
            'source_key': source_key,
            'retry_count': retry_count
        }

        message_id = sqs_service.send_to_dlq(message_body, error_details)

        monitoring_service.send_alarm(
            subject=f"Ingestion Failed: {source_key}",
            message=f"File {source_key} failed after {retry_count} retries. Error: {str(error)}",
            severity='ERROR'
        )

        monitoring_service.check_dlq_threshold()

        return {
            'status': 'FAILED',
            'retry_count': retry_count,
            'dlq_message_id': message_id,
            'error': error_details
        }

    def ingest_to_kb_and_opensearch(
        self,
        processed_key: str,
        data_source_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ingest processed output to Knowledge Base and OpenSearch

        Args:
            processed_key: S3 key in processed bucket
            data_source_id: Knowledge base data source ID
            metadata: Document metadata including access control

        Returns:
            Ingestion results
        """
        start_time = datetime.utcnow()

        try:
            kb_job = bedrock_service.ingest_to_knowledge_base(
                data_source_id=data_source_id,
                documents=[{'s3_key': processed_key, 'metadata': metadata}]
            )

            duration = (datetime.utcnow() - start_time).total_seconds()
            monitoring_service.log_processing_duration('KnowledgeBase', duration)

            logger.info(f"Successfully ingested to KB: {kb_job['ingestion_job_id']}")

            return {
                'status': 'SUCCESS',
                'kb_job': kb_job,
                'processed_key': processed_key
            }

        except Exception as e:
            logger.error(f"Failed to ingest to KB/OpenSearch: {str(e)}")
            raise

    def retrieve_with_access_control(
        self,
        query: str,
        user_id: str,
        team_id: str = None,
        max_results: int = 10
    ) -> list:
        """
        Retrieve documents with IAM + metadata-based access control

        Args:
            query: Search query
            user_id: User identifier for access control
            team_id: Optional team identifier
            max_results: Maximum results to return

        Returns:
            Filtered results
        """
        filter_metadata = {
            'user_id': user_id
        }

        if team_id:
            filter_metadata['team_id'] = team_id

        try:
            results = bedrock_service.retrieve_documents(
                query=query,
                max_results=max_results,
                filter_metadata=filter_metadata
            )

            logger.info(f"Retrieved {len(results)} documents for user {user_id}")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve documents: {str(e)}")
            raise

orchestrator = PipelineOrchestrator()
