from datetime import time as dt_time

from app.handlers.main import _parse_times, _format_schedule
from app.handlers.keyboards import (
    main_menu,
    mood_keyboard,
    skip_details_keyboard,
    MOOD_OPTIONS,
)


class TestParseTimes:
    def test_single_valid_time(self):
        times, errors = _parse_times("08:00")
        assert times == [dt_time(8, 0)]
        assert errors == []

    def test_multiple_valid_times(self):
        times, errors = _parse_times("08:00, 13:00, 21:00")
        assert len(times) == 3
        assert errors == []

    def test_invalid_time_collected_in_errors(self):
        times, errors = _parse_times("08:00, abc, 25:00")
        assert len(times) == 1
        assert "abc" in errors
        assert "25:00" in errors

    def test_empty_string(self):
        times, errors = _parse_times("")
        assert times == []
        assert len(errors) == 1

    def test_boundary_times(self):
        times, errors = _parse_times("00:00, 23:59")
        assert len(times) == 2
        assert errors == []

    def test_out_of_range_hours(self):
        times, errors = _parse_times("24:00")
        assert times == []
        assert "24:00" in errors

    def test_out_of_range_minutes(self):
        times, errors = _parse_times("12:60")
        assert times == []
        assert "12:60" in errors


class TestFormatSchedule:
    def test_with_schedule(self):
        sched = {"times": [dt_time(8, 0), dt_time(21, 0)], "med_names": ["Аспирин"]}
        text = _format_schedule(sched)
        assert "08:00" in text
        assert "21:00" in text
        assert "Аспирин" in text
        assert "📅" in text

    def test_empty_schedule(self):
        text = _format_schedule({"times": [], "med_names": []})
        assert "не настроены" in text

    def test_no_med_names(self):
        sched = {"times": [dt_time(9, 0)], "med_names": []}
        text = _format_schedule(sched)
        assert "не указаны" in text


class TestKeyboards:
    def test_main_menu_has_six_buttons(self):
        kb = main_menu()
        assert len(kb.inline_keyboard) == 6

    def test_mood_keyboard_matches_options(self):
        kb = mood_keyboard()
        assert len(kb.inline_keyboard) == len(MOOD_OPTIONS)
        for row, mood in zip(kb.inline_keyboard, MOOD_OPTIONS):
            assert row[0].text == mood
            assert row[0].callback_data == f"mood:{mood}"

    def test_skip_details_keyboard(self):
        kb = skip_details_keyboard()
        assert len(kb.inline_keyboard) == 1
        assert kb.inline_keyboard[0][0].callback_data == "mood_skip"
