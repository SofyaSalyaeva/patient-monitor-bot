class TestSettings:
    def test_db_url_is_sqlite(self):
        from app.core.config import settings

        url = settings.db_url
        assert "sqlite+aiosqlite:///" in url
        assert settings.DB_PATH in url

    def test_summary_days_default(self):
        from app.core.config import settings

        assert settings.SUMMARY_DAYS == 30

    def test_nlu_cache_ttl_default(self):
        from app.core.config import settings

        assert settings.NLU_CACHE_TTL == 30


class TestModels:
    def test_medication_has_correct_tablename(self):
        from app.db.models import Medication

        assert Medication.__tablename__ == "medication"

    def test_survey_has_correct_tablename(self):
        from app.db.models import Survey

        assert Survey.__tablename__ == "survey"

    def test_schedule_has_correct_tablename(self):
        from app.db.models import Schedule

        assert Schedule.__tablename__ == "schedules"

    def test_medication_columns_exist(self):
        from app.db.models import Medication

        cols = {c.name for c in Medication.__table__.columns}
        expected = {
            "id",
            "user_id",
            "username",
            "med_names",
            "status",
            "scheduled_time",
            "timestamp",
        }
        assert expected == cols

    def test_survey_columns_exist(self):
        from app.db.models import Survey

        cols = {c.name for c in Survey.__table__.columns}
        expected = {"id", "user_id", "username", "mood", "details", "timestamp"}
        assert expected == cols

    def test_schedule_columns_exist(self):
        from app.db.models import Schedule

        cols = {c.name for c in Schedule.__table__.columns}
        expected = {"user_id", "times_json", "med_names_json"}
        assert expected == cols


class TestNLUIntentsDoc:
    """Verify the intent catalogue is comprehensive."""

    def test_all_intents_documented(self):
        from app.services.nlu import INTENTS_DOC

        required = [
            "set_reminder",
            "show_schedule",
            "cancel_reminder",
            "quick_survey",
            "detail_survey",
            "summarize",
            "chit_chat",
        ]
        for intent in required:
            assert intent in INTENTS_DOC, f"Intent '{intent}' missing from INTENTS_DOC"


class TestSchedulerKeyboard:
    def test_keyboard_has_two_buttons(self):
        from app.services.scheduler import ReminderScheduler

        kb = ReminderScheduler._make_keyboard("08:00")
        assert len(kb.inline_keyboard) == 1
        assert len(kb.inline_keyboard[0]) == 2
        assert "med_taken:08:00" in kb.inline_keyboard[0][0].callback_data
        assert "med_skipped:08:00" in kb.inline_keyboard[0][1].callback_data
