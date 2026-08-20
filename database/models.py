# ==================================================
# FILE: database/models.py
# ==================================================
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, 
    ForeignKey, BigInteger, Text
)
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now():
    """تولید زمان UTC سازگار با نسخه‌های جدید پایتون بدون هشدار"""
    return datetime.now(timezone.utc)


class StageEnum(str, Enum):
    INGEST = "ingest"
    ROUGH_CUT = "rough_cut"
    COLOR_AUDIO = "color_audio"
    FINAL_RENDER = "final_render"
    CLIENT_REVIEW = "client_review"
    DELIVERED = "delivered"


class WorkflowStatusEnum(str, Enum):
    EDITING = "editing"
    READY_FOR_DELIVERY = "ready_for_delivery"
    UNDER_REVIEW = "under_review"
    REVISION_IN_PROGRESS = "revision_in_progress"
    REVISION_DONE = "revision_done"
    ARCHIVED = "archived"


class RevisionStatusEnum(str, Enum):
    NEW_REQUEST = "new_request"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class PaymentTypeEnum(str, Enum):
    PREPAYMENT = "prepayment"
    STAGE_PAYMENT = "stage_payment"
    FINAL_SETTLEMENT = "final_settlement"


class SafeEnum(TypeDecorator):
    impl = String(50)
    cache_ok = True

    def __init__(self, enum_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._enum_type = enum_type

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self._enum_type):
            return value.value
        if isinstance(value, str):
            try:
                return self._enum_type[value].value
            except KeyError:
                return value.lower()
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self._enum_type):
            return value
        
        val_str = str(value).strip()
        for member in self._enum_type:
            if member.value == val_str or member.value == val_str.lower():
                return member
        for member in self._enum_type:
            if member.name == val_str or member.name == val_str.upper():
                return member
        return list(self._enum_type)[0]


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(150), nullable=False)
    company = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    instagram = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    projects = relationship("Project", back_populates="client")
    transactions = relationship("Transaction", back_populates="client")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_number = Column(Integer, unique=True, nullable=True, index=True)
    
    title = Column(String(200), nullable=False)
    couple_names = Column(String(200), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    base_fee = Column(BigInteger, default=0)
    total_fee = Column(BigInteger, default=0)
    
    current_stage = Column(SafeEnum(StageEnum), default=StageEnum.ROUGH_CUT)
    workflow_status = Column(SafeEnum(WorkflowStatusEnum), default=WorkflowStatusEnum.EDITING)
    
    event_date = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, default=False)
    archived_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    nle_project_path = Column(String(500), nullable=True)

    client = relationship("Client", back_populates="projects")
    clips = relationship("ProjectClipItem", back_populates="project", cascade="all, delete-orphan", order_by="ProjectClipItem.id")
    revisions = relationship("ProjectRevision", back_populates="project", cascade="all, delete-orphan", order_by="ProjectRevision.revision_number")
    transactions = relationship("Transaction", back_populates="project", cascade="all, delete-orphan", order_by="Transaction.paid_at.desc()")
    drive_locations = relationship("DriveLocation", back_populates="project", cascade="all, delete-orphan")
    event_logs = relationship("ProjectEventLog", back_populates="project", cascade="all, delete-orphan", order_by="ProjectEventLog.created_at.desc()")


class ProjectEventLog(Base):
    __tablename__ = "project_event_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="event_logs")


class ProjectClipItem(Base):
    __tablename__ = "project_clip_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    clip_name = Column(String(150), nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="clips")


class ProjectRevision(Base):
    __tablename__ = "project_revisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    revision_number = Column(Integer, default=1)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    extra_fee = Column(BigInteger, default=0)
    
    status = Column(SafeEnum(RevisionStatusEnum), default=RevisionStatusEnum.NEW_REQUEST)
    
    requested_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="revisions")
    tasks = relationship("ProjectRevisionTask", back_populates="revision", cascade="all, delete-orphan", order_by="ProjectRevisionTask.id")
    transactions = relationship("Transaction", back_populates="revision")


class ProjectRevisionTask(Base):
    __tablename__ = "project_revision_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    revision_id = Column(Integer, ForeignKey("project_revisions.id"), nullable=False)
    task_text = Column(String(300), nullable=False)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    revision = relationship("ProjectRevision", back_populates="tasks")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    revision_id = Column(Integer, ForeignKey("project_revisions.id", ondelete="SET NULL"), nullable=True)
    amount = Column(BigInteger, nullable=False, default=0)
    tracking_code = Column(String(100), nullable=True)
    
    payment_type = Column(SafeEnum(PaymentTypeEnum), default=PaymentTypeEnum.STAGE_PAYMENT)
    
    notes = Column(String(300), nullable=True)
    paid_at = Column(DateTime, default=utc_now)

    project = relationship("Project", back_populates="transactions")
    client = relationship("Client", back_populates="transactions")
    revision = relationship("ProjectRevision", back_populates="transactions")


class DriveLocation(Base):
    __tablename__ = "drive_locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    drive_label = Column(String(100), nullable=True)
    absolute_path = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=True)

    project = relationship("Project", back_populates="drive_locations")