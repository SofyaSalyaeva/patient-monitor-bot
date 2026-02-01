import logging
from datetime import time as dt_time

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.handlers.keyboards import main_menu, mood_keyboard, skip_details_keyboard
from app.handlers.states import MedicationStates, SurveyStates, DetailedSurveyState
from app.db.session import async_session
from app.db.repository import MedicationRepo, SurveyRepo, ScheduleRepo

logger = logging.getLogger(__name__)
router = Router()


_scheduler = None
_summarizer = None


def set_services(scheduler, summarizer):
    global _scheduler, _summarizer
    _scheduler = scheduler
    _summarizer = summarizer


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я помощник для контроля состояния здоровья.\n\n"
        "Можно использовать кнопки ниже или просто написать текстом, например:\n"
        "«поставь напоминание выпить магний в 8 вечера».\n\n"
        "Выберите действие:",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "menu_set_reminder")
async def menu_set_reminder(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "💊 Введите название(я) таблеток через запятую.\n"
        "(например: Аспирин, Витамин D, Пробиотик)",
    )
    await state.set_state(MedicationStates.WAITING_NAMES)


@router.message(MedicationStates.WAITING_NAMES)
async def process_names(message: Message, state: FSMContext):
    names = [n.strip() for n in message.text.split(",") if n.strip()]
    if not names:
        await message.answer("❌ Ничего не введено. Попробуйте снова.")
        return
    await state.set_data({"med_names": names})
    await message.answer(
        f"✅ Таблетки: {', '.join(names)}\n\n"
        "🕐 Введите время(я) приёма через запятую.\n"
        "Формат: HH:MM  (например: 08:00, 13:00, 21:00)",
    )
    await state.set_state(MedicationStates.WAITING_TIMES)


@router.message(MedicationStates.WAITING_TIMES)
async def process_times(message: Message, state: FSMContext):
    times, errors = _parse_times(message.text)
    if errors:
        await message.answer(
            f"❌ Не удалось распознать: {', '.join(errors)}.\n"
            "Формат: HH:MM, через запятую.",
        )
        return
    if not times:
        await message.answer("❌ Ничего не введено. Попробуйте снова.")
        return

    data = await state.get_data()
    med_names: list[str] = data.get("med_names", [])

    _scheduler.set_schedule(message.from_user.id, times, med_names)
    async with async_session() as session:
        await ScheduleRepo.save(session, message.from_user.id, times, med_names)

    await message.answer(
        f"✅ Настроено!\n"
        f"💊 Таблетки: {', '.join(med_names)}\n"
        f"🕐 Времена:  {', '.join(t.strftime('%H:%M') for t in times)}",
        reply_markup=main_menu(),
    )
    await state.clear()


@router.callback_query(F.data == "menu_show_schedule")
async def menu_show_schedule(callback: CallbackQuery):
    await callback.answer()
    sched = _scheduler.get_schedule(callback.from_user.id)
    await callback.message.answer(_format_schedule(sched), reply_markup=main_menu())


@router.callback_query(F.data == "menu_cancel_reminder")
async def menu_cancel_reminder(callback: CallbackQuery):
    await callback.answer()
    sched = _scheduler.get_schedule(callback.from_user.id)
    if sched.get("times"):
        _scheduler.clear_schedule(callback.from_user.id)
        async with async_session() as session:
            await ScheduleRepo.delete(session, callback.from_user.id)
        await callback.message.answer(
            "🗑️ Все напоминания удалены.", reply_markup=main_menu()
        )
    else:
        await callback.message.answer(
            "📭 Напоминаний пока нет.", reply_markup=main_menu()
        )


@router.callback_query(F.data.startswith("med_taken:"))
async def med_taken(callback: CallbackQuery):
    scheduled = callback.data.split(":")[1]
    user = callback.from_user
    names_str = _scheduler.med_names_str(user.id)
    async with async_session() as session:
        await MedicationRepo.log(
            session, user.id, user.username or "unknown", names_str, "Выпил", scheduled
        )
    await callback.answer("Записано ✅")
    await callback.message.edit_text(
        f"💊 {scheduled} — ✅ {names_str} выпил(а). Зафиксировано."
    )


