import json
import logging
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from config import settings

logger = logging.getLogger(__name__)


class OpenAILLMService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"  # fast & cheap

        logger.info(f"OpenAI LLM initialized with model {self.model}")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:

        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        content = response.choices[0].message.content

        return {
            "content": content,
            "stop_reason": "end",
            "usage": response.usage.model_dump() if response.usage else {}
        }

    async def extract_fields(
        self,
        transcript: str,
        fields_schema: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:

        system_prompt = (
            "You are a legal intake assistant. "
            "Extract only clearly stated values. "
            "Return valid JSON only."
        )

        user_message = f"""
Conversation history:
{json.dumps(conversation_history, indent=2)}

Current statement:
{transcript}

Fields schema:
{json.dumps(fields_schema, indent=2)}

Return extracted values as JSON.
"""

        response = await self.generate(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
            temperature=0.1
        )

        content = response["content"]

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("OpenAI extraction JSON parse failed")
            return {}
