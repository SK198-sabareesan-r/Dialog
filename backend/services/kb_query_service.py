"""
Knowledge Base Query Service - Query Bedrock KB with metadata filtering
and automatic multilingual support (English, Sinhala, Tamil).
"""

import boto3
from typing import Dict, Any, Optional, List
from config import settings
from utils.logger import get_logger
from .translation_service import translation_service, SUPPORTED_LANGUAGES

logger = get_logger(__name__)

class KBQueryService:
    """Service for querying Bedrock Knowledge Base"""

    def __init__(self):
        # Build AWS credentials dict (supports SSO session tokens)
        aws_credentials = {
            'region_name': settings.AWS_REGION,
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY
        }

        # Add session token if present (for SSO/temporary credentials)
        if settings.AWS_SESSION_TOKEN:
            aws_credentials['aws_session_token'] = settings.AWS_SESSION_TOKEN

        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', **aws_credentials)
        self.kb_id = settings.BEDROCK_KB_ID

    def query(
        self,
        query: str,
        user_id: str,
        team_id: Optional[str] = None,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Query knowledge base with metadata filtering and multilingual support.

        Flow:
        1. Detect language of the query
        2. Translate query to English if needed
        3. Search Bedrock KB in English
        4. Translate results back to the original language
        5. Return results with language metadata

        Applies access control based on user_id and team_id.
        """
        try:
            # Step 1: Detect query language
            detected_lang = translation_service.detect_language(query)
            logger.info(f"Query language detected: {detected_lang}")

            # Step 2: Translate query to English for KB search
            english_query = query
            if not translation_service.is_english(detected_lang):
                english_query = translation_service.to_english(query, detected_lang)
                logger.info(f"Translated query to English: {english_query}")

            # Step 3: Build metadata filter
            metadata_filter = {
                'equals': {
                    'key': 'user_id',
                    'value': user_id
                }
            }

            if team_id:
                metadata_filter = {
                    'orAll': [
                        {
                            'equals': {
                                'key': 'user_id',
                                'value': user_id
                            }
                        },
                        {
                            'equals': {
                                'key': 'team_id',
                                'value': team_id
                            }
                        }
                    ]
                }

            logger.info(f"Querying KB with filter: {metadata_filter}")

            # Step 4: Query Bedrock KB in English
            response = self.bedrock_agent_runtime.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={'text': english_query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results,
                        'filter': metadata_filter
                    }
                }
            )

            results = response.get('retrievalResults', [])
            logger.info(f"Retrieved {len(results)} results for query: '{english_query}'")

            # Step 5: Format and translate results back to original language
            formatted_results = []
            for result in results:
                english_content = result.get('content', {}).get('text', '')

                # Translate content back to user's language if needed
                if not translation_service.is_english(detected_lang) and english_content:
                    translated_content = translation_service.from_english(
                        english_content, detected_lang
                    )
                else:
                    translated_content = english_content

                formatted_results.append({
                    'content': translated_content,
                    'content_english': english_content,  # keep original for reference
                    'score': result.get('score', 0),
                    'location': result.get('location', {}),
                    'metadata': result.get('metadata', {})
                })

            return {
                'results': formatted_results,
                'language': {
                    'detected': detected_lang,
                    'name': SUPPORTED_LANGUAGES.get(detected_lang, 'Unknown'),
                    'query_translated': not translation_service.is_english(detected_lang),
                    'english_query': english_query,
                }
            }

        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            raise

    def retrieve_and_generate(
        self,
        query: str,
        user_id: str,
        team_id: Optional[str] = None,
        model_arn: str = None
    ) -> Dict[str, Any]:
        """
        Retrieve documents and generate answer using LLM

        This is a higher-level API that retrieves relevant documents
        and uses Claude to generate an answer with citations.
        """
        try:
            # Default to Claude 3 Sonnet
            if not model_arn:
                model_arn = 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'

            # Build metadata filter
            metadata_filter = {
                'equals': {
                    'key': 'user_id',
                    'value': user_id
                }
            }

            if team_id:
                metadata_filter = {
                    'orAll': [
                        {
                            'equals': {
                                'key': 'user_id',
                                'value': user_id
                            }
                        },
                        {
                            'equals': {
                                'key': 'team_id',
                                'value': team_id
                            }
                        }
                    ]
                }

            logger.info(f"Retrieve and generate for query: '{query}'")

            # Call retrieve_and_generate API
            response = self.bedrock_agent_runtime.retrieve_and_generate(
                input={'text': query},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.kb_id,
                        'modelArn': model_arn,
                        'retrievalConfiguration': {
                            'vectorSearchConfiguration': {
                                'numberOfResults': 5,
                                'filter': metadata_filter
                            }
                        }
                    }
                }
            )

            # Extract answer and citations
            output = response.get('output', {}).get('text', '')
            citations = response.get('citations', [])

            logger.info(f"Generated answer with {len(citations)} citations")

            return {
                'answer': output,
                'citations': citations,
                'session_id': response.get('sessionId')
            }

        except Exception as e:
            logger.error(f"Retrieve and generate failed: {str(e)}")
            raise

# Singleton instance
kb_query_service = KBQueryService()
