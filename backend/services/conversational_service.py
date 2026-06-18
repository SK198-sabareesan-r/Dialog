"""
Conversational Response Service

Generates friendly, conversational responses for greetings and small talk
without referencing the knowledge base.
"""

import boto3
import json
import os
from typing import Generator
from utils.logger import get_logger

logger = get_logger(__name__)

# Bedrock runtime client
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

# Use the generation model ARN from .env (same as main KB service)
MODEL_ID = os.getenv('BEDROCK_GENERATION_MODEL_ARN', 'global.anthropic.claude-sonnet-4-5-20250929-v1:0')


class ConversationalService:
    """Generates conversational responses for greetings and small talk."""

    def __init__(self):
        self.system_prompt_en = """You are a friendly AI assistant for Dialog, a telecommunications company in Sri Lanka. You help users find information from their knowledge base.

When users greet you or have small talk:
- Respond warmly and briefly (1-2 sentences max)
- Be helpful and professional
- For greetings: welcome them and let them know you can help with questions
- For thanks: acknowledge gracefully
- For farewells: say goodbye warmly and invite them to return
- For "how are you": respond positively and redirect to helping them

Do NOT mention documents, knowledge base, or sources in greeting responses.
Keep it natural and conversational."""

        self.system_prompt_si = """ඔබ Dialog සඳහා මිත්‍රශීලී AI සහායකයෙකි. Dialog යනු ශ්‍රී ලංකාවේ විදුලි සංදේශ සමාගමකි.

පරිශීලකයින් ඔබට ආචාර කරන විට හෝ කතාබස් කරන විට:
- උණුසුම්ව හා කෙටියෙන් ප්‍රතිචාර දක්වන්න (වාක්‍ය 1-2ක් පමණ)
- උදව්කාරී හා වෘත්තීය වන්න
- ආචාර සඳහා: ඔවුන්ට සාදරයෙන් පිළිගෙන ප්‍රශ්න වලට උදව් කළ හැකි බව දන්වන්න
- ස්තූතියට: කරුණාවෙන් පිළිගන්න
- සමුගැනීම් සඳහා: උණුසුම්ව සමුදෙන්න

ස්වභාවික හා සංවාදාත්මක ලෙස තබා ගන්න."""

        self.system_prompt_ta = """நீங்கள் Dialog க்கான நட்பு AI உதவியாளர். Dialog என்பது இலங்கையில் உள்ள தொலைத்தொடர்பு நிறுவனம்.

பயனர்கள் உங்களை வாழ்த்தும்போது அல்லது பேசும்போது:
- அன்பாகவும் சுருக்கமாகவும் பதிலளிக்கவும் (1-2 வாக்கியங்கள் மட்டும்)
- உதவிகரமாகவும் தொழில்முறையாகவும் இருங்கள்
- வாழ்த்துகளுக்கு: அவர்களை வரவேற்று கேள்விகளுக்கு உதவ முடியும் என்று தெரிவிக்கவும்
- நன்றிக்கு: அன்புடன் ஏற்றுக்கொள்ளுங்கள்
- விடைபெறுதலுக்கு: அன்புடன் விடைபெற்று திரும்பி வர அழைக்கவும்

இயல்பான மற்றும் உரையாடல் முறையில் வைத்திருங்கள்."""

    def generate_response(self, query: str, greeting_type: str, language: str = 'en') -> Generator[str, None, None]:
        """
        Generate a conversational response for greetings.

        Args:
            query: User's original message
            greeting_type: Type of greeting ('greeting', 'farewell', 'thanks', 'how_are_you')
            language: Detected language ('en', 'si', 'ta')

        Yields:
            Text chunks of the response
        """
        try:
            # Select appropriate system prompt
            if language == 'si':
                system_prompt = self.system_prompt_si
            elif language == 'ta':
                system_prompt = self.system_prompt_ta
            else:
                system_prompt = self.system_prompt_en

            # Construct user prompt based on greeting type
            user_prompt = f"User said: \"{query}\"\n\nRespond appropriately in {self._get_language_name(language)}."

            # Prepare Bedrock request
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 200,  # Short response
                "temperature": 0.7,  # Slightly creative
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            }

            # Invoke with streaming
            response = bedrock.invoke_model_with_response_stream(
                modelId=MODEL_ID,
                contentType='application/json',
                accept='application/json',
                body=json.dumps(request_body)
            )

            # Stream the response
            stream = response.get('body')
            if stream:
                for event in stream:
                    chunk = event.get('chunk')
                    if chunk:
                        chunk_obj = json.loads(chunk.get('bytes').decode())

                        if chunk_obj['type'] == 'content_block_delta':
                            if chunk_obj.get('delta', {}).get('type') == 'text_delta':
                                text = chunk_obj['delta'].get('text', '')
                                if text:
                                    yield text

        except Exception as e:
            logger.error(f"Failed to generate conversational response: {e}", exc_info=True)
            # Fallback response
            fallback = self._get_fallback_response(greeting_type, language)
            yield fallback

    def _get_language_name(self, lang_code: str) -> str:
        """Convert language code to full name."""
        mapping = {
            'en': 'English',
            'si': 'Sinhala',
            'ta': 'Tamil'
        }
        return mapping.get(lang_code, 'English')

    def _get_fallback_response(self, greeting_type: str, language: str) -> str:
        """Return a fallback response if LLM fails."""
        fallbacks = {
            'en': {
                'greeting': "Hello! I'm here to help you with questions about Dialog services. What would you like to know?",
                'farewell': "Goodbye! Feel free to come back anytime you need assistance.",
                'thanks': "You're welcome! Let me know if you need anything else.",
                'how_are_you': "I'm doing great, thank you! How can I help you today?",
            },
            'si': {
                'greeting': "ආයුබෝවන්! Dialog සේවා පිළිබඳ ඔබේ ප්‍රශ්නවලට උදව් කිරීමට මම මෙහි සිටිමි. ඔබ දැනගන්න කැමති කුමක්ද?",
                'farewell': "සමුගන්නවා! ඕනෑම වේලාවක උදව්වක් අවශ්‍ය නම් නැවත පැමිණෙන්න.",
                'thanks': "ඔබට සාදරයෙන්! වෙනත් යමක් අවශ්‍ය නම් මට දන්වන්න.",
                'how_are_you': "මම හොඳින්, ස්තූතියි! අද මම ඔබට උදව් කළ හැක්කේ කෙසේද?",
            },
            'ta': {
                'greeting': "வணக்கம்! Dialog சேவைகள் பற்றிய கேள்விகளுக்கு உதவ நான் இங்கே இருக்கிறேன். நீங்கள் என்ன தெரிந்து கொள்ள விரும்புகிறீர்கள்?",
                'farewell': "விடைபெறுகிறேன்! உங்களுக்கு உதவி தேவைப்பட்டால் எப்போது வேண்டுமானாலும் திரும்பி வாருங்கள்.",
                'thanks': "உங்களுக்கு வரவேற்பு! வேறு ஏதாவது தேவைப்பட்டால் எனக்கு தெரியப்படுத்துங்கள்.",
                'how_are_you': "நான் நன்றாக இருக்கிறேன், நன்றி! இன்று நான் உங்களுக்கு எப்படி உதவ முடியும்?",
            }
        }

        lang_fallbacks = fallbacks.get(language, fallbacks['en'])
        return lang_fallbacks.get(greeting_type, lang_fallbacks['greeting'])


# Singleton instance
conversational_service = ConversationalService()
