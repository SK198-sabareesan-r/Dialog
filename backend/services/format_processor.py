import json
from typing import Dict, Any
from datetime import datetime
from .format_detector import format_detector
from .textract_service import textract_service
from .transcribe_service import transcribe_service
from .excel_parser_service import excel_parser_service
from .bedrock_service import bedrock_service
from .s3_service import s3_service
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class FormatProcessor:
    """
    Orchestrates format-specific processing
    Routes files to appropriate handlers based on format
    """

    def __init__(self):
        self.format_detector = format_detector

    def process_file(
        self,
        source_key: str,
        filename: str,
        content_type: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process file with appropriate handler based on format

        Args:
            source_key: S3 key in raw bucket
            filename: Original filename
            content_type: MIME type
            metadata: File metadata

        Returns:
            Processing result with extracted content
        """
        try:
            # Detect and validate format
            format_info = self.format_detector.detect_format(filename, content_type)
            logger.info(f"Processing {filename} as {format_info['category']} using {format_info['handler']}")

            handler = format_info['handler']

            # Route to appropriate handler
            if handler == 'textract':
                return self._process_with_textract(source_key, filename, format_info, metadata)
            elif handler == 'transcribe':
                return self._process_with_transcribe(source_key, filename, format_info, metadata)
            elif handler == 'excel_parser':
                return self._process_with_excel_parser(source_key, filename, format_info, metadata)
            elif handler == 'bda':
                return self._process_with_bda(source_key, filename, format_info, metadata)
            else:
                raise ValueError(f"Unknown handler: {handler}")

        except Exception as e:
            logger.error(f"Failed to process file {filename}: {str(e)}")
            raise

    def _process_with_textract(
        self,
        source_key: str,
        filename: str,
        format_info: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process images with Amazon Textract"""
        logger.info(f"Processing image with Textract: {filename}")

        try:
            # For simple single-page images, use synchronous detection
            result = textract_service.detect_text(
                s3_bucket=settings.S3_RAW_BUCKET,
                s3_key=source_key
            )

            enriched_metadata = {
                **metadata,
                'processor': 'textract',
                'format': format_info['mime_type'],
                'category': format_info['category'],
                'processing_timestamp': datetime.utcnow().isoformat(),
                'text_blocks_count': len(result.get('blocks', [])),
                'page_count': result.get('page_count', 1)
            }

            return {
                'status': 'SUCCESS',
                'text': result['text'],
                'metadata': enriched_metadata,
                'raw_result': result,
                'handler': 'textract'
            }

        except Exception as e:
            logger.error(f"Textract processing failed: {str(e)}")
            raise

    def _process_with_transcribe(
        self,
        source_key: str,
        filename: str,
        format_info: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process audio/video with Amazon Transcribe"""
        logger.info(f"Processing audio/video with Transcribe: {filename}")

        try:
            s3_uri = f"s3://{settings.S3_RAW_BUCKET}/{source_key}"
            job_name = f"transcribe-{source_key.replace('/', '-')}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

            # Start transcription job
            if format_info['category'] == 'video':
                result = transcribe_service.start_video_transcription(
                    s3_uri=s3_uri,
                    job_name=job_name,
                    video_format=format_info['extension'],
                    language_code='en-US',
                    output_bucket=settings.S3_PROCESSED_BUCKET
                )
            else:
                result = transcribe_service.start_transcription_job(
                    s3_uri=s3_uri,
                    job_name=job_name,
                    media_format=format_info['extension'],
                    language_code='en-US',
                    output_bucket=settings.S3_PROCESSED_BUCKET
                )

            enriched_metadata = {
                **metadata,
                'processor': 'transcribe',
                'format': format_info['mime_type'],
                'category': format_info['category'],
                'processing_timestamp': datetime.utcnow().isoformat(),
                'transcribe_job_name': job_name,
                'language_code': result.get('language_code', 'en-US')
            }

            # Return async job info - Step Functions will poll for completion
            return {
                'status': 'IN_PROGRESS',
                'job_name': job_name,
                'job_type': 'transcribe',
                'metadata': enriched_metadata,
                'handler': 'transcribe',
                'requires_polling': True
            }

        except Exception as e:
            logger.error(f"Transcribe processing failed: {str(e)}")
            raise

    def _process_with_excel_parser(
        self,
        source_key: str,
        filename: str,
        format_info: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Excel/CSV files"""
        logger.info(f"Processing spreadsheet: {filename}")

        try:
            # Download file from S3
            file_content = s3_service.get_object(
                bucket=settings.S3_RAW_BUCKET,
                key=source_key
            )

            # Parse Excel
            result = excel_parser_service.parse_excel(
                file_content=file_content,
                filename=filename
            )

            # Extract additional metadata
            excel_metadata = excel_parser_service.extract_metadata(result)

            enriched_metadata = {
                **metadata,
                'processor': 'excel_parser',
                'format': format_info['mime_type'],
                'category': format_info['category'],
                'processing_timestamp': datetime.utcnow().isoformat(),
                **excel_metadata
            }

            return {
                'status': 'SUCCESS',
                'text': result['text'],
                'metadata': enriched_metadata,
                'raw_result': result,
                'handler': 'excel_parser'
            }

        except Exception as e:
            logger.error(f"Excel parsing failed: {str(e)}")
            raise

    def _process_with_bda(
        self,
        source_key: str,
        filename: str,
        format_info: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process documents with Bedrock Data Automation"""
        logger.info(f"Processing document with BDA: {filename}")

        try:
            s3_input_uri = f"s3://{settings.S3_RAW_BUCKET}/{source_key}"
            s3_output_uri = f"s3://{settings.S3_PROCESSED_BUCKET}/bda-output/{source_key}"

            result = bedrock_service.invoke_data_automation(
                s3_input_uri=s3_input_uri,
                s3_output_uri=s3_output_uri,
                document_type="MULTIMODAL"
            )

            enriched_metadata = {
                **metadata,
                'processor': 'bda',
                'format': format_info['mime_type'],
                'category': format_info['category'],
                'processing_timestamp': datetime.utcnow().isoformat(),
                'bda_job_id': result.get('job_id')
            }

            # Return async job info - Step Functions will poll for completion
            return {
                'status': 'IN_PROGRESS',
                'job_id': result.get('job_id'),
                'job_type': 'bda',
                'metadata': enriched_metadata,
                'handler': 'bda',
                'requires_polling': True
            }

        except Exception as e:
            logger.error(f"BDA processing failed: {str(e)}")
            raise

    def get_job_status(self, job_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get status of async processing job

        Args:
            job_info: Job information with job_type and job_id/job_name

        Returns:
            Current job status
        """
        job_type = job_info.get('job_type')

        try:
            if job_type == 'bda':
                return bedrock_service.get_job_status(job_info['job_id'])
            elif job_type == 'transcribe':
                return transcribe_service.get_transcription_job_status(job_info['job_name'])
            else:
                raise ValueError(f"Unknown job type: {job_type}")

        except Exception as e:
            logger.error(f"Failed to get job status: {str(e)}")
            raise

format_processor = FormatProcessor()
