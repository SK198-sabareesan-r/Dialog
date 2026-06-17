import json
from typing import Dict, Any, List
from .aws_client import aws_clients
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class TextractService:
    """Service for Amazon Textract - OCR and document analysis"""

    def __init__(self):
        self.textract_client = aws_clients.get_textract_client()

    def analyze_document(
        self,
        s3_bucket: str,
        s3_key: str,
        features: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze document/image using Textract

        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 key
            features: Analysis features (TABLES, FORMS, LAYOUT)

        Returns:
            Extracted text and metadata
        """
        if features is None:
            features = ['TABLES', 'FORMS', 'LAYOUT']

        try:
            logger.info(f"Starting Textract analysis for s3://{s3_bucket}/{s3_key}")

            response = self.textract_client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': s3_bucket,
                        'Name': s3_key
                    }
                },
                FeatureTypes=features
            )

            job_id = response['JobId']
            logger.info(f"Started Textract job: {job_id}")

            return {
                'job_id': job_id,
                'status': 'IN_PROGRESS',
                'service': 'textract'
            }

        except Exception as e:
            logger.error(f"Failed to start Textract analysis: {str(e)}")
            raise

    def detect_text(
        self,
        s3_bucket: str,
        s3_key: str
    ) -> Dict[str, Any]:
        """
        Simple text detection (synchronous) for single-page documents/images

        Args:
            s3_bucket: S3 bucket name
            s3_key: S3 key

        Returns:
            Detected text and confidence scores
        """
        try:
            logger.info(f"Detecting text in s3://{s3_bucket}/{s3_key}")

            response = self.textract_client.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': s3_bucket,
                        'Name': s3_key
                    }
                }
            )

            # Extract text blocks
            text_blocks = []
            full_text = []

            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_blocks.append({
                        'text': block.get('Text', ''),
                        'confidence': block.get('Confidence', 0),
                        'geometry': block.get('Geometry', {})
                    })
                    full_text.append(block.get('Text', ''))

            extracted_text = '\n'.join(full_text)

            logger.info(f"Extracted {len(text_blocks)} text blocks")

            return {
                'text': extracted_text,
                'blocks': text_blocks,
                'page_count': 1,
                'service': 'textract',
                'method': 'detect_text'
            }

        except Exception as e:
            logger.error(f"Failed to detect text: {str(e)}")
            raise

    def get_analysis_results(self, job_id: str) -> Dict[str, Any]:
        """
        Get results from an asynchronous Textract job

        Args:
            job_id: Textract job ID

        Returns:
            Analysis results including text, tables, and forms
        """
        try:
            response = self.textract_client.get_document_analysis(
                JobId=job_id
            )

            status = response['JobStatus']

            if status == 'SUCCEEDED':
                # Extract all text
                text_blocks = []
                tables = []
                forms = []

                for block in response.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        text_blocks.append(block.get('Text', ''))
                    elif block['BlockType'] == 'TABLE':
                        tables.append(self._parse_table(block, response['Blocks']))
                    elif block['BlockType'] == 'KEY_VALUE_SET':
                        forms.append(self._parse_form(block, response['Blocks']))

                return {
                    'status': 'SUCCEEDED',
                    'text': '\n'.join(text_blocks),
                    'tables': tables,
                    'forms': forms,
                    'page_count': response.get('DocumentMetadata', {}).get('Pages', 1)
                }
            elif status == 'FAILED':
                return {
                    'status': 'FAILED',
                    'error': response.get('StatusMessage', 'Unknown error')
                }
            else:
                return {
                    'status': status,
                    'job_id': job_id
                }

        except Exception as e:
            logger.error(f"Failed to get Textract results: {str(e)}")
            raise

    def _parse_table(self, table_block: Dict, all_blocks: List[Dict]) -> Dict:
        """Parse table structure from Textract blocks"""
        # Simplified table parsing
        return {
            'confidence': table_block.get('Confidence', 0),
            'row_count': table_block.get('RowCount', 0),
            'column_count': table_block.get('ColumnCount', 0)
        }

    def _parse_form(self, form_block: Dict, all_blocks: List[Dict]) -> Dict:
        """Parse form key-value pairs from Textract blocks"""
        # Simplified form parsing
        return {
            'type': form_block.get('EntityTypes', []),
            'confidence': form_block.get('Confidence', 0)
        }

textract_service = TextractService()
