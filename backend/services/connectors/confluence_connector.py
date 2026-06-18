"""
Confluence Connector — Fetches pages from Confluence Cloud/Server via REST API.
"""

import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from typing import List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfluenceConnector:
    """Connects to Confluence and downloads pages as HTML/PDF."""

    def test_connection(self, credentials: dict) -> dict:
        """
        Test Confluence connection.

        credentials:
            base_url: str (e.g., https://yourcompany.atlassian.net/wiki)
            email: str
            api_token: str
            space_key: str
        """
        try:
            auth = self._get_auth(credentials)
            base_url = credentials["base_url"].rstrip("/")

            # Test by fetching spaces
            resp = requests.get(
                f"{base_url}/rest/api/space",
                auth=auth,
                params={"limit": 1},
                timeout=10,
            )
            resp.raise_for_status()

            return {"success": True, "message": "Connected to Confluence successfully"}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "message": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def list_files(
        self, credentials: dict, target_path: str, since: Optional[datetime] = None
    ) -> List[dict]:
        """
        List pages in a Confluence space. target_path is the space_key.
        """
        auth = self._get_auth(credentials)
        base_url = credentials["base_url"].rstrip("/")
        space_key = target_path or credentials.get("space_key", "")

        pages = []
        start = 0
        limit = 50

        while True:
            params = {
                "spaceKey": space_key,
                "type": "page",
                "status": "current",
                "start": start,
                "limit": limit,
                "expand": "version,history.lastUpdated",
            }

            resp = requests.get(
                f"{base_url}/rest/api/content",
                auth=auth,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            for page in data.get("results", []):
                last_modified_str = (
                    page.get("history", {}).get("lastUpdated", {}).get("when", "")
                    or page.get("version", {}).get("when", "")
                )

                # Parse modified time
                modified_dt = None
                if last_modified_str:
                    try:
                        modified_dt = datetime.fromisoformat(
                            last_modified_str.replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                # Filter by since
                if since and modified_dt and modified_dt.replace(tzinfo=None) <= since:
                    continue

                pages.append({
                    "id": page["id"],
                    "name": f"{page['title']}.html",
                    "path": f"/{space_key}/{page['title']}",
                    "size": 0,  # Unknown until download
                    "modified": last_modified_str,
                    "title": page["title"],
                })

            # Pagination
            size = data.get("size", 0)
            if size < limit:
                break
            start += limit

        logger.info(f"Confluence connector: found {len(pages)} pages in space {space_key}")
        return pages

    def download_file(self, credentials: dict, file_id: str) -> bytes:
        """
        Download a Confluence page as HTML content (with styling stripped).
        The page body is fetched in 'storage' format and wrapped as a simple HTML file.
        """
        auth = self._get_auth(credentials)
        base_url = credentials["base_url"].rstrip("/")

        # Fetch page with body content
        resp = requests.get(
            f"{base_url}/rest/api/content/{file_id}",
            auth=auth,
            params={"expand": "body.storage,metadata.labels"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        title = data.get("title", "Untitled")
        body_html = data.get("body", {}).get("storage", {}).get("value", "")

        # Wrap as a full HTML document for better KB ingestion
        html_doc = f"""<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
{body_html}
</body>
</html>"""

        content = html_doc.encode("utf-8")
        logger.debug(f"Downloaded Confluence page {file_id}: {title} ({len(content)} bytes)")
        return content

    def get_deterministic_key(self, user_id: str, file_info: dict) -> str:
        """Generate a deterministic S3 key for a Confluence page."""
        page_id = file_info["id"]
        safe_name = file_info["name"].replace(" ", "_").replace("/", "_")
        return f"documents/{user_id}/confluence/{page_id}_{safe_name}"

    def _get_auth(self, credentials: dict):
        """Get HTTP Basic Auth for Confluence API."""
        return HTTPBasicAuth(credentials["email"], credentials["api_token"])
