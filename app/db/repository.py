import json
from datetime import datetime, timedelta, time as dt_time

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Medication, Survey, Schedule


class MedicationRepo:
    """All queries touching the `medication` table."""

    @staticmethod
    async def log(
        session: AsyncSession,
        user_id: int,
        username: str,
        med_names: str,
        status: str,
        scheduled_time: str,
    ) -> None:
        session.add(
            Medication(
                user_id=user_id,
                username=username,
                med_names=med_names,
                status=status,
                scheduled_time=scheduled_time,
                timestamp=datetime.utcnow(),
            )
        )
        await session.commit()

    @staticmethod
    async def get_last_n_days(
        session: AsyncSession, user_id: int, days: int
    ) -> list[Medication]:
        since = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(Medication)
            .where(Medication.user_id == user_id, Medication.timestamp >= since)
            .order_by(Medication.timestamp)
        )
        return list(result.scalars())


class SurveyRepo:
    """All queries touching the `survey` table."""

    @staticmethod
    async def log(
        session: AsyncSession,
        user_id: int,
        username: str,
        mood: str,
        details: str,
    ) -> None:
        session.add(
            Survey(
                user_id=user_id,
                username=username,
                mood=mood,
                details=details,
                timestamp=datetime.utcnow(),
            )
        )
        await session.commit()

    @staticmethod
    async def get_last_n_days(
        session: AsyncSession, user_id: int, days: int
    ) -> list[Survey]:
        since = datetime.utcnow() - timedelta(days=days)
        result = await session.execute(
            select(Survey)
            .where(Survey.user_id == user_id, Survey.timestamp >= since)
            .order_by(Survey.timestamp)
        )
        return list(result.scalars())


class ScheduleRepo:
    """All queries touching the `schedules` table."""

    @staticmethod
    async def save(
        session: AsyncSession, user_id: int, times: list[dt_time], med_names: list[str]
    ) -> None:
        existing = await session.execute(
            select(Schedule).where(Schedule.user_id == user_id)
        )
        row = existing.scalar_one_or_none()
        times_json = json.dumps([t.strftime("%H:%M") for t in times])
        names_json = json.dumps(med_names)
        if row:
            row.times_json = times_json
            row.med_names_json = names_json
        else:
            session.add(
                Schedule(
                    user_id=user_id, times_json=times_json, med_names_json=names_json
                )
            )
        await session.commit()

    @staticmethod
    async def delete(session: AsyncSession, user_id: int) -> None:
        await session.execute(delete(Schedule).where(Schedule.user_id == user_id))
        await session.commit()

    @staticmethod
    async def get(session: AsyncSession, user_id: int) -> Schedule | None:
        result = await session.execute(
            select(Schedule).where(Schedule.user_id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all(session: AsyncSession) -> list[Schedule]:
        result = await session.execute(select(Schedule))
        return list(result.scalars())
