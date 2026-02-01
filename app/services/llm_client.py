import asyncio
import logging

import openai

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin async wrapper around the OpenAI-compatible Yandex endpoint."""

    MODEL = "yandexgpt"

    def __init__(self) -> None:
        self._folder = settings.YANDEX_CLOUD_FOLDER
        self._client = openai.OpenAI(
            api_key=settings.YANDEX_CLOUD_API_KEY,
            project=self._folder,
            base_url="https://ai.api.cloud.yandex.net/v1",
        )

    def _call_sync(self, prompt: str, max_tokens: int, temperature: float) -> str:
        resp = self._client.chat.completions.create(
            model=f"gpt://{self._folder}/{self.MODEL}",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content

    async def call(
        self, prompt: str, max_tokens: int = 1024, temperature: float = 0.3
    ) -> str:
        """Run the synchronous SDK call in a thread pool to stay non-blocking."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._call_sync, prompt, max_tokens, temperature
        )
