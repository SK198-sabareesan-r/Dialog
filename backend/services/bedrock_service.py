import json
from typing import Dict, Any, List
from .aws_client import aws_clients
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class BedrockService:
    """Service for Bedrock Data Automation and Knowledge Base operations"""

    def __init__(self):
        self.bedrock_client = aws_clients.get_bedrock_client()
        self.bedrock_agent_client = aws_clients.get_bedrock_agent_client()
        self.kb_id = settings.BEDROCK_KB_ID
        self.embedding_model = settings.BEDROCK_EMBEDDING_MODEL

    def invoke_data_automation(
        self,
        s3_input_uri: str,
        s3_output_uri: str,
        document_type: str = "MULTIMODAL"
    ) -> Dict[str, Any]:
        """
        Invoke Bedrock Data Automation to parse multimodal content

        Args:
            s3_input_uri: S3 URI of input file
            s3_output_uri: S3 URI for output
            document_type: Type of document (MULTIMODAL, TEXT, IMAGE, etc.)

        Returns:
            Job details including job ID and status
        """
        try:
            response = self.bedrock_client.start_data_automation_job(
                dataAutomationProjectArn=settings.BEDROCK_DATA_AUTOMATION_JOB_ARN,
                inputConfiguration={
                    's3Uri': s3_input_uri
                },
                outputConfiguration={
                    's3Uri': s3_output_uri
                },
                dataAutomationType=document_type
            )

            job_id = response['jobArn']
            logger.info(f"Started BDA job: {job_id}")

            return {
                'job_id': job_id,
                'status': 'STARTED',
                'input_uri': s3_input_uri,
                'output_uri': s3_output_uri
            }

        except Exception as e:
            logger.error(f"Failed to start BDA job: {str(e)}")
            raise

    def get_job_status(self, job_arn: str) -> Dict[str, Any]:
        """Get status of BDA job"""
        try:
            response = self.bedrock_client.get_data_automation_job(
                jobIdentifier=job_arn
            )

            return {
                'job_id': job_arn,
                'status': response['status'],
                'created_at': response.get('creationTime'),
                'completed_at': response.get('completionTime'),
                'error': response.get('failureReason')
            }

        except Exception as e:
            logger.error(f"Failed to get job status: {str(e)}")
            raise

    def ingest_to_knowledge_base(
        self,
        data_source_id: str,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Ingest documents to Bedrock Knowledge Base

        Args:
            data_source_id: Data source ID in the knowledge base
            documents: List of document metadata

        Returns:
            Ingestion job details
        """
        try:
            response = self.bedrock_agent_client.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=data_source_id
            )

            ingestion_job_id = response['ingestionJob']['ingestionJobId']
            logger.info(f"Started KB ingestion job: {ingestion_job_id}")

            return {
                'ingestion_job_id': ingestion_job_id,
                'status': response['ingestionJob']['status'],
                'knowledge_base_id': self.kb_id
            }

        except Exception as e:
            logger.error(f"Failed to start KB ingestion: {str(e)}")
            raise

    def get_ingestion_status(
        self,
        data_source_id: str,
        ingestion_job_id: str
    ) -> Dict[str, Any]:
        """Get status of knowledge base ingestion job"""
        try:
            response = self.bedrock_agent_client.get_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=data_source_id,
                ingestionJobId=ingestion_job_id
            )

            job = response['ingestionJob']
            return {
                'ingestion_job_id': ingestion_job_id,
                'status': job['status'],
                'started_at': job.get('startedAt'),
                'completed_at': job.get('completedAt'),
                'statistics': job.get('statistics', {})
            }

        except Exception as e:
            logger.error(f"Failed to get ingestion status: {str(e)}")
            raise

    def retrieve_documents(
        self,
        query: str,
        max_results: int = 10,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents from knowledge base with IAM-based filtering

        Args:
            query: Search query
            max_results: Maximum number of results
            filter_metadata: Metadata filters for access control

        Returns:
            List of retrieved documents
        """
        try:
            retrieve_config = {
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results
                }
            }

            if filter_metadata:
                retrieve_config['vectorSearchConfiguration']['filter'] = filter_metadata

            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={'text': query},
                retrievalConfiguration=retrieve_config
            )

            results = response.get('retrievalResults', [])
            logger.info(f"Retrieved {len(results)} documents for query: {query}")

            return results

        except Exception as e:
            logger.error(f"Failed to retrieve documents: {str(e)}")
            raise

bedrock_service = BedrockService()
