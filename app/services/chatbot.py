import logging

from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_FALLBACK_MSG = "Привет! Я здесь, если тебе нужна поддержка. 😊"


class ChatBot:
    def __init__(self, llm: LLMClient):
        self._llm = llm

    async def respond(self, text: str) -> str:
        prompt = (
            "Ты дружелюбный чат-помощник медицинского бота в Telegram. "
            "Поддержи пользователя, ответь на вопросы о здоровье в общем смысле. "
            "НЕ ставишь диагнозов и НЕ назначаешь лечение.\n\n"
            f'Пользователь написал:\n"{text}"\n\n'
            "Ответь кратко (2–4 предложения), по-русски, тёплым тоном. "
            "Если медицинский вопрос, напомни обратиться к врачу.\n"
            "Вернуть только текст ответа."
        )
        try:
            return await self._llm.call(prompt, max_tokens=300, temperature=0.7)
        except Exception as exc:
            logger.error("ChatBot error: %s", exc)
            return _FALLBACK_MSG
