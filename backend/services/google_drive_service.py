"""
Google Drive Service — calls the Drive v3 REST API directly via requests.

Uses Bearer token auth (access_token from Google OAuth) without the
google-auth library, which requires refresh_token + client credentials
even for simple short-lived token usage.
"""

import io
import requests
from typing import Dict, Any, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

DRIVE_API = 'https://www.googleapis.com/drive/v3'
UPLOAD_API = 'https://www.googleapis.com/upload/drive/v3'


class GoogleDriveService:

    def _headers(self, access_token: str) -> dict:
        return {'Authorization': f'Bearer {access_token}'}

    def _get(self, access_token: str, path: str, params: dict = None) -> dict:
        resp = requests.get(
            f'{DRIVE_API}{path}',
            headers=self._headers(access_token),
            params=params or {},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Shared Drive listing
    # ------------------------------------------------------------------

    def list_shared_drives(self, access_token: str) -> List[Dict[str, Any]]:
        try:
            data = self._get(access_token, '/drives', {'pageSize': 100, 'fields': 'drives(id,name,kind)'})
            drives = data.get('drives', [])
            logger.info(f"Found {len(drives)} shared drives")
            return drives
        except Exception as e:
            logger.error(f"Failed to list shared drives: {e}")
            raise

    # ------------------------------------------------------------------
    # File listing
    # ------------------------------------------------------------------

    def list_files(
        self,
        access_token: str,
        drive_id: Optional[str] = None,
        page_size: int = 100,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        try:
            params = {
                'pageSize': page_size,
                'fields': 'files(id,name,mimeType,size,modifiedTime,parents,driveId)',
                'supportsAllDrives': 'true',
                'includeItemsFromAllDrives': 'true',
            }
            if query:
                params['q'] = query
            if drive_id:
                params['driveId'] = drive_id
                params['corpora'] = 'drive'
            else:
                params['corpora'] = 'user'

            data = self._get(access_token, '/files', params)
            files = data.get('files', [])
            logger.info(f"Listed {len(files)} files")
            return files
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            raise

    # ------------------------------------------------------------------
    # Folder browsing
    # ------------------------------------------------------------------

    def browse_folder(
        self,
        access_token: str,
        folder_id: str = 'root',
        drive_id: Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        try:
            params = {
                'q': f"'{folder_id}' in parents and trashed=false",
                'pageSize': 1000,
                'fields': 'files(id,name,mimeType,size,modifiedTime)',
                'orderBy': 'folder,name',
                'supportsAllDrives': 'true',
                'includeItemsFromAllDrives': 'true',
            }
            if drive_id:
                params['driveId'] = drive_id
                params['corpora'] = 'drive'
            else:
                params['corpora'] = 'user'

            data = self._get(access_token, '/files', params)
            items = data.get('files', [])

            folders, files = [], []
            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    folders.append({'id': item['id'], 'name': item['name'], 'mimeType': item['mimeType']})
                else:
                    files.append({
                        'id': item['id'],
                        'name': item['name'],
                        'mimeType': item['mimeType'],
                        'size': item.get('size', '0'),
                        'modifiedTime': item.get('modifiedTime', ''),
                    })

            logger.info(f"Browsed folder {folder_id}: {len(folders)} folders, {len(files)} files")
            return {'folders': folders, 'files': files}
        except Exception as e:
            logger.error(f"Failed to browse folder: {e}")
            raise

    # ------------------------------------------------------------------
    # File download
    # ------------------------------------------------------------------

    def download_file(
        self,
        file_id: str,
        access_token: str,
        drive_id: Optional[str] = None,
    ) -> bytes:
        try:
            # First get the mime type to decide export vs direct download
            meta = self._get(access_token, f'/files/{file_id}', {
                'fields': 'id,name,mimeType',
                'supportsAllDrives': 'true',
            })
            mime_type = meta.get('mimeType', '')

            # Google Workspace types need export
            export_map = {
                'application/vnd.google-apps.document':     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.google-apps.spreadsheet':  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            }

            if mime_type in export_map:
                resp = requests.get(
                    f'{DRIVE_API}/files/{file_id}/export',
                    headers=self._headers(access_token),
                    params={'mimeType': export_map[mime_type], 'supportsAllDrives': 'true'},
                    timeout=120,
                )
            else:
                resp = requests.get(
                    f'{DRIVE_API}/files/{file_id}',
                    headers=self._headers(access_token),
                    params={'alt': 'media', 'supportsAllDrives': 'true'},
                    timeout=120,
                )

            resp.raise_for_status()
            content = resp.content
            logger.info(f"Downloaded file {file_id} ({len(content)} bytes)")
            return content
        except Exception as e:
            logger.error(f"Failed to download from Google Drive: {e}")
            raise

    # ------------------------------------------------------------------
    # File metadata
    # ------------------------------------------------------------------

    def get_file_metadata(self, file_id: str, access_token: str) -> Dict[str, Any]:
        try:
            data = self._get(access_token, f'/files/{file_id}', {
                'fields': 'id,name,mimeType,size,createdTime,modifiedTime,owners,driveId,parents',
                'supportsAllDrives': 'true',
            })
            logger.info(f"Retrieved metadata for file: {data.get('name')}")
            return data
        except Exception as e:
            logger.error(f"Failed to get file metadata: {e}")
            raise


google_drive_service = GoogleDriveService()
