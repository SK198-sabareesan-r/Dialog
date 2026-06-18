"""
Sync Connectors — S3, Google Drive, Confluence
"""

from services.connectors.s3_connector import S3Connector
from services.connectors.gdrive_connector import GoogleDriveConnector
from services.connectors.confluence_connector import ConfluenceConnector


def get_connector(source_type: str):
    """Factory to get the right connector by source type."""
    connectors = {
        "s3": S3Connector,
        "google_drive": GoogleDriveConnector,
        "confluence": ConfluenceConnector,
    }
    connector_class = connectors.get(source_type)
    if not connector_class:
        raise ValueError(f"Unknown source type: {source_type}")
    return connector_class()
