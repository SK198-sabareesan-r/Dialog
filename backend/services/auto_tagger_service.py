"""
Auto-Tagger Service — AI-Powered Metadata Generation at Ingestion Time

Extracts a text sample from uploaded documents and uses Claude to automatically
generate structured metadata tags (department, document_type, topics, language, etc.).

These tags are written as a Bedrock KB .metadata.json file alongside the document
in S3, enabling dynamic metadata filtering at retrieval time.
"""

import io
import json
import boto3
from typing import Dict, Any, Optional

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_TEXT_SAMPLE_CHARS = 5000


class AutoTaggerService:
    """Extract text from documents and generate metadata tags using Claude."""

    def __init__(self):
        aws_credentials = {
            "region_name": settings.AWS_REGION,
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        }
        if settings.AWS_SESSION_TOKEN:
            aws_credentials["aws_session_token"] = settings.AWS_SESSION_TOKEN

        self.bedrock_runtime = boto3.client("bedrock-runtime", **aws_credentials)
        self.model_id = settings.BEDROCK_GENERATION_MODEL_ARN

    # ------------------------------------------------------------------
    # Text extraction from various file types
    # ------------------------------------------------------------------

    def _extract_text_sample(
        self, file_content: bytes, filename: str, content_type: str
    ) -> Optional[str]:
        """
        Extract a text sample from the document for Claude to analyze.
        Returns up to MAX_TEXT_SAMPLE_CHARS characters, or None if extraction fails.
        """
        text = None

        try:
            if content_type == "application/pdf":
                text = self._extract_pdf_text(file_content)

            elif content_type in (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ):
                text = self._extract_docx_text(file_content)

            elif content_type in (
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ):
                text = self._extract_pptx_text(file_content)

            elif content_type in (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ):
                text = self._extract_xlsx_text(file_content)

            elif content_type in ("text/plain", "text/csv", "text/html"):
                text = file_content.decode("utf-8", errors="ignore")

            elif content_type.startswith("image/"):
                text = f"[Image file: {filename}]"

            elif content_type.startswith("video/") or content_type.startswith("audio/"):
                text = f"[Media file: {filename}]"

            else:
                text = f"[File: {filename}, type: {content_type}]"

        except Exception as e:
            logger.warning(f"Text extraction failed for {filename}: {e}")
            text = f"[File: {filename}, type: {content_type}]"

        if text:
            return text[:MAX_TEXT_SAMPLE_CHARS]
        return None

    def _extract_pdf_text(self, file_content: bytes) -> str:
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        pages_text = []
        total_pages = len(reader.pages)
        # Sample pages spread across the document to catch multilingual content
        # Take first 3 pages + middle page + last page
        sample_indices = list(range(min(3, total_pages)))
        if total_pages > 4:
            sample_indices.append(total_pages // 2)
        if total_pages > 1:
            sample_indices.append(total_pages - 1)
        # Deduplicate and sort
        sample_indices = sorted(set(sample_indices))

        for i in sample_indices:
            page_text = reader.pages[i].extract_text()
            if page_text:
                pages_text.append(f"[Page {i+1}]\n{page_text}")
        return "\n".join(pages_text)

    def _extract_docx_text(self, file_content: bytes) -> str:
        from docx import Document

        doc = Document(io.BytesIO(file_content))
        paragraphs = [p.text for p in doc.paragraphs[:50] if p.text.strip()]
        return "\n".join(paragraphs)

    def _extract_pptx_text(self, file_content: bytes) -> str:
        from pptx import Presentation

        prs = Presentation(io.BytesIO(file_content))
        slides_text = []
        for slide in prs.slides[:10]:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    slides_text.append(shape.text_frame.text)
        return "\n".join(slides_text)

    def _extract_xlsx_text(self, file_content: bytes) -> str:
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True)
        text_parts = []
        for sheet_name in wb.sheetnames[:3]:
            ws = wb[sheet_name]
            text_parts.append(f"Sheet: {sheet_name}")
            row_count = 0
            for row in ws.iter_rows(values_only=True):
                if row_count >= 20:
                    break
                row_text = " | ".join(str(cell) for cell in row if cell is not None)
                if row_text.strip():
                    text_parts.append(row_text)
                row_count += 1
        return "\n".join(text_parts)

    # ------------------------------------------------------------------
    # Claude-based auto-tagging
    # ------------------------------------------------------------------

    def generate_tags(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        user_id: str,
        team_id: Optional[str] = None,
        department: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate metadata tags for a document using Claude.

        Returns a dict suitable for Bedrock KB .metadata.json format:
        {
            "metadataAttributes": {
                "department": "...",
                "doc_type": "...",
                "topic": "...",
                "language": "...",
                "user_id": "...",
                ...
            }
        }
        """
        text_sample = self._extract_text_sample(file_content, filename, content_type)

        if not text_sample or text_sample.startswith("["):
            # Can't extract meaningful text — use basic metadata only
            logger.info(f"No text extractable from {filename}, using basic metadata only")
            return self._build_basic_metadata(
                filename, content_type, user_id, team_id, department, tags
            )

        # Call Claude to analyze the text and generate tags
        ai_tags = self._call_claude_for_tags(text_sample, filename, content_type)

        # Merge AI-generated tags with user-provided metadata
        metadata_attributes = {
            "user_id": user_id,
            "source": "web_ui",
            "filename": filename,
            "content_type": content_type,
        }

        if team_id:
            metadata_attributes["team_id"] = team_id
        if department:
            metadata_attributes["department"] = department
        elif ai_tags.get("department"):
            metadata_attributes["department"] = ai_tags["department"]
        if tags:
            metadata_attributes["tags"] = tags

        # Add AI-generated fields (don't overwrite user-provided ones)
        for key in ("doc_type", "topic", "sub_topic", "summary", "confidentiality"):
            if ai_tags.get(key) and key not in metadata_attributes:
                metadata_attributes[key] = ai_tags[key]

        # Handle multilingual: store languages as a list for Bedrock KB 'in' filter
        if ai_tags.get("languages") and isinstance(ai_tags["languages"], list):
            metadata_attributes["languages"] = ai_tags["languages"]
            metadata_attributes["primary_language"] = ai_tags.get("primary_language", ai_tags["languages"][0])
            metadata_attributes["is_multilingual"] = str(len(ai_tags["languages"]) > 1).lower()
        elif ai_tags.get("primary_language"):
            metadata_attributes["languages"] = [ai_tags["primary_language"]]
            metadata_attributes["primary_language"] = ai_tags["primary_language"]
            metadata_attributes["is_multilingual"] = "false"

        return {"metadataAttributes": metadata_attributes}

    def _call_claude_for_tags(
        self, text_sample: str, filename: str, content_type: str
    ) -> Dict[str, Any]:
        """
        Call Claude to analyze document text and return structured metadata tags.
        """
        prompt = f"""You are a document classification engine for an enterprise knowledge base. Analyze the following document content and return structured metadata tags.

FILENAME: {filename}
CONTENT TYPE: {content_type}

DOCUMENT CONTENT (sampled {len(text_sample)} characters from multiple pages):
---
{text_sample}
---

Return a JSON object with these fields. Be specific and accurate based on the content:

{{
  "department": "the most likely department this belongs to (e.g. HR, Finance, IT, Marketing, Legal, Operations, Engineering, Sales, Customer Support, Management)",
  "doc_type": "document type (e.g. policy, report, guide, manual, memo, proposal, invoice, contract, presentation, spreadsheet, meeting_notes, training_material)",
  "topic": "primary topic in 2-4 words (e.g. leave_management, quarterly_revenue, network_security)",
  "sub_topic": "secondary topic if applicable, otherwise empty string",
  "languages": ["list of ALL language codes detected in the document (e.g. [\"en\", \"si\", \"ta\"]). A multilingual document should list ALL languages found across pages. Use ISO 639-1 codes: en=English, si=Sinhala, ta=Tamil"],
  "primary_language": "the dominant language code (the one with most content)",
  "summary": "one-sentence summary of the document content (max 100 chars)",
  "confidentiality": "public, internal, confidential, or restricted — based on content sensitivity"
}}

RULES:
- Base ALL answers on the actual document content, not assumptions
- Use lowercase for all values except department names
- If uncertain about a field, use "unknown"
- For languages: carefully check ALL pages for different scripts/languages. Sinhala uses සිංහල script, Tamil uses தமிழ் script. A document can have 1, 2, or 3+ languages.
- Return ONLY the JSON object, no explanation

JSON:"""

        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                }),
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            raw_text = response_body["content"][0]["text"].strip()

            # Handle possible markdown wrapping
            if raw_text.startswith("```"):
                raw_text = raw_text.split("\n", 1)[1]
                raw_text = raw_text.rsplit("```", 1)[0]

            tags = json.loads(raw_text)
            logger.info(f"Auto-tagged {filename}: dept={tags.get('department')}, type={tags.get('doc_type')}, topic={tags.get('topic')}")
            return tags

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Claude tags for {filename}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Claude auto-tagging failed for {filename}: {e}")
            return {}

    def _build_basic_metadata(
        self,
        filename: str,
        content_type: str,
        user_id: str,
        team_id: Optional[str],
        department: Optional[str],
        tags: Optional[str],
    ) -> Dict[str, Any]:
        """Build basic metadata when text extraction is not possible."""
        metadata_attributes = {
            "user_id": user_id,
            "source": "web_ui",
            "filename": filename,
            "content_type": content_type,
        }
        if team_id:
            metadata_attributes["team_id"] = team_id
        if department:
            metadata_attributes["department"] = department
        if tags:
            metadata_attributes["tags"] = tags

        # Infer doc_type from content_type
        if content_type.startswith("image/"):
            metadata_attributes["doc_type"] = "image"
        elif content_type.startswith("video/"):
            metadata_attributes["doc_type"] = "video"
        elif content_type.startswith("audio/"):
            metadata_attributes["doc_type"] = "audio"
        elif "spreadsheet" in content_type:
            metadata_attributes["doc_type"] = "spreadsheet"
        elif "presentation" in content_type:
            metadata_attributes["doc_type"] = "presentation"

        return {"metadataAttributes": metadata_attributes}


# Singleton instance
auto_tagger_service = AutoTaggerService()
