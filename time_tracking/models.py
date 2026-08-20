# ==================================================
# FILE: time_tracking/models.py
# ==================================================
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, BigInteger, Text, Float
)
from sqlalchemy.orm import relationship
from database.models import Base, SafeEnum


class SessionStatusEnum(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"


class ActivityStateEnum(str, Enum):
    EDITING = "editing"
    PROCESSING = "processing"
    IDLE = "idle"
    OUTSIDE_EDITING = "outside_editing"


class WorkSession(Base):
    __tablename__ = "work_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    clip_id = Column(Integer, ForeignKey("project_clip_items.id", ondelete="SET NULL"), nullable=True)

    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)

    active_duration = Column(Integer, default=0)    # به ثانیه
    paused_duration = Column(Integer, default=0)    # به ثانیه
    idle_duration = Column(Integer, default=0)      # به ثانیه
    total_duration = Column(Integer, default=0)     # به ثانیه

    activity_type = Column(String(50), default="editing", nullable=True) # رفع محدودیت NOT NULL
    stage_name = Column(String(50), default="Editing")
    status = Column(SafeEnum(SessionStatusEnum), default=SessionStatusEnum.ACTIVE)
    note = Column(Text, nullable=True)
    is_manual = Column(Boolean, default=False)
    is_clip_completed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # ارتباطات
    project = relationship("Project", backref="work_sessions")
    clip = relationship("ProjectClipItem", backref="work_sessions")
    activity_logs = relationship("ActivityLog", back_populates="session", cascade="all, delete-orphan")


class DailyGoal(Base):
    __tablename__ = "daily_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_str = Column(String(20), unique=True, nullable=False)
    target_minutes = Column(Integer, default=480) # پیش‌فرض ۸ ساعت
    updated_at = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("work_sessions.id", ondelete="CASCADE"), nullable=True)

    application_name = Column(String(100), nullable=True)
    window_title = Column(String(250), nullable=True)
    state = Column(SafeEnum(ActivityStateEnum), default=ActivityStateEnum.EDITING)

    cpu_usage = Column(Float, default=0.0)
    gpu_usage = Column(Float, default=0.0)
    ram_usage = Column(Float, default=0.0)

    user_idle_seconds = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("WorkSession", back_populates="activity_logs")