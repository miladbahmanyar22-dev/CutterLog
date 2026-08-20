# ================================================== 
# FILE: core/settings_manager.py 
# ================================================== 
import json
import shutil
from pathlib import Path
from config import APP_DATA_DIR, DB_PATH
from database.models import Base
from database.db_manager import db

SETTINGS_FILE = APP_DATA_DIR / "settings.json"

DEFAULT_CLIENT_MESSAGE_TEMPLATE = """سلام {couple_names} عزیز 🌸
امیدواریم حالتون عالی باشه.
پروژه تدوین مراسم شما در حال حاضر در وضعیت «{workflow_status}» قرار دارد.

🎬 پیشرفت کلیپ‌ها: {progress_pct}٪
📅 تاریخ مراسم: {event_date}

در صورت داشتن هرگونه سوال در خدمت شما هستیم.
با احترام، {editor_name} - {studio_name}"""

DEFAULT_SETTINGS = {
    # وضعیت راه‌اندازی اولیه
    "is_first_run": True,

    # ۱. عمومی
    "editor_name": "",
    "alert_days_before_deadline": 5,
    "auto_archive_delivered_days": 7,
    "auto_open_folder": True,
    
    # ۲. پیام‌رسانی
    "client_message_template": DEFAULT_CLIENT_MESSAGE_TEMPLATE,

    # ۳. پروژه‌ها و پکیج‌های پیش‌فرض
    "custom_clips": [
        "فیلم کامل مراسم (Long Cut)",
        "کلیپ روز مراسم (Same Day Edit)",
        "تیزر اینستاگرام (۱ دقیقه‌ای)",
        "کلیپ فرمالیته / کویر / شمال",
        "کلیپ حاضرین / مهمان‌ها",
        "پشت صحنه (Backstage)",
        "کلیپ رقص تکی عروس / دو نفره",
        "تایم‌لپس و هوایی (Drone/FPV)"
    ],
    "packages": {
        "پکیج کامل VIP": ["فیلم کامل مراسم (Long Cut)", "کلیپ روز مراسم (Same Day Edit)", "تیزر اینستاگرام (۱ دقیقه‌ای)", "کلیپ فرمالیته / کویر / شمال", "کلیپ رقص تکی عروس / دو نفره"],
        "پکیج اقتصادی": ["فیلم کامل مراسم (Long Cut)", "تیزر اینستاگرام (۱ دقیقه‌ای)"]
    },

    # ۴. مالی و برندینگ (خام و خالی)
    "quick_amounts": {
        "اقتصادی": 10000000,
        "استاندارد": 15000000,
        "کامل VIP": 20000000
    },
    "studio_name": "",
    "phone": "",
    "card_number": "",
    "iban": "",
    "invoice_footer_note": "کلیه حقوق مادی و معنوی راش‌ها تا زمان تسویه کامل متعلق به استودیو می‌باشد.",
    "studio_logo_path": "",
    "studio_signature_path": "",

    # ۵. ایمنی و مسیرها
    "default_drive_path": "",
    "music_vault_path": "",
    "copy_audio_to_vault": True
}


class SettingsManager:
    @staticmethod
    def load_settings() -> dict:
        if not SETTINGS_FILE.exists():
            SettingsManager.save_settings(DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS.copy()
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in DEFAULT_SETTINGS.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            return DEFAULT_SETTINGS.copy()

    @staticmethod
    def save_settings(settings_dict: dict) -> bool:
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings_dict, f, ensure_ascii=False, indent=4)
            return True
        except Exception:
            return False

    @staticmethod
    def backup_database(destination_path: str) -> bool:
        try:
            shutil.copy2(DB_PATH, destination_path)
            return True
        except Exception:
            return False

    @staticmethod
    def restore_database(source_path: str) -> bool:
        try:
            shutil.copy2(source_path, DB_PATH)
            return True
        except Exception:
            return False

    @staticmethod
    def reset_settings_to_default() -> bool:
        return SettingsManager.save_settings(DEFAULT_SETTINGS)

    @staticmethod
    def wipe_entire_database() -> bool:
        try:
            Base.metadata.drop_all(bind=db.engine)
            Base.metadata.create_all(bind=db.engine)
            return True
        except Exception:
            return False