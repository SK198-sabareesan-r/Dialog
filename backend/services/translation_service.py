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

import boto3
from typing import Optional
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

        Uses Amazon Comprehend for detection.
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

            # Pick highest confidence language
            top = max(languages, key=lambda x: x["Score"])
            detected = top["LanguageCode"]
            confidence = top["Score"]

            logger.info(
                f"Detected language: {detected} "
                f"({SUPPORTED_LANGUAGES.get(detected, 'unknown')}) "
                f"confidence: {confidence:.2f}"
            )

            # If it's a supported language with decent confidence, use it
            if detected in SUPPORTED_LANGUAGES and confidence >= 0.7:
                return detected

            # Default to English for unsupported or low-confidence
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
        """
        Translate text from source_lang to target_lang.

        Args:
            text:        Text to translate
            source_lang: ISO code of source language ('en', 'si', 'ta')
            target_lang: ISO code of target language ('en', 'si', 'ta')

        Returns:
            Translated text. Returns original text if translation fails.
        """
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
            logger.error(
                f"Translation failed ({source_lang} → {target_lang}): {str(e)}"
            )
            # Return original text rather than crashing
            return text

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def to_english(self, text: str, source_lang: str) -> str:
        """Translate any text to English."""
        return self.translate(text, source_lang=source_lang, target_lang="en")

    def from_english(self, text: str, target_lang: str) -> str:
        """Translate English text to target language."""
        return self.translate(text, source_lang="en", target_lang=target_lang)

    def is_english(self, lang_code: str) -> bool:
        return lang_code == "en"


# Singleton instance
translation_service = TranslationService()
