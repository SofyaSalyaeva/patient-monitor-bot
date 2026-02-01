from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Single base for all ORM models."""


class Medication(Base):
    __tablename__ = "medication"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String, nullable=False)
    med_names = Column(String, nullable=False)
    status = Column(String, nullable=False)
    scheduled_time = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


class Survey(Base):
    __tablename__ = "survey"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String, nullable=False)
    mood = Column(String, nullable=False)
    details = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


class Schedule(Base):
    __tablename__ = "schedules"

    user_id = Column(Integer, primary_key=True)
    times_json = Column(String, nullable=False)
    med_names_json = Column(String, nullable=False, default="[]")
