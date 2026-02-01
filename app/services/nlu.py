import hashlib
import json
import logging
import time as time_module
from datetime import datetime
from typing import Optional

from app.services.llm_client import LLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)

INTENTS_DOC = """
- set_reminder: пользователь хочет поставить напоминание о таблетках.
  Параметры: "medication" (список названий через запятую), "times" (список времён HH:MM).
  Примеры: «поставь напоминание выпить магний в 8 вечера»,
           «напоминай мне про аспирин в 09:00 и 21:00».
- show_schedule: пользователь хочет увидеть текущее расписание.
  Примеры: «покажи расписание», «что у меня настроено».
- cancel_reminder: пользователь хочет отменить напоминания.
  Примеры: «убери напоминания», «отмени все».
- quick_survey: быстрая оценка состояния.
  Примеры: «как я себя чувствую», «быстрый опрос».
- detail_survey: развёрнутый отчёт о состоянии.
  Примеры: «хочу описать состояние подробно».
- summarize: суммаризация / отчёт.
  Примеры: «дай отчёт», «покажи статистику».
- chit_chat: всё остальное.
"""


class NLUCache:
    """In-memory cache with configurable TTL keyed by MD5 of normalised text."""

    def __init__(self, ttl: int | None = None):
        self._ttl = ttl if ttl is not None else settings.NLU_CACHE_TTL
        self._store: dict[str, tuple[dict, float]] = {}

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.md5(text.strip().lower().encode()).hexdigest()

    def get(self, text: str) -> Optional[dict]:
        key = self._key(text)
        entry = self._store.get(key)
        if entry is None:
            return None
        result, expires_at = entry
        if time_module.time() > expires_at:
            del self._store[key]
            return None
        return result

    def set(self, text: str, result: dict) -> None:
        self._store[self._key(text)] = (result, time_module.time() + self._ttl)


_FALLBACK: dict = {"intent": "chit_chat", "medication": "", "times": ""}


class NLU:
    """
    Accepts `llm` via constructor (Dependency Inversion).
    Tests can pass a stub instead of a real LLMClient.
    """

    def __init__(self, llm: LLMClient, cache: NLUCache | None = None):
        self._llm = llm
        self._cache = cache or NLUCache()

    async def understand(self, text: str) -> dict:
        cached = self._cache.get(text)
        if cached:
            logger.info("NLU cache hit: %.50s", text)
            return cached

        prompt = self._build_prompt(text)
        try:
            raw = await self._llm.call(prompt, max_tokens=256, temperature=0.1)
            result = self._parse(raw)
        except Exception as exc:
            logger.warning("NLU error: %s", exc)
            result = _FALLBACK.copy()

        self._cache.set(text, result)
        return result

    @staticmethod
    def _build_prompt(text: str) -> str:
        now_str = datetime.now().strftime("%H:%M")
        return (
            "Ты — модуль понимания команд медицинского чат-бота в Telegram.\n"
            f"Текущее время: {now_str}.\n\n"
            f'Пользователь написал:\n"{text}"\n\n'
            "Определи интент.\n"
            f"Доступные интенты:\n{INTENTS_DOC}\n\n"
            "ВАЖНО:\n"
            "- Вернуть ТОЛЬКО валидный JSON.\n"
            "- «вечер»→20:00, «утро»→08:00, «днём»→13:00, «ночь»→00:00.\n"
            "- «через N часов» → прибавь к текущему.\n"
            "- times всегда HH:MM.\n"
            "- Если medication или times не извлечены — оставь пустой строкой.\n\n"
            "Формат:\n"
            '{"intent":"<name>","medication":"<...>","times":"<...>"}\n'
        )

    @staticmethod
    def _parse(raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        if "intent" not in result:
            return _FALLBACK.copy()
        return result
