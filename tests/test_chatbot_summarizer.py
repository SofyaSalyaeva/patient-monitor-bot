import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.chatbot import ChatBot
from app.services.summarizer import Summarizer


class StubLLM:
    def __init__(self, response: str = "stub answer"):
        self.response = response

    async def call(self, prompt: str, **kwargs) -> str:
        return self.response


class BrokenLLM:
    async def call(self, *a, **kw):
        raise RuntimeError("boom")


@pytest.mark.asyncio
class TestChatBot:
    async def test_returns_llm_response(self):
        bot = ChatBot(llm=StubLLM("Всё хорошо!"))
        result = await bot.respond("как дела?")
        assert result == "Всё хорошо!"

    async def test_returns_fallback_on_error(self):
        bot = ChatBot(llm=BrokenLLM())
        result = await bot.respond("что-то")
        assert "поддержка" in result


@pytest.mark.asyncio
class TestSummarizer:
    async def test_returns_llm_response(self):
        llm = StubLLM("Отчёт: всё нормально.")
        summarizer = Summarizer(llm=llm)

        session = AsyncMock()
        med_row = MagicMock()
        med_row.timestamp = "2025-01-01 08:00:00"
        med_row.med_names = "Аспирин"
        med_row.status = "Выпил"
        med_row.scheduled_time = "08:00"

        survey_row = MagicMock()
        survey_row.timestamp = "2025-01-01 09:00:00"
        survey_row.mood = "😊 Хорошо"
        survey_row.details = "всё хорошо"

        import app.services.summarizer as mod

        orig_med = mod.MedicationRepo.get_last_n_days
        orig_surv = mod.SurveyRepo.get_last_n_days

        mod.MedicationRepo.get_last_n_days = AsyncMock(return_value=[med_row])
        mod.SurveyRepo.get_last_n_days = AsyncMock(return_value=[survey_row])

        try:
            result = await summarizer.summarize(session, user_id=123)
            assert result == "Отчёт: всё нормально."
        finally:
            mod.MedicationRepo.get_last_n_days = orig_med
            mod.SurveyRepo.get_last_n_days = orig_surv

    async def test_returns_error_string_on_llm_failure(self):
        summarizer = Summarizer(llm=BrokenLLM())
        session = AsyncMock()

        import app.services.summarizer as mod

        orig_med = mod.MedicationRepo.get_last_n_days
        orig_surv = mod.SurveyRepo.get_last_n_days
        mod.MedicationRepo.get_last_n_days = AsyncMock(return_value=[])
        mod.SurveyRepo.get_last_n_days = AsyncMock(return_value=[])
        try:
            result = await summarizer.summarize(session, user_id=999)
            assert "❌" in result
        finally:
            mod.MedicationRepo.get_last_n_days = orig_med
            mod.SurveyRepo.get_last_n_days = orig_surv
