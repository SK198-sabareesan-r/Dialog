"""
Translation Service - Language detection and translation using Amazon Translate.

Supports:
- English (en)
- Sinhala (si)
- Tamil   (ta)

Flow:
  User query (any language)
      → detect language
      → translate to English (if not already English)
      → KB search in English
      → translate results back to original language
"""

import re
import boto3
from typing import Optional, List
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Languages supported by this application
SUPPORTED_LANGUAGES = {
    "en": "English",
    "si": "Sinhala",
    "ta": "Tamil",
}


class TranslationService:
    """Wraps Amazon Translate for language detection and translation."""

    def __init__(self):
        aws_credentials = {
            "region_name": settings.AWS_REGION,
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        }
        if settings.AWS_SESSION_TOKEN:
            aws_credentials["aws_session_token"] = settings.AWS_SESSION_TOKEN

        self.client = boto3.client("translate", **aws_credentials)
        self.comprehend = boto3.client("comprehend", **aws_credentials)

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text.
        Returns ISO language code: 'en', 'si', 'ta', etc.
        Falls back to 'en' if detection fails or confidence is low.
        """
        if not text or not text.strip():
            return "en"

        try:
            response = self.comprehend.detect_dominant_language(Text=text[:300])
            languages = response.get("Languages", [])

            if not languages:
                logger.warning("No language detected, defaulting to English")
                return "en"

            top = max(languages, key=lambda x: x["Score"])
            detected = top["LanguageCode"]
            confidence = top["Score"]

            logger.info(
                f"Detected language: {detected} "
                f"({SUPPORTED_LANGUAGES.get(detected, 'unknown')}) "
                f"confidence: {confidence:.2f}"
            )

            if detected in SUPPORTED_LANGUAGES and confidence >= 0.7:
                return detected

            return "en"

        except Exception as e:
            logger.error(f"Language detection failed: {str(e)}")
            return "en"

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Translate plain text from source_lang to target_lang."""
        if source_lang == target_lang:
            return text

        if not text or not text.strip():
            return text

        try:
            response = self.client.translate_text(
                Text=text,
                SourceLanguageCode=source_lang,
                TargetLanguageCode=target_lang,
            )
            translated = response["TranslatedText"]
            logger.info(
                f"Translated {source_lang} → {target_lang} "
                f"({len(text)} chars → {len(translated)} chars)"
            )
            return translated

        except Exception as e:
            logger.error(f"Translation failed ({source_lang} → {target_lang}): {str(e)}")
            return text

    def from_english_markdown(self, markdown_text: str, target_lang: str) -> str:
        """
        Translate an English markdown answer to target_lang, preserving structure.

        Post-processing steps applied after translation:
          1. Fix bold markers broken by Translate (** text** → **text**)
          2. Fix numbered lists reset to 1. 1. 1. → 1. 2. 3.
        """
        if not markdown_text or not markdown_text.strip():
            return markdown_text

        # Translate the whole markdown in one call
        translated = self.translate(markdown_text, source_lang="en", target_lang=target_lang)

        # Fix bold/italic markers that Translate broke with extra spaces
        translated = self._fix_bold_markers(translated)

        # Fix collapsed numbered lists (1. 1. 1. → 1. 2. 3.)
        translated = self._fix_numbered_lists(translated)

        logger.info(f"from_english_markdown en → {target_lang}: done")
        return translated

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    def _fix_bold_markers(self, text: str) -> str:
        """
        Fix bold/italic markers that Amazon Translate breaks by inserting
        spaces inside them, so react-markdown can render them correctly.

        Patterns fixed:
          ** text**   →  **text**   (space after opening **)
          **text **   →  **text**   (space before closing **)
          ** text **  →  **text**   (both sides)
          * text*     →  *text*     (same for single * italic)
        """
        # Fix spaces immediately inside ** bold markers
        # Handles: ** text** , **text ** , ** text **
        text = re.sub(r'\*\*\s+(.+?)\*\*', lambda m: f'**{m.group(1).strip()}**', text)
        text = re.sub(r'\*\*(.+?)\s+\*\*', lambda m: f'**{m.group(1).strip()}**', text)

        # Fix spaces inside * italic markers (only single *, not **)
        text = re.sub(r'(?<!\*)\*\s+(.+?)\*(?!\*)', lambda m: f'*{m.group(1).strip()}*', text)
        text = re.sub(r'(?<!\*)\*(.+?)\s+\*(?!\*)', lambda m: f'*{m.group(1).strip()}*', text)

        # If a line has an odd number of ** (one was dropped by Translate),
        # add a closing ** at the end of the line so it still renders as bold
        lines = text.splitlines()
        clean_lines = []
        for line in lines:
            count = len(re.findall(r'\*\*', line))
            if count % 2 != 0:
                line = line.rstrip() + '**'
            clean_lines.append(line)

        return '\n'.join(clean_lines)

    def _fix_numbered_lists(self, text: str) -> str:
        """
        Fix numbered lists where Amazon Translate reset every item to '1.'.

        Only renumbers a consecutive run of list items if ALL items in that
        run start with '1.' — meaning Translate collapsed the numbers.
        Legitimate separate single-item '1.' entries are left alone.
        """
        lines = text.splitlines()

        # Identify runs of consecutive numbered list lines
        runs: List[tuple] = []   # (start_idx, end_idx) inclusive
        i = 0
        while i < len(lines):
            if re.match(r'^\d+\.\s+', lines[i]):
                start = i
                while i < len(lines) and re.match(r'^\d+\.\s+', lines[i]):
                    i += 1
                runs.append((start, i - 1))
            else:
                i += 1

        # For each run where every item starts with '1.', renumber sequentially
        result = lines[:]
        for start, end in runs:
            nums = [int(re.match(r'^(\d+)\.', result[j]).group(1)) for j in range(start, end + 1)]
            if all(n == 1 for n in nums) and (end - start) > 0:
                for offset, j in enumerate(range(start, end + 1)):
                    rest = re.match(r'^\d+\.\s+(.*)', result[j]).group(1)
                    result[j] = f"{offset + 1}. {rest}"

        return '\n'.join(result)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def to_english(self, text: str, source_lang: str) -> str:
        """Translate any text to English."""
        return self.translate(text, source_lang=source_lang, target_lang="en")

    def from_english(self, text: str, target_lang: str) -> str:
        """Translate English plain text to target language."""
        return self.translate(text, source_lang="en", target_lang=target_lang)

    def is_english(self, lang_code: str) -> bool:
        return lang_code == "en"


# Singleton instance
translation_service = TranslationService()
