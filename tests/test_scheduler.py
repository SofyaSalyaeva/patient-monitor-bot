import pytest
from datetime import time as dt_time
from unittest.mock import AsyncMock

from app.services.scheduler import ReminderScheduler


def _make_scheduler():
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    sched = ReminderScheduler(bot=bot)
    return sched, bot


class TestReminderSchedulerMemory:
    def test_set_and_get_schedule(self):
        sched, _ = _make_scheduler()
        times = [dt_time(8, 0), dt_time(21, 0)]
        sched.set_schedule(100, times, ["Аспирин"])
        result = sched.get_schedule(100)
        assert result["times"] == times
        assert result["med_names"] == ["Аспирин"]

    def test_get_schedule_unknown_user(self):
        sched, _ = _make_scheduler()
        result = sched.get_schedule(999)
        assert result == {"times": [], "med_names": []}

    def test_clear_schedule(self):
        sched, _ = _make_scheduler()
        sched.set_schedule(100, [dt_time(8, 0)], ["Витамин D"])
        sched.clear_schedule(100)
        assert sched.get_schedule(100) == {"times": [], "med_names": []}

    def test_med_names_str_with_names(self):
        sched, _ = _make_scheduler()
        sched.set_schedule(1, [dt_time(8, 0)], ["Аспирин", "Витамин D"])
        assert sched.med_names_str(1) == "Аспирин, Витамин D"

    def test_med_names_str_without_names(self):
        sched, _ = _make_scheduler()
        sched.set_schedule(1, [dt_time(8, 0)], [])
        assert sched.med_names_str(1) == "таблетки"

    def test_med_names_str_unknown_user(self):
        sched, _ = _make_scheduler()
        assert sched.med_names_str(999) == "таблетки"


@pytest.mark.asyncio
class TestReminderSchedulerSend:
    async def test_sends_message_at_matching_time(self):
        sched, bot = _make_scheduler()
        # set schedule for current minute
        from datetime import datetime

        now = datetime.now()
        target = dt_time(now.hour, now.minute)
        sched.set_schedule(42, [target], ["Магний"])

        # force _sent_today empty
        sched._sent_today.clear()

        await sched._check_and_send()
        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args
        assert "42" in str(call_kwargs) or call_kwargs[1].get("chat_id") == 42

    async def test_does_not_send_twice_same_minute(self):
        sched, bot = _make_scheduler()
        from datetime import datetime

        now = datetime.now()
        target = dt_time(now.hour, now.minute)
        sched.set_schedule(42, [target], ["Магний"])
        sched._sent_today.clear()

        await sched._check_and_send()
        await sched._check_and_send()  # second call
        assert bot.send_message.call_count == 1

    async def test_does_not_send_for_far_future_time(self):
        sched, bot = _make_scheduler()
        # set time far in the future (or past, wrapping)
        sched.set_schedule(42, [dt_time(23, 59)], ["Test"])
        sched._sent_today.clear()

        from datetime import datetime

        now = datetime.now()
        # only skip if current time is NOT 23:58 or 23:59
        if now.hour != 23 or now.minute < 58:
            await sched._check_and_send()
            bot.send_message.assert_not_called()

    async def test_handles_send_exception_gracefully(self):
        sched, bot = _make_scheduler()
        bot.send_message = AsyncMock(side_effect=Exception("Telegram down"))

        from datetime import datetime

        now = datetime.now()
        target = dt_time(now.hour, now.minute)
        sched.set_schedule(42, [target], ["Test"])
        sched._sent_today.clear()

        # should not raise
        await sched._check_and_send()
