"""
Knowledge Base Query Service - Hybrid search + retrieve-and-generate
using Bedrock Knowledge Base with Claude Sonnet 4.5.

Search type : HYBRID  (vector similarity + keyword BM25)
Chunks      : 10 (configurable via KB_NUM_RESULTS)
Generation  : anthropic.claude-sonnet-4-5
Languages   : English, Sinhala (si), Tamil (ta)
"""

import boto3
from typing import Dict, Any, Optional, List
from config import settings
from utils.logger import get_logger
from .translation_service import translation_service, SUPPORTED_LANGUAGES

logger = get_logger(__name__)


class KBQueryService:
    """Hybrid-search retrieve-and-generate against Bedrock Knowledge Base."""

    def __init__(self):
        aws_credentials = {
            'region_name': settings.AWS_REGION,
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        }
        if settings.AWS_SESSION_TOKEN:
            aws_credentials['aws_session_token'] = settings.AWS_SESSION_TOKEN

        self.bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', **aws_credentials)
        self.kb_id = settings.BEDROCK_KB_ID
        self.model_arn = settings.BEDROCK_GENERATION_MODEL_ARN
        self.num_results = settings.KB_NUM_RESULTS  # 10 chunks

    # ------------------------------------------------------------------
    # Primary method — called by /api/retrieve
    # ------------------------------------------------------------------

    def query(
        self,
        query: str,
        user_id: Optional[str] = None,
        team_id: Optional[str] = None,
        max_results: int = None,        # falls back to settings.KB_NUM_RESULTS
    ) -> Dict[str, Any]:
        """
        Hybrid search + LLM summarisation flow:

        1. Detect query language (English / Sinhala / Tamil)
        2. Translate query to English when needed
        3. Hybrid retrieval (vector + keyword) — 10 chunks
        4. Claude Sonnet 4.5 generates a summarised answer with citations
        5. Translate the generated answer back to the original language
        """
        num_chunks = max_results or self.num_results

        try:
            # ── 1. Language detection ────────────────────────────────────
            detected_lang = translation_service.detect_language(query)
            logger.info(f"Query language detected: {detected_lang}")

            # ── 2. Translate to English for retrieval ────────────────────
            english_query = query
            if not translation_service.is_english(detected_lang):
                english_query = translation_service.to_english(query, detected_lang)
                logger.info(f"Translated query → English: {english_query}")

            # ── 3. Build retrieval config (HYBRID, optional filter) ───────
            retrieval_config = self._build_retrieval_config(
                num_chunks=num_chunks,
                user_id=user_id,
                team_id=team_id,
            )

            # ── 4. retrieve_and_generate with Claude Sonnet 4.5 ──────────
            logger.info(
                f"retrieve_and_generate — model: {self.model_arn}, "
                f"search: HYBRID, chunks: {num_chunks}"
            )

            response = self.bedrock_agent_runtime.retrieve_and_generate(
                input={'text': english_query},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.kb_id,
                        'modelArn': self.model_arn,
                        'retrievalConfiguration': retrieval_config,
                        'generationConfiguration': {
                            'promptTemplate': {
                                'textPromptTemplate': (
                                    'You are a knowledge base assistant. Your ONLY job is to answer questions using EXCLUSIVELY the information provided in the search results below.\n\n'
                                    'CRITICAL RULES:\n'
                                    '1. ONLY use information from the search results below - DO NOT use your general knowledge\n'
                                    '2. If the search results DO NOT contain the answer, you MUST respond EXACTLY with: "I cannot find this information in the available documents."\n'
                                    '3. DO NOT make assumptions or infer information not explicitly stated in the search results\n'
                                    '4. DO NOT provide general knowledge answers - ONLY answer from the search results\n'
                                    '5. If the search results are empty or irrelevant, say you cannot find the information\n\n'
                                    'Formatting rules (when answering from search results):\n'
                                    '- Use numbered lists (1. 2. 3.) for sequential steps\n'
                                    '- Use bullet points (-) for non-sequential items\n'
                                    '- Use **bold** for important terms\n'
                                    '- Be concise and direct\n\n'
                                    'Search Results:\n'
                                    '$search_results$\n\n'
                                    'Question: $query$\n\n'
                                    'Answer (ONLY from search results above):'
                                )
                            },
                        },
                    },
                },
            )

            # ── 5. Parse response ─────────────────────────────────────────
            english_answer = response.get('output', {}).get('text', '')
            raw_citations = response.get('citations', [])
            logger.debug(f"Raw citations from Bedrock: {raw_citations}")
            citations = self._parse_citations(raw_citations)
            session_id = response.get('sessionId')

            logger.info(
                f"Generated answer ({len(english_answer)} chars), "
                f"{len(citations)} cited chunks"
            )

            # ── 6. Translate answer back to original language ─────────────
            # Use markdown-aware translation so **bold**, ## headings, and
            # - bullets survive the trip through Amazon Translate intact.
            answer = english_answer
            if not translation_service.is_english(detected_lang) and english_answer:
                answer = translation_service.from_english_markdown(english_answer, detected_lang)

            return {
                'answer': answer,
                'answer_english': english_answer,
                'citations': citations,
                'results_count': len(citations),
                # keep a flat `results` list so the frontend ResultCard still works
                'results': citations,
                'session_id': session_id,
                'language': {
                    'detected': detected_lang,
                    'name': SUPPORTED_LANGUAGES.get(detected_lang, 'Unknown'),
                    'query_translated': not translation_service.is_english(detected_lang),
                    'english_query': english_query,
                },
                'retrieval': {
                    'search_type': 'HYBRID',
                    'chunks_requested': num_chunks,
                    'chunks_returned': len(citations),
                    'model': self.model_arn,
                },
            }

        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_retrieval_config(
        self,
        num_chunks: int,
        user_id: Optional[str],
        team_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build the retrievalConfiguration block.
        Uses HYBRID search (vector + keyword BM25).
        Adds a metadata filter only when user_id is supplied.
        """
        vector_search_config: Dict[str, Any] = {
            'numberOfResults': num_chunks,
            'overrideSearchType': 'HYBRID',   # vector + keyword
        }

        if user_id:
            if team_id:
                vector_search_config['filter'] = {
                    'orAll': [
                        {'equals': {'key': 'user_id', 'value': user_id}},
                        {'equals': {'key': 'team_id', 'value': team_id}},
                    ]
                }
            else:
                vector_search_config['filter'] = {
                    'equals': {'key': 'user_id', 'value': user_id}
                }

        return {'vectorSearchConfiguration': vector_search_config}

    def _parse_citations(self, raw_citations: list) -> List[Dict[str, Any]]:
        """
        Flatten the Bedrock retrieve_and_generate citation structure.

        The response shape is:
          citations: [
            {
              generatedResponsePart: { textResponsePart: { text, span } },
              retrievedReferences: [
                {
                  content: { text },
                  location: { s3Location: { uri } },
                  metadata: { ... }
                }
              ]
            }
          ]

        We deduplicate by S3 URI so the same source file isn't listed twice.
        """
        seen_uris: set = set()
        chunks = []

        # Debug: Log the structure we're receiving
        logger.debug(f"DEBUG: Processing {len(raw_citations)} citation blocks")
        for i, citation in enumerate(raw_citations):
            logger.debug(f"DEBUG: Citation {i} keys: {citation.keys()}")
            logger.debug(f"DEBUG: Citation {i} full structure: {citation}")

        for citation in raw_citations:
            for ref in citation.get('retrievedReferences', []):
                content_text = ref.get('content', {}).get('text', '')
                location = ref.get('location', {})
                metadata = ref.get('metadata', {})

                s3_uri = (
                    location.get('s3Location', {}).get('uri')
                    or metadata.get('x-amz-bedrock-kb-source-uri', '')
                )

                # Skip duplicates
                if s3_uri and s3_uri in seen_uris:
                    continue
                if s3_uri:
                    seen_uris.add(s3_uri)

                chunks.append({
                    'content': {'text': content_text},
                    'score': ref.get('score', 0),
                    'location': location,
                    'metadata': metadata,
                    's3_uri': s3_uri,
                    'source_file': s3_uri.split('/')[-1] if s3_uri else '',
                })

        logger.info(f"Parsed {len(chunks)} unique cited chunks from {len(raw_citations)} citation blocks")
        return chunks


# Singleton instance
kb_query_service = KBQueryService()
