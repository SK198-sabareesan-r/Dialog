"""
Confluence Cloud Service — browse spaces/pages and download content.

Auth: Confluence Cloud uses Basic auth (email + API token) or OAuth.
We use email + API token (most common for org setups).

Content exported as:
  - Pages: exported as HTML then saved as .html file
  - Attachments: downloaded as-is (PDFs, DOCX, etc.)
"""

import io
import re
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfluenceService:
    """Browse Confluence Cloud spaces/pages and download for KB ingestion."""

    def _base_url(self, site_url: str) -> str:
        url = site_url.rstrip('/')
        if not url.startswith('http'):
            url = f'https://{url}'
        return f"{url}/wiki/rest/api"

    def _auth(self, email: str, api_token: str) -> HTTPBasicAuth:
        return HTTPBasicAuth(email, api_token)

    def _get(self, site_url: str, email: str, api_token: str, path: str, params: dict = None) -> dict:
        url = f"{self._base_url(site_url)}{path}"
        resp = requests.get(url, auth=self._auth(email, api_token), params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Spaces
    # ------------------------------------------------------------------

    def list_spaces(self, site_url: str, email: str, api_token: str) -> List[Dict[str, Any]]:
        """List all spaces the user has access to."""
        spaces = []
        start = 0
        limit = 50
        while True:
            data = self._get(site_url, email, api_token, '/space', {
                'start': start, 'limit': limit, 'type': 'global',
                'expand': 'description.plain',
            })
            results = data.get('results', [])
            spaces.extend([{
                'key': s['key'],
                'name': s['name'],
                'type': s.get('type', 'global'),
                'description': s.get('description', {}).get('plain', {}).get('value', ''),
            } for s in results])
            if data.get('size', 0) < limit:
                break
            start += limit
        logger.info(f"Found {len(spaces)} Confluence spaces")
        return spaces

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def list_pages(
        self,
        site_url: str,
        email: str,
        api_token: str,
        space_key: str,
        parent_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List pages in a space (optionally filtered by parent or search term)."""
        pages = []
        start = 0
        limit = 50

        if search:
            # CQL search within the space
            cql = f'space="{space_key}" AND type=page AND title~"{search}"'
            while True:
                data = self._get(site_url, email, api_token, '/content/search', {
                    'cql': cql, 'start': start, 'limit': limit,
                    'expand': 'ancestors',
                })
                results = data.get('results', [])
                pages.extend(self._format_pages(results))
                if data.get('size', 0) < limit:
                    break
                start += limit
        elif parent_id:
            # Child pages of a specific parent
            while True:
                data = self._get(site_url, email, api_token, f'/content/{parent_id}/child/page', {
                    'start': start, 'limit': limit, 'expand': 'ancestors',
                })
                results = data.get('results', [])
                pages.extend(self._format_pages(results))
                if data.get('size', 0) < limit:
                    break
                start += limit
        else:
            # Top-level pages in space
            while True:
                data = self._get(site_url, email, api_token, '/content', {
                    'spaceKey': space_key, 'type': 'page',
                    'depth': 'root', 'start': start, 'limit': limit,
                    'expand': 'ancestors',
                })
                results = data.get('results', [])
                pages.extend(self._format_pages(results))
                if data.get('size', 0) < limit:
                    break
                start += limit

        return pages

    def _format_pages(self, results: list) -> List[Dict[str, Any]]:
        return [{
            'id': p['id'],
            'title': p['title'],
            'type': p.get('type', 'page'),
            'url': p.get('_links', {}).get('webui', ''),
        } for p in results]

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    def list_attachments(
        self,
        site_url: str,
        email: str,
        api_token: str,
        page_id: str,
    ) -> List[Dict[str, Any]]:
        """List attachments on a page."""
        data = self._get(site_url, email, api_token, f'/content/{page_id}/child/attachment', {
            'limit': 100,
        })
        results = data.get('results', [])
        return [{
            'id': a['id'],
            'title': a['title'],
            'media_type': a.get('metadata', {}).get('mediaType', ''),
            'size': a.get('extensions', {}).get('fileSize', 0),
            'download_url': a.get('_links', {}).get('download', ''),
        } for a in results]

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download_page_as_html(
        self,
        site_url: str,
        email: str,
        api_token: str,
        page_id: str,
        page_title: str,
    ) -> tuple[bytes, str]:
        """
        Download a page's body as a self-contained HTML file.
        Returns (content_bytes, filename).
        """
        data = self._get(site_url, email, api_token, f'/content/{page_id}', {
            'expand': 'body.storage,version,space',
        })
        title = data.get('title', page_title)
        space_name = data.get('space', {}).get('name', '')
        body_html = data.get('body', {}).get('storage', {}).get('value', '')

        # Wrap in minimal HTML
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>{title}</title></head>
<body>
<h1>{title}</h1>
<p><em>Space: {space_name}</em></p>
{body_html}
</body>
</html>"""
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')[:80]
        filename = f"confluence_{safe_title}.html"
        return html.encode('utf-8'), filename

    def download_attachment(
        self,
        site_url: str,
        email: str,
        api_token: str,
        download_url: str,
        filename: str,
    ) -> bytes:
        """Download a raw attachment by its download URL path."""
        base = site_url.rstrip('/')
        if not base.startswith('http'):
            base = f'https://{base}'
        url = f"{base}/wiki{download_url}" if not download_url.startswith('http') else download_url
        resp = requests.get(url, auth=self._auth(email, api_token), timeout=120, stream=True)
        resp.raise_for_status()
        return resp.content

    def test_connection(self, site_url: str, email: str, api_token: str) -> Dict[str, Any]:
        """Test credentials and return user info."""
        data = self._get(site_url, email, api_token, '/user/current', {})
        return {
            'display_name': data.get('displayName', ''),
            'email': data.get('email', ''),
            'account_id': data.get('accountId', ''),
        }


confluence_service = ConfluenceService()
