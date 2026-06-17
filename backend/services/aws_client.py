import boto3
from typing import Optional
from config import settings

class AWSClientManager:
    """Centralized AWS client management"""

    _s3_client: Optional[boto3.client] = None
    _bedrock_client: Optional[boto3.client] = None
    _bedrock_agent_client: Optional[boto3.client] = None
    _stepfunctions_client: Optional[boto3.client] = None
    _sqs_client: Optional[boto3.client] = None
    _cloudwatch_client: Optional[boto3.client] = None
    _sns_client: Optional[boto3.client] = None
    _textract_client: Optional[boto3.client] = None
    _transcribe_client: Optional[boto3.client] = None

    @classmethod
    def get_boto3_session(cls):
        """Get configured boto3 session"""
        session_kwargs = {
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
            'region_name': settings.AWS_REGION,
        }
        # Include session token for SSO / temporary credentials
        if settings.AWS_SESSION_TOKEN:
            session_kwargs['aws_session_token'] = settings.AWS_SESSION_TOKEN
        return boto3.Session(**session_kwargs)

    @classmethod
    def get_s3_client(cls):
        """Get or create S3 client"""
        if cls._s3_client is None:
            session = cls.get_boto3_session()
            cls._s3_client = session.client('s3')
        return cls._s3_client

    @classmethod
    def get_bedrock_client(cls):
        """Get or create Bedrock client"""
        if cls._bedrock_client is None:
            session = cls.get_boto3_session()
            cls._bedrock_client = session.client('bedrock')
        return cls._bedrock_client

    @classmethod
    def get_bedrock_agent_client(cls):
        """Get or create Bedrock Agent client"""
        if cls._bedrock_agent_client is None:
            session = cls.get_boto3_session()
            cls._bedrock_agent_client = session.client('bedrock-agent')
        return cls._bedrock_agent_client

    @classmethod
    def get_stepfunctions_client(cls):
        """Get or create Step Functions client"""
        if cls._stepfunctions_client is None:
            session = cls.get_boto3_session()
            cls._stepfunctions_client = session.client('stepfunctions')
        return cls._stepfunctions_client

    @classmethod
    def get_sqs_client(cls):
        """Get or create SQS client"""
        if cls._sqs_client is None:
            session = cls.get_boto3_session()
            cls._sqs_client = session.client('sqs')
        return cls._sqs_client

    @classmethod
    def get_cloudwatch_client(cls):
        """Get or create CloudWatch client"""
        if cls._cloudwatch_client is None:
            session = cls.get_boto3_session()
            cls._cloudwatch_client = session.client('cloudwatch')
        return cls._cloudwatch_client

    @classmethod
    def get_sns_client(cls):
        """Get or create SNS client"""
        if cls._sns_client is None:
            session = cls.get_boto3_session()
            cls._sns_client = session.client('sns')
        return cls._sns_client

    @classmethod
    def get_textract_client(cls):
        """Get or create Textract client"""
        if cls._textract_client is None:
            session = cls.get_boto3_session()
            cls._textract_client = session.client('textract')
        return cls._textract_client

    @classmethod
    def get_transcribe_client(cls):
        """Get or create Transcribe client"""
        if cls._transcribe_client is None:
            session = cls.get_boto3_session()
            cls._transcribe_client = session.client('transcribe')
        return cls._transcribe_client

aws_clients = AWSClientManager()
