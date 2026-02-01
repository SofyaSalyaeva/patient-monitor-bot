import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repository import MedicationRepo, SurveyRepo
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class Summarizer:
    def __init__(self, llm: LLMClient):
        self._llm = llm
        self._days = settings.SUMMARY_DAYS

    async def summarize(self, session: AsyncSession, user_id: int) -> str:
        meds = await MedicationRepo.get_last_n_days(session, user_id, self._days)
        surveys = await SurveyRepo.get_last_n_days(session, user_id, self._days)

        med_block = (
            "\n".join(
                f"  {m.timestamp} | {m.med_names} | {m.status} | назначено на {m.scheduled_time}"
                for m in meds
            )
            or "  (нет записей)"
        )

        survey_block = (
            "\n".join(
                f"  {s.timestamp} | Настроение: {s.mood} | {s.details}" for s in surveys
            )
            or "  (нет записей)"
        )

        prompt = (
            "Ты медицинский аналитик-помощник. Проанализируй данные пациента "
            f"за последние {self._days} дней и составь краткий отчёт.\n\n"
            f"═══ ПРИЁМ ТАБЛЕТОК ═══\n{med_block}\n\n"
            f"═══ ОПРОСЫ САМОЧУВСТВИЯ ═══\n{survey_block}\n\n"
            "Структура отчёта:\n"
            "1. Статистика приёма таблеток (% выполнения, пропуски).\n"
            "2. Динамика настроения.\n"
            "3. Краткие выводы и рекомендации.\n\n"
            "Кратко, по-русски, профессиональный тон. Без диагнозов."
        )
        try:
            return await self._llm.call(prompt, max_tokens=1024, temperature=0.3)
        except Exception as exc:
            logger.error("Summarizer error: %s", exc)
            return f"❌ Не удалось сгенерировать отчёт: {exc}"
