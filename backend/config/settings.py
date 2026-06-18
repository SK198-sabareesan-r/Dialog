"""
Simplified Settings Configuration
Only includes what's needed for Bedrock KB native integration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings:
    """Application settings - simplified for Bedrock KB native integration"""

    # AWS Configuration (REQUIRED)
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_SESSION_TOKEN = os.getenv('AWS_SESSION_TOKEN')  # For SSO temporary credentials

    # S3 Storage (REQUIRED)
    S3_RAW_BUCKET = os.getenv('S3_RAW_BUCKET')

    # Bedrock Knowledge Base Configuration (REQUIRED)
    BEDROCK_KB_ID = os.getenv('BEDROCK_KB_ID')
    BEDROCK_DATA_SOURCE_ID = os.getenv('BEDROCK_DATA_SOURCE_ID')
    BEDROCK_EMBEDDING_MODEL = os.getenv('BEDROCK_EMBEDDING_MODEL', 'amazon.titan-embed-text-v1')

    # Bedrock generation model for retrieve-and-generate
    # Claude Sonnet 4.5 via global inference profile
    BEDROCK_GENERATION_MODEL_ARN = os.getenv(
        'BEDROCK_GENERATION_MODEL_ARN',
        'global.anthropic.claude-sonnet-4-5-20250929-v1:0'
    )

    # Retrieval settings
    KB_NUM_RESULTS = int(os.getenv('KB_NUM_RESULTS', '10'))   # chunks to retrieve

    # Google Drive Integration (OPTIONAL)
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

    # PostgreSQL RDS (for chat sessions)
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@database-dialogbox.c9cu4cy0u7rk.ap-south-1.rds.amazonaws.com:5432/postgres')

    # JWT Configuration (for session management)
    JWT_SECRET = os.getenv('JWT_SECRET', 'dialog-bda-pipeline-secret-change-in-production')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_EXPIRE_HOURS = int(os.getenv('JWT_EXPIRE_HOURS', '8'))

    # Database (RDS PostgreSQL)
    DATABASE_URL = os.getenv('DATABASE_URL')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

    # Encryption key for sync credentials (Fernet key — run once to generate:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '')

    @classmethod
    def validate(cls):
        """Validate that all required settings are present"""
        required_fields = [
            'AWS_REGION',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'S3_RAW_BUCKET',
            'BEDROCK_KB_ID',
            'BEDROCK_DATA_SOURCE_ID',
        ]

        missing = [field for field in required_fields if not getattr(cls, field)]
        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}\n"
                f"Please update your .env file with these values."
            )

        return True

    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("=" * 80)
        print("Current Configuration:")
        print("=" * 80)
        print(f"AWS Region: {cls.AWS_REGION}")
        print(f"S3 Bucket: {cls.S3_RAW_BUCKET}")
        print(f"Bedrock KB ID: {cls.BEDROCK_KB_ID}")
        print(f"Data Source ID: {cls.BEDROCK_DATA_SOURCE_ID}")
        print(f"Embedding Model: {cls.BEDROCK_EMBEDDING_MODEL}")
        print(f"Google Drive Enabled: {'Yes' if cls.GOOGLE_CLIENT_ID else 'No'}")
        print("=" * 80)

settings = Settings()
