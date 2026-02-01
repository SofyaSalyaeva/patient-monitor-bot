import asyncio
import json
import logging
from datetime import datetime, time as dt_time

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.db.repository import ScheduleRepo
from app.db.session import async_session

logger = logging.getLogger(__name__)


class ReminderScheduler:
    def __init__(self, bot: Bot):
        self._bot = bot
        # {user_id: {"times": [dt_time, ...], "med_names": [str, ...]}}
        self._schedules: dict[int, dict] = {}
        # {user_id: set of "HH:MM" already sent today}
        self._sent_today: dict[int, set[str]] = {}

    async def load_from_db(self) -> None:
        async with async_session() as session:
            rows = await ScheduleRepo.get_all(session)
        for row in rows:
            times_str = json.loads(row.times_json)
            self._schedules[row.user_id] = {
                "times": [
                    dt_time(int(t.split(":")[0]), int(t.split(":")[1]))
                    for t in times_str
                ],
                "med_names": json.loads(row.med_names_json),
            }
        logger.info("Loaded %d schedules from DB", len(self._schedules))

    def set_schedule(
        self, user_id: int, times: list[dt_time], med_names: list[str]
    ) -> None:
        self._schedules[user_id] = {"times": times, "med_names": med_names}
        self._sent_today.setdefault(user_id, set())

    def clear_schedule(self, user_id: int) -> None:
        self._schedules.pop(user_id, None)
        self._sent_today.pop(user_id, None)

    def get_schedule(self, user_id: int) -> dict:
        return self._schedules.get(user_id, {"times": [], "med_names": []})

    def med_names_str(self, user_id: int) -> str:
        names = self.get_schedule(user_id).get("med_names", [])
        return ", ".join(names) if names else "таблетки"

    async def run_loop(self) -> None:
        while True:
            await self._check_and_send()
            await asyncio.sleep(60)

    @staticmethod
    def _make_keyboard(scheduled_str: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Выпил", callback_data=f"med_taken:{scheduled_str}"
                    ),
                    InlineKeyboardButton(
                        text="❌ Пропустил",
                        callback_data=f"med_skipped:{scheduled_str}",
                    ),
                ]
            ]
        )

    async def _check_and_send(self) -> None:
        now = datetime.now()
        for user_id, data in list(self._schedules.items()):
            sent = self._sent_today.setdefault(user_id, set())
            names_str = self.med_names_str(user_id)
            for t in data["times"]:
                key = t.strftime("%H:%M")
                delta = (now.hour * 60 + now.minute) - (t.hour * 60 + t.minute)
                if delta in (0, 1) and key not in sent:
                    sent.add(key)
                    try:
                        await self._bot.send_message(
                            chat_id=user_id,
                            text=f"💊 Напоминание в {key}: выпьите {names_str}!",
                            reply_markup=self._make_keyboard(key),
                        )
                    except Exception as exc:
                        logger.warning("Reminder send failed for %d: %s", user_id, exc)

        # reset at midnight
        if now.hour == 0 and now.minute == 0:
            self._sent_today.clear()
