"""
Greeting Detection Utility

Detects if a user message is a conversational greeting/farewell/thanks
rather than a knowledge base query.
"""

import re
from typing import Tuple


class GreetingDetector:
    """Detects greetings, farewells, and conversational messages."""

    def __init__(self):
        # English patterns
        self.greetings_en = [
            r'\b(hi|hello|hey|hola|greetings?)\b',
            r'\bgood\s+(morning|afternoon|evening|day)\b',
            r'\bwhat\'?s\s+up\b',
            r'\bhowdy\b',
        ]

        self.farewells_en = [
            r'\b(bye|goodbye|good\s*bye|see\s+you|farewell|take\s+care)\b',
            r'\bcatch\s+you\s+later\b',
            r'\btalk\s+to\s+you\s+later\b',
            r'\bttyl\b',
        ]

        self.thanks_en = [
            r'\b(thanks?|thank\s+you|thx|ty)\b',
            r'\bappreciate\s+it\b',
            r'\bmuch\s+appreciated\b',
        ]

        self.how_are_you_en = [
            r'\bhow\s+(are|r)\s+you\b',
            r'\bhow\'s\s+it\s+going\b',
            r'\bhow\s+have\s+you\s+been\b',
        ]

        # Sinhala patterns (common greetings)
        self.greetings_si = [
            r'හෙලෝ',
            r'ආයුබෝවන්',
            r'හායි',
            r'හලෝ',
        ]

        self.farewells_si = [
            r'බායි',
            r'ගුඩ්\s*බායි',
            r'යන්නම්',
        ]

        self.thanks_si = [
            r'ස්තූතියි',
            r'ස්තුතියි',
            r'බොහොම\s+ස්තූතියි',
            r'ථෑන්ක්ස්',
        ]

        # Tamil patterns (common greetings)
        self.greetings_ta = [
            r'வணக்கம்',
            r'ஹலோ',
            r'ஹாய்',
        ]

        self.farewells_ta = [
            r'பை',
            r'குட்\s*பை',
        ]

        self.thanks_ta = [
            r'நன்றி',
            r'மிக்க\s+நன்றி',
            r'தேங்க்ஸ்',
        ]

        # Compile all patterns
        self.all_patterns = {
            'greeting': self.greetings_en + self.greetings_si + self.greetings_ta,
            'farewell': self.farewells_en + self.farewells_si + self.farewells_ta,
            'thanks': self.thanks_en + self.thanks_si + self.thanks_ta,
            'how_are_you': self.how_are_you_en,
        }

    def is_greeting(self, query: str, language: str = None) -> Tuple[bool, str]:
        """
        Check if a query is a greeting/conversational message.

        Args:
            query: User's message
            language: Detected language (optional, for better accuracy)

        Returns:
            (is_greeting: bool, greeting_type: str)
            greeting_type is one of: 'greeting', 'farewell', 'thanks', 'how_are_you', 'none'
        """
        if not query or not query.strip():
            return False, 'none'

        query_clean = query.strip()
        query_lower = query_clean.lower()

        # Rule 1: If query is too long, likely not a pure greeting
        # Allow up to 50 chars to handle "Good morning, how are you?"
        if len(query_clean) > 50:
            return False, 'none'

        # Rule 2: If query contains question words + is long, likely a real question
        question_indicators = ['what', 'how', 'when', 'where', 'why', 'who', 'which', 'can', 'could', 'should', 'would']
        has_question = any(q in query_lower for q in question_indicators)
        has_question_mark = '?' in query_clean

        # If it's a question AND longer than 15 chars, likely a real query
        # Exception: "how are you?" is a greeting
        if (has_question or has_question_mark) and len(query_clean) > 15:
            # Check if it's "how are you" type greeting
            for pattern in self.all_patterns['how_are_you']:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return True, 'how_are_you'
            # Otherwise, it's a real question
            return False, 'none'

        # Rule 3: Check against all greeting patterns
        for greeting_type, patterns in self.all_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return True, greeting_type

        return False, 'none'


# Singleton instance
greeting_detector = GreetingDetector()
