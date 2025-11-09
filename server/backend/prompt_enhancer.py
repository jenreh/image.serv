"""Prompt enhancement service for image generation."""

import logging
from typing import Final

from openai import AsyncAzureOpenAI

logger = logging.getLogger(__name__)

# API Configuration
CHAT_MODEL: Final[str] = "gpt-4.1-mini"
API_VERSION: Final[str] = "2025-04-01-preview"


class PromptEnhancer:
    """Encapsulates prompt enhancement logic."""

    def __init__(self, client: AsyncAzureOpenAI):
        self.client = client

    async def enhance(self, prompt: str) -> str:
        """Enhance prompt for better image generation results."""
        logger.debug("Starting prompt enhancement")
        try:
            response = await self.client.chat.completions.create(
                model=CHAT_MODEL,
                stream=False,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an image generation assistant specialized in "
                            "optimizing user prompts. Ensure content "
                            "compliance rules are followed. Do not ask followup "
                            "questions, just generate the optimized prompt."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Enhance this prompt for image generation: {prompt}"
                        ),
                    },
                ],
            )
            result = response.choices[0].message.content.strip()

            if not result:
                logger.warning("Prompt enhancement returned empty, using original")
                return prompt

            logger.info("Prompt enhanced successfully")
            return result
        except Exception as e:
            logger.exception("Prompt enhancement failed: %s", str(e))
            return prompt
