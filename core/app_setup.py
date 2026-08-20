# ==================================================
# FILE: core/app_setup.py
# ==================================================
import sys
from pathlib import Path
from config import APP_DATA_DIR, DB_PATH
from database.db_manager import db
from core.font_manager import FontManager
from core.settings_manager import SettingsManager


def initialize_application() -> bool:
    """
    راه‌اندازی زیرساخت‌های اولیه نرم‌افزار قبل از لود UI:
    - ایجاد دایرکتوری داده‌های برنامه
    - راه‌اندازی دیتابیس و اجرای مایگریشن‌ها
    - بارگذاری فونت‌های سیستم
    - بارگذاری تنظیمات اولیه
    """
    try:
        # ۱. اطمینان از وجود پوشه داده‌ها
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

        # ۲. مقداردهی اولیه پایگاه داده
        db.init_db()

        # ۳. بارگذاری فونت‌ها
        FontManager.load_fonts()

        # ۴. اطمینان از مقداردهی تنظیمات
        SettingsManager.load_settings()

        return True
    except Exception as e:
        print(f"Error during application bootstrap: {e}")
        return False