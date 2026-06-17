"""
Google Drive Service - Download files from both personal Google Drive
and Google Shared Drives (Team Drives).

Personal Drive  → user's own My Drive
Shared Drive    → organisation/team shared drives (Team Drives)
"""

from typing import Dict, Any, List, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
import io
from utils.logger import get_logger

logger = get_logger(__name__)


class GoogleDriveService:
    """Service for interacting with Google Drive API.

    Supports both personal (My Drive) and Shared Drives (Team Drives).
    Pass drive_id to target a specific Shared Drive.
    """

    def _get_service(self, access_token: str):
        """Build and return a Google Drive API service client."""
        credentials = Credentials(token=access_token)
        return build('drive', 'v3', credentials=credentials)

    # ------------------------------------------------------------------
    # Shared Drive listing
    # ------------------------------------------------------------------

    def list_shared_drives(self, access_token: str) -> List[Dict[str, Any]]:
        """
        List all Shared Drives (Team Drives) the user has access to.

        Returns:
            List of shared drives with id and name.
        """
        try:
            service = self._get_service(access_token)

            results = service.drives().list(
                pageSize=100,
                fields="drives(id, name, kind)"
            ).execute()

            drives = results.get('drives', [])
            logger.info(f"Found {len(drives)} shared drives")
            return drives

        except Exception as e:
            logger.error(f"Failed to list shared drives: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # File listing
    # ------------------------------------------------------------------

    def list_files(
        self,
        access_token: str,
        drive_id: Optional[str] = None,
        page_size: int = 100,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List files from personal Drive or a specific Shared Drive.

        Args:
            access_token: User's Google access token
            drive_id:     Shared Drive ID (None = personal My Drive)
            page_size:    Number of files to return
            query:        Google Drive query string (optional)

        Returns:
            List of file metadata dicts
        """
        try:
            service = self._get_service(access_token)

            params = {
                'pageSize': page_size,
                'fields': "files(id, name, mimeType, size, modifiedTime, parents, driveId)",
                'supportsAllDrives': True,
                'includeItemsFromAllDrives': True,
            }

            if query:
                params['q'] = query

            if drive_id:
                # Scope listing to a specific Shared Drive
                params['driveId'] = drive_id
                params['corpora'] = 'drive'
                logger.info(f"Listing files in Shared Drive: {drive_id}")
            else:
                # Personal My Drive
                params['corpora'] = 'user'
                logger.info("Listing files in personal My Drive")

            results = service.files().list(**params).execute()
            files = results.get('files', [])

            logger.info(f"Listed {len(files)} files")
            return files

        except Exception as e:
            logger.error(f"Failed to list files: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # File download
    # ------------------------------------------------------------------

    def download_file(
        self,
        file_id: str,
        access_token: str,
        drive_id: Optional[str] = None
    ) -> bytes:
        """
        Download a file from personal Drive or a Shared Drive.

        Args:
            file_id:      Google Drive file ID
            access_token: User's Google access token
            drive_id:     Shared Drive ID (None = personal My Drive)

        Returns:
            File content as bytes
        """
        try:
            service = self._get_service(access_token)

            # supportsAllDrives=True is required for Shared Drive files
            request = service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )

            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)

            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.info(
                        f"Download progress: {int(status.progress() * 100)}%"
                    )

            file_content = file_buffer.getvalue()
            logger.info(
                f"Downloaded file {file_id} "
                f"({'Shared Drive: ' + drive_id if drive_id else 'My Drive'}) "
                f"({len(file_content)} bytes)"
            )

            return file_content

        except Exception as e:
            logger.error(f"Failed to download from Google Drive: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # File metadata
    # ------------------------------------------------------------------

    def get_file_metadata(
        self,
        file_id: str,
        access_token: str
    ) -> Dict[str, Any]:
        """
        Get file metadata from personal Drive or a Shared Drive.

        Returns file name, mime type, size, etc.
        """
        try:
            service = self._get_service(access_token)

            file = service.files().get(
                fileId=file_id,
                supportsAllDrives=True,
                fields='id, name, mimeType, size, createdTime, modifiedTime, owners, driveId, parents'
            ).execute()

            logger.info(f"Retrieved metadata for file: {file.get('name')}")
            return file

        except Exception as e:
            logger.error(f"Failed to get file metadata: {str(e)}")
            raise


# Singleton instance
google_drive_service = GoogleDriveService()
