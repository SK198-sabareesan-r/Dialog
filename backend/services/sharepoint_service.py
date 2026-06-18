"""
SharePoint Online Service — browse sites/drives/files via Microsoft Graph API.

Auth: Azure AD client credentials (tenant_id + client_id + client_secret).
      Admin registers app once with Sites.Read.All (application permission).
"""

import re
import requests
from typing import Dict, Any, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)

GRAPH_BASE = 'https://graph.microsoft.com/v1.0'


class SharePointService:

    def _get_token(self, tenant_id: str, client_id: str, client_secret: str) -> str:
        url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
        resp = requests.post(url, data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'https://graph.microsoft.com/.default',
        }, timeout=15)
        resp.raise_for_status()
        return resp.json()['access_token']

    def _headers(self, token: str) -> dict:
        return {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}

    def _get(self, token: str, path: str, params: dict = None) -> dict:
        url = f'{GRAPH_BASE}{path}'
        resp = requests.get(url, headers=self._headers(token), params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------

    def test_connection(self, tenant_id: str, client_id: str, client_secret: str, site_url: str) -> Dict[str, Any]:
        token = self._get_token(tenant_id, client_id, client_secret)
        # Resolve site URL to a site object
        hostname, path = self._parse_site_url(site_url)
        data = self._get(token, f'/sites/{hostname}:{path}')
        return {
            'site_id': data['id'],
            'site_name': data.get('displayName', data.get('name', '')),
            'web_url': data.get('webUrl', ''),
        }

    # ------------------------------------------------------------------
    # Sites
    # ------------------------------------------------------------------

    def list_sites(self, tenant_id: str, client_id: str, client_secret: str, site_url: str) -> List[Dict[str, Any]]:
        """Return the configured site plus its subsites."""
        token = self._get_token(tenant_id, client_id, client_secret)
        hostname, path = self._parse_site_url(site_url)
        root = self._get(token, f'/sites/{hostname}:{path}')
        sites = [{'id': root['id'], 'name': root.get('displayName', root.get('name', '')), 'web_url': root.get('webUrl', '')}]

        try:
            sub = self._get(token, f'/sites/{root["id"]}/sites')
            for s in sub.get('value', []):
                sites.append({'id': s['id'], 'name': s.get('displayName', s.get('name', '')), 'web_url': s.get('webUrl', '')})
        except Exception:
            pass

        return sites

    # ------------------------------------------------------------------
    # Drives (document libraries)
    # ------------------------------------------------------------------

    def list_drives(self, tenant_id: str, client_id: str, client_secret: str, site_id: str) -> List[Dict[str, Any]]:
        token = self._get_token(tenant_id, client_id, client_secret)
        data = self._get(token, f'/sites/{site_id}/drives')
        return [{'id': d['id'], 'name': d.get('name', ''), 'drive_type': d.get('driveType', '')} for d in data.get('value', [])]

    # ------------------------------------------------------------------
    # Items (files + folders)
    # ------------------------------------------------------------------

    def list_items(self, tenant_id: str, client_id: str, client_secret: str, drive_id: str, folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        token = self._get_token(tenant_id, client_id, client_secret)
        if folder_id:
            path = f'/drives/{drive_id}/items/{folder_id}/children'
        else:
            path = f'/drives/{drive_id}/root/children'

        data = self._get(token, path, {'$top': 200})
        items = []
        for item in data.get('value', []):
            is_folder = 'folder' in item
            items.append({
                'id': item['id'],
                'name': item.get('name', ''),
                'is_folder': is_folder,
                'size': item.get('size', 0),
                'mime_type': item.get('file', {}).get('mimeType', '') if not is_folder else '',
                'download_url': item.get('@microsoft.graph.downloadUrl', ''),
            })
        return items

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download_file(self, tenant_id: str, client_id: str, client_secret: str, drive_id: str, item_id: str) -> tuple[bytes, str]:
        """Download a file by drive + item ID. Returns (bytes, filename)."""
        token = self._get_token(tenant_id, client_id, client_secret)
        meta = self._get(token, f'/drives/{drive_id}/items/{item_id}')
        filename = meta.get('name', 'file')

        download_url = meta.get('@microsoft.graph.downloadUrl')
        if not download_url:
            content_url = f'{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content'
            resp = requests.get(content_url, headers=self._headers(token), timeout=120, allow_redirects=True)
        else:
            resp = requests.get(download_url, timeout=120, stream=True)

        resp.raise_for_status()
        return resp.content, filename

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_site_url(self, site_url: str):
        """Extract hostname and server-relative path from a SharePoint URL."""
        site_url = site_url.rstrip('/')
        if not site_url.startswith('http'):
            site_url = f'https://{site_url}'
        from urllib.parse import urlparse
        parsed = urlparse(site_url)
        hostname = parsed.netloc
        path = parsed.path or '/'
        return hostname, path


sharepoint_service = SharePointService()
