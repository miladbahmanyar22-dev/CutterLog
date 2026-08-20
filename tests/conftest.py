# ==================================================
# FILE: tests/conftest.py
# ==================================================
import sys
from pathlib import Path

# اضافه کردن پوشه ریشه پروژه به مسیرهای پایتون
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, Client, Project, ProjectClipItem, StageEnum, WorkflowStatusEnum
from database.db_manager import db


@pytest.fixture(scope="function")
def test_db_session():
    """ایجاد دیتابیس موقت در حافظه (in-memory SQLite) برای هر تست"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    original_session_factory = db.SessionLocal
    db.SessionLocal = TestingSessionLocal
    
    yield session
    
    session.close()
    db.SessionLocal = original_session_factory
    Base.metadata.drop_all(bind=engine)