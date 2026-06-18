"""
Google Drive Connector — Uses a stored refresh_token to sync files from Drive.

Credentials needed from user:
  - refresh_token: obtained during Google login (access_type=offline)
  - folder_id: which folder to sync (user picks via browse UI)
  - drive_id: (optional) shared drive ID

client_id and client_secret are auto-filled from app settings.
"""

import requests
from datetime import datetime
from typing import List, Optional
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_API = "https://www.googleapis.com/drive/v3"


class GoogleDriveConnector:
    """Connects to Google Drive using a refresh token for scheduled sync."""

    def _fill_app_creds(self, credentials: dict) -> dict:
        """Auto-fill client_id/secret from app settings if not provided."""
        creds = dict(credentials)
        if not creds.get("client_id"):
            creds["client_id"] = settings.GOOGLE_CLIENT_ID
        if not creds.get("client_secret"):
            creds["client_secret"] = settings.GOOGLE_CLIENT_SECRET
        return creds

    def test_connection(self, credentials: dict) -> dict:
        """
        Test that the refresh token can get a valid access token.

        credentials:
            refresh_token: str (required — from user's Google login)
            folder_id: str (optional — folder to sync, default "root")
            drive_id: str (optional — for shared drives)
            client_id: str (optional — auto-filled from app settings)
            client_secret: str (optional — auto-filled from app settings)
        """
        try:
            creds = self._fill_app_creds(credentials)
            access_token = self._get_access_token(creds)
            # Verify by listing 1 file
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {"pageSize": 1, "fields": "files(id,name)"}

            if credentials.get("drive_id"):
                params["driveId"] = credentials["drive_id"]
                params["includeItemsFromAllDrives"] = "true"
                params["supportsAllDrives"] = "true"
                params["corpora"] = "drive"

            resp = requests.get(f"{DRIVE_API}/files", headers=headers, params=params)
            resp.raise_for_status()

            return {"success": True, "message": "Connected to Google Drive successfully"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def list_files(
        self, credentials: dict, target_path: str, since: Optional[datetime] = None
    ) -> List[dict]:
        """
        List files in a Drive folder. target_path is the folder_id.
        If `since` is set, only returns files modified after that datetime.
        """
        creds = self._fill_app_creds(credentials)
        access_token = self._get_access_token(creds)
        headers = {"Authorization": f"Bearer {access_token}"}

        folder_id = target_path or creds.get("folder_id", "root")
        drive_id = creds.get("drive_id")

        # Build query
        query_parts = [
            f"'{folder_id}' in parents",
            "trashed = false",
            "mimeType != 'application/vnd.google-apps.folder'",
        ]
        if since:
            since_str = since.strftime("%Y-%m-%dT%H:%M:%S")
            query_parts.append(f"modifiedTime > '{since_str}'")

        params = {
            "q": " and ".join(query_parts),
            "fields": "files(id,name,mimeType,size,modifiedTime)",
            "pageSize": 1000,
        }

        if drive_id:
            params["driveId"] = drive_id
            params["includeItemsFromAllDrives"] = "true"
            params["supportsAllDrives"] = "true"
            params["corpora"] = "drive"

        files = []
        page_token = None

        while True:
            if page_token:
                params["pageToken"] = page_token

            resp = requests.get(f"{DRIVE_API}/files", headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

            for f in data.get("files", []):
                # Skip Google Docs native formats (Sheets, Slides, etc.)
                # They'll be exported as PDF
                files.append({
                    "id": f["id"],
                    "name": f["name"],
                    "path": f"/{folder_id}/{f['name']}",
                    "size": int(f.get("size", 0)),
                    "modified": f.get("modifiedTime", ""),
                    "mime_type": f.get("mimeType", ""),
                })

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        logger.info(f"Google Drive connector: found {len(files)} files in folder {folder_id}")
        return files

    def download_file(self, credentials: dict, file_id: str) -> bytes:
        """Download a file from Google Drive by file ID."""
        creds = self._fill_app_creds(credentials)
        access_token = self._get_access_token(creds)
        headers = {"Authorization": f"Bearer {access_token}"}

        # Try direct download first
        url = f"{DRIVE_API}/files/{file_id}?alt=media"
        params = {}
        if creds.get("drive_id"):
            params["supportsAllDrives"] = "true"

        resp = requests.get(url, headers=headers, params=params)

        # If it's a Google Docs native file, export as PDF
        if resp.status_code == 403 or resp.headers.get("content-type", "").startswith("application/json"):
            url = f"{DRIVE_API}/files/{file_id}/export?mimeType=application/pdf"
            resp = requests.get(url, headers=headers, params=params)

        resp.raise_for_status()
        content = resp.content

        logger.debug(f"Downloaded Drive file {file_id} ({len(content)} bytes)")
        return content

    def get_deterministic_key(self, user_id: str, file_info: dict) -> str:
        """Generate a deterministic S3 key."""
        filename = file_info["name"]
        file_id = file_info["id"]
        # Use file ID to ensure uniqueness even if names collide
        return f"documents/{user_id}/gdrive/{file_id}_{filename}"

    def _get_access_token(self, credentials: dict) -> str:
        """Exchange refresh token for a fresh access token."""
        resp = requests.post(TOKEN_URL, data={
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "refresh_token": credentials["refresh_token"],
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        token = resp.json()["access_token"]
        return token
