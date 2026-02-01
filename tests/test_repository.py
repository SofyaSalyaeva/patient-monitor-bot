import json
import pytest
from datetime import time as dt_time, datetime, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Medication
from app.db.repository import MedicationRepo, SurveyRepo, ScheduleRepo


@pytest.fixture
async def async_session_fixture():
    """Create an in-memory async SQLite engine + session per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
class TestMedicationRepo:
    async def test_log_and_retrieve(self, async_session_fixture):
        session = async_session_fixture
        await MedicationRepo.log(session, 1, "user1", "Аспирин", "Выпил", "08:00")

        rows = await MedicationRepo.get_last_n_days(session, 1, 1)
        assert len(rows) == 1
        assert rows[0].med_names == "Аспирин"
        assert rows[0].status == "Выпил"

    async def test_get_last_n_days_filters_old(self, async_session_fixture):
        session = async_session_fixture
        old = Medication(
            user_id=1,
            username="u",
            med_names="Old",
            status="Выпил",
            scheduled_time="08:00",
            timestamp=datetime.utcnow() - timedelta(days=60),
        )
        session.add(old)
        await session.commit()

        rows = await MedicationRepo.get_last_n_days(session, 1, 30)
        assert len(rows) == 0

    async def test_get_last_n_days_different_user(self, async_session_fixture):
        session = async_session_fixture
        await MedicationRepo.log(session, 1, "u1", "A", "Выпил", "08:00")
        await MedicationRepo.log(session, 2, "u2", "B", "Выпил", "09:00")

        rows = await MedicationRepo.get_last_n_days(session, 1, 1)
        assert all(r.user_id == 1 for r in rows)


@pytest.mark.asyncio
class TestSurveyRepo:
    async def test_log_and_retrieve(self, async_session_fixture):
        session = async_session_fixture
        await SurveyRepo.log(session, 5, "user5", "😊 Хорошо", "всё отлично")

        rows = await SurveyRepo.get_last_n_days(session, 5, 1)
        assert len(rows) == 1
        assert rows[0].mood == "😊 Хорошо"
        assert rows[0].details == "всё отлично"

    async def test_empty_result(self, async_session_fixture):
        session = async_session_fixture
        rows = await SurveyRepo.get_last_n_days(session, 999, 1)
        assert rows == []


@pytest.mark.asyncio
class TestScheduleRepo:
    async def test_save_new(self, async_session_fixture):
        session = async_session_fixture
        await ScheduleRepo.save(session, 10, [dt_time(8, 0)], ["Магний"])

        row = await ScheduleRepo.get(session, 10)
        assert row is not None
        assert json.loads(row.times_json) == ["08:00"]
        assert json.loads(row.med_names_json) == ["Магний"]

    async def test_save_updates_existing(self, async_session_fixture):
        session = async_session_fixture
        await ScheduleRepo.save(session, 10, [dt_time(8, 0)], ["Магний"])
        await ScheduleRepo.save(session, 10, [dt_time(21, 0)], ["Аспирин"])

        row = await ScheduleRepo.get(session, 10)
        assert json.loads(row.times_json) == ["21:00"]
        assert json.loads(row.med_names_json) == ["Аспирин"]

    async def test_delete(self, async_session_fixture):
        session = async_session_fixture
        await ScheduleRepo.save(session, 10, [dt_time(8, 0)], ["X"])
        await ScheduleRepo.delete(session, 10)

        row = await ScheduleRepo.get(session, 10)
        assert row is None

    async def test_get_returns_none_for_missing(self, async_session_fixture):
        session = async_session_fixture
        row = await ScheduleRepo.get(session, 9999)
        assert row is None

    async def test_get_all(self, async_session_fixture):
        session = async_session_fixture
        await ScheduleRepo.save(session, 1, [dt_time(8, 0)], ["A"])
        await ScheduleRepo.save(session, 2, [dt_time(9, 0)], ["B"])

        rows = await ScheduleRepo.get_all(session)
        assert len(rows) == 2
