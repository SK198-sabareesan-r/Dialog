import json
import time
from typing import Dict, Any, Optional
from .aws_client import aws_clients
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class TranscribeService:
    """Service for Amazon Transcribe - Audio/Video transcription"""

    def __init__(self):
        self.transcribe_client = aws_clients.get_transcribe_client()

    def start_transcription_job(
        self,
        s3_uri: str,
        job_name: str,
        media_format: str,
        language_code: str = 'en-US',
        output_bucket: str = None
    ) -> Dict[str, Any]:
        """
        Start transcription job for audio/video file

        Args:
            s3_uri: S3 URI (s3://bucket/key)
            job_name: Unique job name
            media_format: Format (mp4, mp3, wav, avi, etc.)
            language_code: Language code (en-US, si-LK for Sinhala, ta-IN for Tamil)
            output_bucket: S3 bucket for output

        Returns:
            Job details
        """
        try:
            logger.info(f"Starting transcription job: {job_name} for {s3_uri}")

            # Prepare job parameters
            job_params = {
                'TranscriptionJobName': job_name,
                'Media': {'MediaFileUri': s3_uri},
                'MediaFormat': self._normalize_media_format(media_format),
                'LanguageCode': language_code,
                'Settings': {
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': 10
                }
            }

            # Add output location if specified
            if output_bucket:
                job_params['OutputBucketName'] = output_bucket

            response = self.transcribe_client.start_transcription_job(**job_params)

            job_info = response['TranscriptionJob']

            logger.info(f"Transcription job started: {job_name}")

            return {
                'job_name': job_name,
                'status': job_info['TranscriptionJobStatus'],
                'language_code': language_code,
                'service': 'transcribe'
            }

        except Exception as e:
            logger.error(f"Failed to start transcription job: {str(e)}")
            raise

    def get_transcription_job_status(self, job_name: str) -> Dict[str, Any]:
        """
        Get status and results of transcription job

        Args:
            job_name: Transcription job name

        Returns:
            Job status and transcript if completed
        """
        try:
            response = self.transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )

            job = response['TranscriptionJob']
            status = job['TranscriptionJobStatus']

            result = {
                'job_name': job_name,
                'status': status,
                'language_code': job.get('LanguageCode'),
                'creation_time': job.get('CreationTime').isoformat() if job.get('CreationTime') else None
            }

            if status == 'COMPLETED':
                transcript_uri = job['Transcript']['TranscriptFileUri']
                result['transcript_uri'] = transcript_uri
                result['completion_time'] = job.get('CompletionTime').isoformat() if job.get('CompletionTime') else None

                # Optionally fetch and parse transcript
                # You would need to download from transcript_uri and parse JSON

            elif status == 'FAILED':
                result['failure_reason'] = job.get('FailureReason', 'Unknown error')

            return result

        except Exception as e:
            logger.error(f"Failed to get transcription job status: {str(e)}")
            raise

    def wait_for_completion(
        self,
        job_name: str,
        max_wait_seconds: int = 3600,
        poll_interval: int = 30
    ) -> Dict[str, Any]:
        """
        Wait for transcription job to complete

        Args:
            job_name: Job name
            max_wait_seconds: Maximum time to wait
            poll_interval: Seconds between status checks

        Returns:
            Final job status
        """
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            status = self.get_transcription_job_status(job_name)

            if status['status'] in ['COMPLETED', 'FAILED']:
                return status

            logger.info(f"Transcription job {job_name} status: {status['status']}, waiting...")
            time.sleep(poll_interval)

        raise TimeoutError(f"Transcription job {job_name} did not complete within {max_wait_seconds} seconds")

    def start_video_transcription(
        self,
        s3_uri: str,
        job_name: str,
        video_format: str,
        language_code: str = 'en-US',
        output_bucket: str = None
    ) -> Dict[str, Any]:
        """
        Start transcription for video file (extracts audio track)

        Args:
            s3_uri: S3 URI of video file
            job_name: Unique job name
            video_format: Video format (mp4, avi, mov, etc.)
            language_code: Language code
            output_bucket: Output bucket

        Returns:
            Job details
        """
        # For video files, Transcribe automatically extracts audio
        return self.start_transcription_job(
            s3_uri=s3_uri,
            job_name=job_name,
            media_format=video_format,
            language_code=language_code,
            output_bucket=output_bucket
        )

    def _normalize_media_format(self, format_str: str) -> str:
        """
        Normalize media format to Transcribe-accepted values

        Args:
            format_str: Input format (may include dot or be full mime type)

        Returns:
            Normalized format
        """
        # Remove leading dot if present
        format_str = format_str.lstrip('.')

        # Map common formats
        format_map = {
            'mp4': 'mp4',
            'mp3': 'mp3',
            'wav': 'wav',
            'flac': 'flac',
            'm4a': 'mp4',
            'avi': 'mp4',  # Transcribe treats video as mp4
            'mov': 'mp4',
            'mkv': 'mp4'
        }

        return format_map.get(format_str.lower(), 'mp4')

    def delete_transcription_job(self, job_name: str) -> bool:
        """Delete a transcription job"""
        try:
            self.transcribe_client.delete_transcription_job(
                TranscriptionJobName=job_name
            )
            logger.info(f"Deleted transcription job: {job_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete transcription job: {str(e)}")
            raise

transcribe_service = TranscribeService()
