"""
Memory Extractor - Extract memorable info from conversations using LLM
"""

import json
import logging
from typing import List, Dict
from openai import OpenAI

from config import Config

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """Analisis conversation ini dan extract maklumat memorable tentang USER.

Return JSON format only:
{{
"should_remember": true/false,
"memories": [
{{
"key": "category_name",
"value": "the_value",
"type": "fact|preference|query",
"confidence": 0.0-1.0,
"reason": "why worth remembering"
}}
]
}}

Rules:
- Extract PERSONAL info (nama, prefs, facts about user)
- ALWAYS extract USER QUERIES/topics they ask about - this is very important!
- If user asks about a topic (e.g., "apa itu nginx?", "explain docker"), ALWAYS mark as type="query"
- Set confidence 0.9 for all query types - user interest is high priority
- Ignore generic greetings and short thanks

Conversation:
{conversation}

JSON:"""


class MemoryExtractor:
    """
    Extract memorable information from conversation using LLM.
    """

    def __init__(self):
        """Initialize extractor with OpenAI client."""
        self.client = OpenAI(
            api_key=Config.OPENROUTER_API_KEY, base_url=Config.OPENROUTER_BASE_URL
        )
        self.model = Config.MODEL
        logger.debug("MemoryExtractor initialized")

    def extract_from_conversation(self, messages: List[Dict]) -> List[Dict]:
        """
        Extract memorable info from recent conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            List of memory dicts: {key, value, type, confidence, reason}
        """
        conversation_parts = []

        for msg in messages[-6:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if content:
                conversation_parts.append(f"{role.upper()}: {content}")

        conversation = "\n\n".join(conversation_parts)

        prompt = EXTRACTION_PROMPT.format(conversation=conversation)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )

            result_text = response.choices[0].message.content

            if not result_text:
                return []

            json_start = result_text.find("{")
            json_end = result_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_text = result_text[json_start:json_end]
                parsed = json.loads(json_text)
            else:
                parsed = json.loads(result_text)

            if not parsed.get("should_remember", False):
                return []

            memories = parsed.get("memories", [])

            valid_memories = [
                m
                for m in memories
                if m.get("confidence", 0) > 0.7 and m.get("key") and m.get("value")
            ]

            logger.info(f"Extracted {len(valid_memories)} memories from conversation")
            return valid_memories

        except Exception as e:
            logger.debug(f"Memory extraction failed: {e}")
            return []