@router.callback_query(F.data.startswith("med_skipped:"))
async def med_skipped(callback: CallbackQuery):
    scheduled = callback.data.split(":")[1]
    user = callback.from_user
    names_str = _scheduler.med_names_str(user.id)
    async with async_session() as session:
        await MedicationRepo.log(
            session,
            user.id,
            user.username or "unknown",
            names_str,
            "Пропустил",
            scheduled,
        )
    await callback.answer("Записано ❌")
    await callback.message.edit_text(
        f"💊 {scheduled} — ❌ {names_str} пропущен(а). Зафиксировано."
    )


@router.callback_query(F.data == "menu_quick_survey")
async def menu_quick_survey(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        "📋 Как вы себя чувствуете?", reply_markup=mood_keyboard()
    )


@router.callback_query(F.data.startswith("mood:"))
async def mood_selected(callback: CallbackQuery, state: FSMContext):
    mood = callback.data.split(":", 1)[1]
    await state.set_data({"mood": mood})
    await callback.answer()
    await callback.message.answer(
        f"Вы выбрали: {mood}\n\nДобавьте подробности или нажмите «Пропустить».",
        reply_markup=skip_details_keyboard(),
    )
    await state.set_state(SurveyStates.WAITING_DETAILS)


@router.callback_query(F.data == "mood_skip")
async def mood_skip(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    mood = data.get("mood", "—")
    user = callback.from_user
    async with async_session() as session:
        await SurveyRepo.log(session, user.id, user.username or "unknown", mood, "—")
    await callback.answer("Записано ✅")
    await callback.message.answer(
        "✅ Результат опроса сохранён.", reply_markup=main_menu()
    )
    await state.clear()


@router.message(SurveyStates.WAITING_DETAILS)
async def survey_details_text(message: Message, state: FSMContext):
    data = await state.get_data()
    mood = data.get("mood", "—")
    user = message.from_user
    async with async_session() as session:
        await SurveyRepo.log(
            session, user.id, user.username or "unknown", mood, message.text
        )
    await message.answer("✅ Результат опроса сохранён.", reply_markup=main_menu())
    await state.clear()


@router.callback_query(F.data == "menu_detail_survey")
async def menu_detail_survey(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "📝 Расскажите подробно о своём состоянии.\n(любой длины, затем отправьте.)",
    )
    await state.set_state(DetailedSurveyState.WAITING_TEXT)


@router.message(DetailedSurveyState.WAITING_TEXT)
async def detailed_survey_text(message: Message, state: FSMContext):
    user = message.from_user
    async with async_session() as session:
        await SurveyRepo.log(
            session,
            user.id,
            user.username or "unknown",
            "Развёрнутый ответ",
            message.text,
        )
    await message.answer("✅ Развёрнутый опрос сохранён.", reply_markup=main_menu())
    await state.clear()


@router.callback_query(F.data == "menu_summarize")
async def menu_summarize(callback: CallbackQuery):
    await callback.answer()
    msg = await callback.message.answer("⏳ Генерирую отчёт, подождите...")
    async with async_session() as session:
        report = await _summarizer.summarize(session, callback.from_user.id)
    await msg.edit_text(
        f"📊 Отчёт за последние 30 дней:\n\n{report}", reply_markup=main_menu()
    )


def _parse_times(raw: str) -> tuple[list[dt_time], list[str]]:
    times, errors = [], []
    for part in raw.split(","):
        part = part.strip()
        try:
            h, m = map(int, part.split(":"))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
            times.append(dt_time(h, m))
        except (ValueError, AttributeError):
            errors.append(part)
    return times, errors


def _format_schedule(sched: dict) -> str:
    times = sched.get("times", [])
    names = sched.get("med_names", [])
    if times:
        return (
            f"📅 Расписание:\n"
            f"💊 Таблетки: {', '.join(names) if names else 'не указаны'}\n"
            f"🕐 Времена:  {', '.join(t.strftime('%H:%M') for t in times)}"
        )
    return "📅 Напоминания ещё не настроены.\nНажмите «💊 Настроить напоминания»."
