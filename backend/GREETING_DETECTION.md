# Greeting Detection & Conversational Responses

## Overview

The system now intelligently detects greeting/conversational messages (hi, hello, thanks, bye) and responds directly without searching the knowledge base, providing faster and more natural responses.

## How It Works

### Flow Diagram

```
User Query
    ↓
Language Detection
    ↓
Greeting Detection ←─────┐
    ↓                    │
    Is Greeting?         │
    ↓           ↓        │
   YES         NO        │
    ↓           ↓        │
Conversational  KB Search│
Response        ↓        │
    ↓        Generate    │
    ↓        from KB     │
    ↓           ↓        │
    └───────────┴────────┘
         Stream Response
```

### Components

#### 1. Greeting Detector (`utils/greeting_detector.py`)

**Purpose:** Detects if a message is a greeting/conversational rather than a knowledge query.

**Supported Categories:**
- **Greetings:** hi, hello, hey, good morning, etc.
- **Farewells:** bye, goodbye, see you, etc.
- **Thanks:** thanks, thank you, appreciate it, etc.
- **How are you:** how are you, what's up, etc.

**Multilingual Support:**
- English
- Sinhala (සිංහල): හෙලෝ, ආයුබෝවන්, ස්තූතියි, බායි
- Tamil (தமிழ்): வணக்கம், நன்றி, பை

**Detection Logic:**
```python
is_greeting, greeting_type = greeting_detector.is_greeting(query, language)
# Returns: (True, 'greeting') or (False, 'none')
```

**Edge Cases Handled:**
- ✓ "Hi" → Greeting
- ✓ "Thanks" → Greeting
- ✗ "Hi, how do I get a SIM replacement?" → NOT a greeting (real question)
- ✗ "High speed internet" → NOT a greeting (contains "hi" but is a query)

#### 2. Conversational Service (`services/conversational_service.py`)

**Purpose:** Generates friendly, conversational responses using Claude.

**System Prompts:**
- English: Friendly Dialog assistant, brief responses
- Sinhala: සිංහල උපදෙස් සමඟ
- Tamil: தமிழ் வழிகாட்டுதலுடன்

**Response Examples:**

| Input | Output |
|-------|--------|
| "Hi" | "Hello! I'm here to help you with questions about Dialog services. What would you like to know?" |
| "Thanks" | "You're welcome! Let me know if you need anything else." |
| "Bye" | "Goodbye! Feel free to come back anytime you need assistance." |
| "හෙලෝ" | "ආයුබෝවන්! Dialog සේවා පිළිබඳ ඔබේ ප්‍රශ්නවලට උදව් කිරීමට මම මෙහි සිටිමි..." |

**Fallback Responses:** If LLM fails, uses pre-defined fallback messages per language.

#### 3. Streaming Integration (`api/app.py`)

**Modified:** `query_knowledge_base_stream()` endpoint

**Flow:**
1. Detect language
2. **Check if greeting** ← NEW
3. If greeting:
   - Generate conversational response
   - Stream response
   - Save to chat history (with empty citations)
   - Return early (skip KB search)
4. If NOT greeting:
   - Continue with normal RAG pipeline
   - Translate → Search KB → Generate from sources

## Testing

### Run Unit Tests

```bash
cd backend
python test_greeting_detection.py
```

### Manual Testing

**Test Cases:**

```bash
# English greetings
curl -X POST http://localhost:8001/api/retrieve/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "hello", "user_id": "test"}'

# Sinhala greeting
curl -X POST http://localhost:8001/api/retrieve/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "හෙලෝ", "user_id": "test"}'

# Mixed (should do KB search)
curl -X POST http://localhost:8001/api/retrieve/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "Hi, what is Dialog helpline?", "user_id": "test"}'
```

## Performance Benefits

| Scenario | Before | After |
|----------|--------|-------|
| "Hello" | ~5-10s (KB search + generation) | ~1-2s (direct response) |
| "Thanks" | ~5-10s | ~1-2s |
| User Experience | Slow for simple greetings | Fast and natural |

## Configuration

### Environment Variables

No additional configuration needed. Uses existing:
- `BEDROCK_MODEL_ID` - Claude model for responses
- `AWS_REGION` - AWS region for Bedrock

### Customization

**Add new greeting patterns:**

Edit `utils/greeting_detector.py`:
```python
self.greetings_en.append(r'\bhowdy\b')
self.greetings_si.append(r'අයියේ')
```

**Modify response style:**

Edit `services/conversational_service.py` system prompts:
```python
self.system_prompt_en = """Your custom prompt here..."""
```

## Chat Session Integration

Greeting exchanges are saved to chat history:
- User message: "Hi"
- Assistant message: Conversational response
- Citations: `[]` (empty)
- Language: detected language
- Duration: response generation time

This ensures conversation continuity when users switch between greetings and real questions.

## Limitations

1. **Length threshold:** Messages > 50 chars are rarely pure greetings
2. **Mixed queries:** "Hi, question here?" triggers KB search (intentional)
3. **Language detection first:** Requires language detection before greeting check
4. **No context:** Greeting responses don't reference previous conversation

## Future Enhancements

- [ ] Context-aware greetings (reference user's previous queries)
- [ ] Personalized greetings (use user name from session)
- [ ] More languages (French, German, etc.)
- [ ] Sentiment detection (frustrated vs happy user)
- [ ] Custom greeting responses per client/tenant

## Monitoring

**Metrics to track:**
- % of queries detected as greetings
- Avg response time: greeting vs KB query
- User satisfaction: greeting responses

**Logs:**
```python
logger.info(f"Greeting detected: type={greeting_type}, query={query}")
```

## Troubleshooting

**Issue:** Real question detected as greeting
- Check query length and pattern matching in `greeting_detector.py`
- Add exception patterns for your use case

**Issue:** Greeting not detected
- Verify pattern exists in detector
- Check language code matches ('en', 'si', 'ta')
- Review query preprocessing (trim, lowercase)

**Issue:** LLM response fails
- Check Bedrock credentials and region
- Verify MODEL_ID exists
- Falls back to pre-defined responses automatically

## Dependencies

```
boto3>=1.26.0  # AWS Bedrock
```

No additional dependencies required.
