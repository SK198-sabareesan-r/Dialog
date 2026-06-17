import boto3
from typing import Optional
from config import settings


class AWSClientManager:
    """Centralized AWS client management — only services actively used."""

    _s3_client: Optional[boto3.client] = None
    _bedrock_agent_client: Optional[boto3.client] = None
    _bedrock_agent_runtime_client: Optional[boto3.client] = None
    _translate_client: Optional[boto3.client] = None
    _comprehend_client: Optional[boto3.client] = None

    @classmethod
    def get_boto3_session(cls):
        """Get configured boto3 session."""
        session_kwargs = {
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
            'region_name': settings.AWS_REGION,
        }
        if settings.AWS_SESSION_TOKEN:
            session_kwargs['aws_session_token'] = settings.AWS_SESSION_TOKEN
        return boto3.Session(**session_kwargs)

    @classmethod
    def get_s3_client(cls):
        """S3 — file storage."""
        if cls._s3_client is None:
            cls._s3_client = cls.get_boto3_session().client('s3')
        return cls._s3_client

    @classmethod
    def get_bedrock_agent_client(cls):
        """Bedrock Agent — start_ingestion_job, KB management."""
        if cls._bedrock_agent_client is None:
            cls._bedrock_agent_client = cls.get_boto3_session().client('bedrock-agent')
        return cls._bedrock_agent_client

    @classmethod
    def get_bedrock_agent_runtime_client(cls):
        """Bedrock Agent Runtime — retrieve_and_generate, retrieve."""
        if cls._bedrock_agent_runtime_client is None:
            cls._bedrock_agent_runtime_client = cls.get_boto3_session().client('bedrock-agent-runtime')
        return cls._bedrock_agent_runtime_client

    @classmethod
    def get_translate_client(cls):
        """Amazon Translate — multilingual query support."""
        if cls._translate_client is None:
            cls._translate_client = cls.get_boto3_session().client('translate')
        return cls._translate_client

    @classmethod
    def get_comprehend_client(cls):
        """Amazon Comprehend — language detection."""
        if cls._comprehend_client is None:
            cls._comprehend_client = cls.get_boto3_session().client('comprehend')
        return cls._comprehend_client


aws_clients = AWSClientManager()
