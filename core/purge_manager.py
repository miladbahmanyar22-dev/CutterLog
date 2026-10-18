# ==================================================
# FILE: core/purge_manager.py
# ==================================================
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy import select, delete, func, text

from config import DB_PATH, APP_DATA_DIR, APP_VERSION
from database.db_manager import db
from database.models import (
    Project, Client, Transaction, ProjectClipItem,
    ProjectRevision, ProjectRevisionTask, ProjectEventLog, DriveLocation
)
from time_tracking.models import WorkSession, ActivityLog, DailyGoal
from core.settings_manager import SettingsManager, DEFAULT_SETTINGS
from core.audio_vault_manager import VIRTUAL_INDEX_FILE
from core.signals import global_signals

SNAPSHOTS_DIR = APP_DATA_DIR / "_snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class PurgeManager:
    """
    مدیریت فوق‌حرفه‌ای و ماژولار پاک‌سازی هدفمند داده‌ها
    همراه با ایجاد خودکار Safety Snapshot و آزادسازی اتصالات SQLite در ویندوز
    """

    @classmethod
    def get_live_metrics(cls) -> Dict[str, Any]:
        """محاسبه دقیق و زنده رکوردهای موجود برای نمایش در بج‌های کارت‌ها"""
        metrics = {
            "time_tracking_sessions": 0,
            "activity_logs_count": 0,
            "archived_projects_count": 0,
            "active_projects_count": 0,
            "transactions_count": 0,
            "studios_count": 0,
            "has_branding": False,
            "media_vault_refs_count": 0,
            "last_snapshot_date": cls.get_last_snapshot_info()
        }

        try:
            with db.get_session() as session:
                metrics["time_tracking_sessions"] = session.execute(
                    select(func.count(WorkSession.id))
                ).scalar() or 0

                metrics["activity_logs_count"] = session.execute(
                    select(func.count(ActivityLog.id))
                ).scalar() or 0

                metrics["archived_projects_count"] = session.execute(
                    select(func.count(Project.id)).where(Project.is_archived == True)
                ).scalar() or 0

                metrics["active_projects_count"] = session.execute(
                    select(func.count(Project.id)).where(Project.is_archived == False)
                ).scalar() or 0

                metrics["transactions_count"] = session.execute(
                    select(func.count(Transaction.id))
                ).scalar() or 0

                metrics["studios_count"] = session.execute(
                    select(func.count(Client.id))
                ).scalar() or 0
        except Exception as e:
            print(f"Error fetching live purge metrics: {e}")

        # بررسی تنظیمات و برندینگ
        try:
            settings = SettingsManager.load_settings()
            has_logo = bool(settings.get("studio_logo_path") and Path(settings.get("studio_logo_path")).exists())
            has_sign = bool(settings.get("studio_signature_path") and Path(settings.get("studio_signature_path")).exists())
            has_custom_name = bool(settings.get("studio_name") or settings.get("editor_name"))
            metrics["has_branding"] = has_logo or has_sign or has_custom_name
        except Exception:
            metrics["has_branding"] = False

        # بررسی آرشیو موزیک
        if VIRTUAL_INDEX_FILE.exists():
            try:
                import json
                with open(VIRTUAL_INDEX_FILE, "r", encoding="utf-8") as f:
                    v_data = json.load(f)
                    metrics["media_vault_refs_count"] = sum(len(files) for files in v_data.values())
            except Exception:
                pass

        return metrics

    @classmethod
    def create_safety_snapshot(cls) -> Optional[Path]:
        """تولید اتوماتیک و فشرده نقطه بازگشت اضطراری قبل از اعمال هرگونه حذف"""
        try:
            if not DB_PATH.exists():
                return None

            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            snap_file = SNAPSHOTS_DIR / f"snapshot_{now_str}.clpbackup"

            with zipfile.ZipFile(snap_file, "w", zipfile.ZIP_DEFLATED) as zipf:
                # دیتابیس
                zipf.write(DB_PATH, arcname="cutterlog.db")

                # تنظیمات فعلی
                settings_file = APP_DATA_DIR / "settings.json"
                if settings_file.exists():
                    zipf.write(settings_file, arcname="settings.json")

                # ایندکس موزیک
                if VIRTUAL_INDEX_FILE.exists():
                    zipf.write(VIRTUAL_INDEX_FILE, arcname="music_vault_refs.json")

            # نگهداری حداکثر ۳ اسنپ‌شات آخر برای جلوگیری از اشغال فضای دیسک
            all_snaps = sorted(SNAPSHOTS_DIR.glob("snapshot_*.clpbackup"), key=os.path.getmtime)
            while len(all_snaps) > 3:
                oldest = all_snaps.pop(0)
                try:
                    oldest.unlink()
                except Exception:
                    pass

            return snap_file
        except Exception as e:
            print(f"Error creating safety snapshot: {e}")
            return None

    @classmethod
    def get_last_snapshot_info(cls) -> Optional[Dict[str, Any]]:
        """دریافت مشخصات آخرین اسنپ‌شات اضطراری موجود"""
        try:
            all_snaps = sorted(SNAPSHOTS_DIR.glob("snapshot_*.clpbackup"), key=os.path.getmtime, reverse=True)
            if not all_snaps:
                return None

            latest = all_snaps[0]
            mtime = datetime.fromtimestamp(os.path.getmtime(latest))
            from core.persian_utils import gregorian_to_jalali, to_persian_numbers

            time_str = mtime.strftime("%H:%M")
            date_str = gregorian_to_jalali(mtime)

            return {
                "path": str(latest.resolve()),
                "filename": latest.name,
                "display_time": f"{date_str} - ساعت {to_persian_numbers(time_str)}"
            }
        except Exception:
            return None

    @classmethod
    def restore_last_snapshot(cls) -> bool:
        """بازگردانی بلادرنگ آخرین نقطه بازگشت اضطراری"""
        last_snap = cls.get_last_snapshot_info()
        if not last_snap:
            return False

        snap_path = Path(last_snap["path"])
        if not snap_path.exists():
            return False

        try:
            # ۱. آزادسازی کانکشن دیتابیس
            db.engine.dispose()

            with zipfile.ZipFile(snap_path, "r") as zipf:
                names = zipf.namelist()
                if "cutterlog.db" in names:
                    zipf.extract("cutterlog.db", APP_DATA_DIR / "_temp_restore")
                    shutil.copy2(APP_DATA_DIR / "_temp_restore" / "cutterlog.db", DB_PATH)
                    shutil.rmtree(APP_DATA_DIR / "_temp_restore", ignore_errors=True)

                if "settings.json" in names:
                    zipf.extract("settings.json", APP_DATA_DIR)

                if "music_vault_refs.json" in names:
                    zipf.extract("music_vault_refs.json", APP_DATA_DIR)

            # ارسال سیگنال‌های بروزرسانی سراسری به تمام UI
            global_signals.project_updated.emit(0)
            global_signals.transaction_recorded.emit(0)
            global_signals.settings_updated.emit()
            return True
        except Exception as e:
            print(f"Error restoring snapshot: {e}")
            return False

    @classmethod
    def execute_granular_purge(cls, selected_scopes: List[str]) -> bool:
        """
        اجرای دقیق پاکسازی بر روی دامنه‌های انتخابی کاربر
        با حفظ یکپارچگی ارجاعات و بازنشانی متغیرها
        """
        if not selected_scopes:
            return False

        # ۱. تهیه اسنپ‌شات اضطراری تضمینی
        cls.create_safety_snapshot()

        try:
            with db.get_session() as session:

                # دامنه ۱: لاگ‌ها، جلسات کاری و تایم‌ترکینگ
                if "time_tracking" in selected_scopes:
                    session.execute(delete(ActivityLog))
                    session.execute(delete(WorkSession))
                    session.execute(delete(DailyGoal))
                    # پاک‌سازی کش‌های موقت مانیتورینگ
                    try:
                        from core.media_scanner import THUMBNAIL_CACHE, METADATA_CACHE
                        THUMBNAIL_CACHE.clear()
                        METADATA_CACHE.clear()
                    except Exception:
                        pass

                # دامنه ۲: پروژه‌های آرشیو شده و تسویه‌شده
                if "archived_projects" in selected_scopes:
                    archived_projects = session.scalars(
                        select(Project).where(Project.is_archived == True)
                    ).all()

                    for p in archived_projects:
                        session.delete(p)

                # دامنه ۳: پروژه‌های فعال پایپ‌لاین
                if "active_projects" in selected_scopes:
                    active_projects = session.scalars(
                        select(Project).where(Project.is_archived == False)
                    ).all()

                    for p in active_projects:
                        session.delete(p)

                # دامنه ۴: دفتر کل مالی و تراکنش‌ها
                if "financial_ledger" in selected_scopes:
                    session.execute(delete(Transaction))

                # دامنه ۵: دایرکتوری استودیوها
                if "studios_directory" in selected_scopes:
                    session.execute(text("UPDATE projects SET client_id = NULL"))
                    session.execute(text("UPDATE transactions SET client_id = NULL"))
                    session.execute(delete(Client))

                session.commit()

            # دامنه ۶: برندینگ و تنظیمات هویت استودیو
            if "branding_settings" in selected_scopes:
                settings = SettingsManager.load_settings()
                for key in ["studio_name", "editor_name", "phone", "card_number", "iban",
                            "studio_logo_path", "studio_signature_path", "invoice_footer_note",
                            "client_message_template"]:
                    if key in DEFAULT_SETTINGS:
                        settings[key] = DEFAULT_SETTINGS[key]
                    else:
                        settings[key] = ""

                # پاک‌سازی فایل‌های فیزیکی لوگو و امضای بازگردانی‌شده
                branding_dir = APP_DATA_DIR / "branding_assets"
                if branding_dir.exists():
                    shutil.rmtree(branding_dir, ignore_errors=True)

                SettingsManager.save_settings(settings)

            # دامنه ۷: ایندکس مجازی آرشیو موزیک
            if "media_vault" in selected_scopes:
                if VIRTUAL_INDEX_FILE.exists():
                    try:
                        VIRTUAL_INDEX_FILE.unlink()
                    except Exception:
                        pass

            # انتشار سیگنال‌های سراسری
            global_signals.project_deleted.emit(0)
            global_signals.project_updated.emit(0)
            global_signals.transaction_recorded.emit(0)
            global_signals.settings_updated.emit()
            return True

        except Exception as e:
            print(f"Error during granular purge: {e}")
            return False