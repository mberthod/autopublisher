import json
import re
from typing import Any, Optional

from loguru import logger
from openai import OpenAI

from app.config import settings


class BaseAgent:
    def __init__(self, client: Optional[OpenAI] = None):
        self._client = client or OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self.model = settings.deepseek_model

    def call(self, system_prompt: str, user_prompt: str) -> str:
        logger.debug(f"LLM call to {self.model}")
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        content = response.choices[0].message.content or ""
        logger.debug(f"LLM response length: {len(content)} chars")
        return content

    @staticmethod
    def extract_json(text: str) -> dict[str, Any]:
        text = text.strip()
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try extracting from ```json ... ``` block
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # Try finding first { ... } in text
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Could not extract JSON from LLM response: {text[:200]}")
