import logging
from datetime import time as dt_time

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.handlers.keyboards import main_menu, mood_keyboard
from app.db.session import async_session
from app.db.repository import ScheduleRepo, SurveyRepo

logger = logging.getLogger(__name__)
router = Router()

_nlu = None
_chatbot = None
_scheduler = None
_summarizer = None
_bot = None

_pending: dict[int, dict] = {}


def set_services(nlu, chatbot, scheduler, summarizer, bot: Bot):
    global _nlu, _chatbot, _scheduler, _summarizer, _bot
    _nlu, _chatbot, _scheduler, _summarizer, _bot = (
        nlu,
        chatbot,
        scheduler,
        summarizer,
        bot,
    )


@router.message()
async def fallback_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text or ""
    if not text:
        return

    pending = _pending.pop(user_id, None)
    if pending and await _handle_pending(message, pending):
        return

    await _bot.send_chat_action(chat_id=user_id, action="typing")
    nlu_result = await _nlu.understand(text)
    intent = nlu_result.get("intent", "chit_chat")
    medication = nlu_result.get("medication", "")
    times_str = nlu_result.get("times", "")

    logger.info(
        "NLU [user=%d]: intent=%s med=%s times=%s | %.60s",
        user_id,
        intent,
        medication,
        times_str,
        text,
    )

    if intent == "set_reminder":
        await _handle_set_reminder(message, medication, times_str)
    elif intent == "show_schedule":
        await _handle_show_schedule(message)
    elif intent == "cancel_reminder":
        await _handle_cancel_reminder(message)
    elif intent == "quick_survey":
        await message.answer("📋 Как вы себя чувствуете?", reply_markup=mood_keyboard())
    elif intent == "detail_survey":
        await message.answer("📝 Расскажите подробно о состоянии.")
        _pending[user_id] = {"awaiting": "detail_survey_text"}
    elif intent == "summarize":
        msg = await message.answer("⏳ Генерирую отчёт, подождите...")
        async with async_session() as session:
            report = await _summarizer.summarize(session, user_id)
        await msg.edit_text(
            f"📊 Отчёт за последние 30 дней:\n\n{report}", reply_markup=main_menu()
        )
    else:
        response = await _chatbot.respond(text)
        await message.answer(response)


async def _handle_set_reminder(message: Message, medication: str, times_str: str):
    user_id = message.from_user.id
    med_names = (
        [n.strip() for n in medication.split(",") if n.strip()] if medication else []
    )
    times = []
    if times_str:
        for part in times_str.split(","):
            part = part.strip()
            try:
                h, m = map(int, part.split(":"))
                if 0 <= h <= 23 and 0 <= m <= 59:
                    times.append(dt_time(h, m))
            except (ValueError, AttributeError):
                pass

    if med_names and times:
        _scheduler.set_schedule(user_id, times, med_names)
        async with async_session() as session:
            await ScheduleRepo.save(session, user_id, times, med_names)
        await message.answer(
            f"✅ Готово!\n"
            f"💊 Таблетки: {', '.join(med_names)}\n"
            f"🕐 Времена:  {', '.join(t.strftime('%H:%M') for t in times)}",
            reply_markup=main_menu(),
        )
        return

    if med_names and not times:
        await message.answer(
            f"💊 Таблетки: {', '.join(med_names)} — запомнил!\n\n"
            "🕐 Укажите время(я) приёма (HH:MM через запятую).",
        )
        _pending[user_id] = {"med_names": med_names}
        return

    if not med_names and times:
        await message.answer(
            f"🕐 Время: {', '.join(t.strftime('%H:%M') for t in times)} — запомнил!\n\n"
            "💊 Укажите название(я) таблеток через запятую.",
        )
        _pending[user_id] = {"times": times}
        return

    await message.answer(
        "💡 Не удалось извлечь данные. Нажмите кнопку «💊 Настроить напоминания» — "
        "она проведёт вас пошагово.",
        reply_markup=main_menu(),
    )


async def _handle_show_schedule(message: Message):
    sched = _scheduler.get_schedule(message.from_user.id)
    times = sched.get("times", [])
    names = sched.get("med_names", [])
    if times:
        text = (
            f"📅 Расписание:\n"
            f"💊 Таблетки: {', '.join(names) if names else 'не указаны'}\n"
            f"🕐 Времена:  {', '.join(t.strftime('%H:%M') for t in times)}"
        )
    else:
        text = "📅 Напоминания ещё не настроены."
    await message.answer(text, reply_markup=main_menu())


async def _handle_cancel_reminder(message: Message):
    sched = _scheduler.get_schedule(message.from_user.id)
    if sched.get("times"):
        _scheduler.clear_schedule(message.from_user.id)
        async with async_session() as session:
            await ScheduleRepo.delete(session, message.from_user.id)
        await message.answer("🗑️ Все напоминания удалены.", reply_markup=main_menu())
    else:
        await message.answer("📭 Напоминаний пока нет.", reply_markup=main_menu())


async def _handle_pending(message: Message, pending: dict) -> bool:
    user_id = message.from_user.id
    text = message.text or ""

    if pending.get("awaiting") == "detail_survey_text":
        user = message.from_user
        async with async_session() as session:
            await SurveyRepo.log(
                session, user.id, user.username or "unknown", "Развёрнутый ответ", text
            )
        await message.answer("✅ Развёрнутый опрос сохранён.", reply_markup=main_menu())
        return True

    if "med_names" in pending and "times" not in pending:
        times = []
        errors = []
        for part in text.split(","):
            part = part.strip()
            try:
                h, m = map(int, part.split(":"))
                if 0 <= h <= 23 and 0 <= m <= 59:
                    times.append(dt_time(h, m))
                else:
                    raise ValueError
            except (ValueError, AttributeError):
                errors.append(part)
        if times and not errors:
            _scheduler.set_schedule(user_id, times, pending["med_names"])
            async with async_session() as session:
                await ScheduleRepo.save(session, user_id, times, pending["med_names"])
            await message.answer(
                f"✅ Настроено!\n💊 {', '.join(pending['med_names'])}\n🕐 {', '.join(t.strftime('%H:%M') for t in times)}",
                reply_markup=main_menu(),
            )
            return True
        await message.answer(
            f"❌ Не удалось распознать: {', '.join(errors) if errors else text}.\nФормат: HH:MM."
        )
        _pending[user_id] = pending
        return True

    if "times" in pending and "med_names" not in pending:
        med_names = [n.strip() for n in text.split(",") if n.strip()]
        if med_names:
            _scheduler.set_schedule(user_id, pending["times"], med_names)
            async with async_session() as session:
                await ScheduleRepo.save(session, user_id, pending["times"], med_names)
            await message.answer(
                f"✅ Настроено!\n💊 {', '.join(med_names)}\n🕐 {', '.join(t.strftime('%H:%M') for t in pending['times'])}",
                reply_markup=main_menu(),
            )
            return True
        await message.answer("❌ Ничего не введено. Укажите названия через запятую.")
        _pending[user_id] = pending
        return True

    return False
