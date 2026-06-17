from typing import Dict, Any, List
from opensearchpy import OpenSearch, RequestsHttpConnection
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

class OpenSearchService:
    """Service for OpenSearch vector store operations"""

    def __init__(self):
        self.endpoint = settings.OPENSEARCH_ENDPOINT
        self.index_name = settings.OPENSEARCH_INDEX

        host = self.endpoint.replace('https://', '').replace('http://', '')

        self.client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY),
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )

    def create_index(self, index_name: str = None) -> bool:
        """Create OpenSearch index with vector mapping"""
        index_name = index_name or self.index_name

        index_body = {
            'settings': {
                'index': {
                    'number_of_shards': 2,
                    'number_of_replicas': 1,
                    'knn': True,
                    'knn.algo_param.ef_search': 512
                }
            },
            'mappings': {
                'properties': {
                    'document_id': {'type': 'keyword'},
                    'content': {'type': 'text'},
                    'embedding': {
                        'type': 'knn_vector',
                        'dimension': 1536,
                        'method': {
                            'name': 'hnsw',
                            'space_type': 'cosinesimil',
                            'engine': 'nmslib'
                        }
                    },
                    'metadata': {
                        'properties': {
                            'source': {'type': 'keyword'},
                            'source_key': {'type': 'keyword'},
                            'timestamp': {'type': 'date'},
                            'user_id': {'type': 'keyword'},
                            'team_id': {'type': 'keyword'},
                            'access_level': {'type': 'keyword'}
                        }
                    }
                }
            }
        }

        try:
            if self.client.indices.exists(index=index_name):
                logger.info(f"Index {index_name} already exists")
                return True

            response = self.client.indices.create(index=index_name, body=index_body)
            logger.info(f"Created index {index_name}: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to create index: {str(e)}")
            raise

    def index_document(
        self,
        document_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> bool:
        """Index a document with its embedding"""
        document = {
            'document_id': document_id,
            'content': content,
            'embedding': embedding,
            'metadata': metadata
        }

        try:
            response = self.client.index(
                index=self.index_name,
                id=document_id,
                body=document
            )

            logger.info(f"Indexed document {document_id}: {response['result']}")
            return response['result'] in ['created', 'updated']

        except Exception as e:
            logger.error(f"Failed to index document: {str(e)}")
            raise

    def search_similar(
        self,
        query_embedding: List[float],
        k: int = 10,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        query_body = {
            'size': k,
            'query': {
                'bool': {
                    'must': [
                        {
                            'knn': {
                                'embedding': {
                                    'vector': query_embedding,
                                    'k': k
                                }
                            }
                        }
                    ]
                }
            }
        }

        if filter_metadata:
            filters = []
            for key, value in filter_metadata.items():
                filters.append({'term': {f'metadata.{key}': value}})
            query_body['query']['bool']['filter'] = filters

        try:
            response = self.client.search(
                index=self.index_name,
                body=query_body
            )

            hits = response['hits']['hits']
            results = [
                {
                    'document_id': hit['_id'],
                    'score': hit['_score'],
                    'content': hit['_source']['content'],
                    'metadata': hit['_source']['metadata']
                }
                for hit in hits
            ]

            logger.info(f"Found {len(results)} similar documents")
            return results

        except Exception as e:
            logger.error(f"Failed to search documents: {str(e)}")
            raise

    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the index"""
        try:
            response = self.client.delete(
                index=self.index_name,
                id=document_id
            )
            logger.info(f"Deleted document {document_id}: {response['result']}")
            return response['result'] == 'deleted'
        except Exception as e:
            logger.error(f"Failed to delete document: {str(e)}")
            raise

opensearch_service = OpenSearchService()
