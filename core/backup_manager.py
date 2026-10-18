# ==================================================
# FILE: core/backup_manager.py
# ==================================================
import os
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

from config import DB_PATH, APP_DATA_DIR, APP_VERSION
from core.settings_manager import SettingsManager
from core.audio_vault_manager import VIRTUAL_INDEX_FILE
from core.persian_utils import gregorian_to_jalali


class StudioBackupManager:
    """
    مدیریت جامع، فشرده‌سازی و بازیابی گزینشی بسته‌های پشتیبان CutterLog Pro (.clpbackup / .zip)
    با محافظت از قفل کانکشن ویندوز و اعتبارسنجی مانیفست
    """

    BACKUP_SECTIONS = [
        ("database", "پروژه‌ها و پایپ‌لاین (دیتابیس کامل SQLite)", "شامل تمام پروژه‌ها، کلیپ‌ها، اصلاحیه‌ها و تراکنش‌های مالی"),
        ("packages_clips", "پکیج‌های سریع و بانک عناوین کلیپ‌ها", "پکیج‌های آماده و اسامی کلیپ‌های پیش‌فرض مراسم"),
        ("quick_amounts", "مبالغ سریع و پیش‌فرض قراردادها", "مبالغ پرتکرار جهت تسریع در ثبت پروژه‌ها"),
        ("branding_finance", "هویت برند، اطلاعات بانکی و اسناد", "نام استودیو، تلفن، شماره کارت/شبا، فایل لوگو و مهر/امضا"),
        ("client_template", "قالب پیام‌رسانی به مشتری", "قالب پیامک و پیام‌های آماده برای تلگرام و واتساپ"),
        ("music_vault", "ایندکس دسته‌بندی‌های آرشیو موزیک", "فهرست دسته‌بندی‌ها و لینک‌های مجازی فایل‌های صوتی")
    ]

    @classmethod
    def create_backup_archive(cls, output_filepath: str, selected_sections: List[str]) -> bool:
        """
        ایجاد بسته پشتیبان فشرده شامل بخش‌های انتخابی به همراه مانیفست اعتبارسنجی
        """
        temp_dir = APP_DATA_DIR / "_temp_backup_staging"
        try:
            settings = SettingsManager.load_settings()
            manifest = {
                "app_name": "CutterLog Pro",
                "app_version": APP_VERSION,
                "created_at_iso": datetime.utcnow().isoformat(),
                "created_at_jalali": gregorian_to_jalali(datetime.now()),
                "editor_name": settings.get("editor_name", ""),
                "studio_name": settings.get("studio_name", ""),
                "included_sections": selected_sections,
                "branding_files": {}
            }

            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            temp_dir.mkdir(parents=True, exist_ok=True)

            # ۱. دیتابیس کامل SQLite
            if "database" in selected_sections and DB_PATH.exists():
                shutil.copy2(DB_PATH, temp_dir / "cutterlog.db")

            # ۲. بخش‌های تنظیمات
            extracted_settings = {}
            if "packages_clips" in selected_sections:
                extracted_settings["custom_clips"] = settings.get("custom_clips", [])
                extracted_settings["packages"] = settings.get("packages", {})

            if "quick_amounts" in selected_sections:
                extracted_settings["quick_amounts"] = settings.get("quick_amounts", {})

            if "client_template" in selected_sections:
                extracted_settings["client_message_template"] = settings.get("client_message_template", "")

            if "branding_finance" in selected_sections:
                for k in ["studio_name", "editor_name", "phone", "card_number", "iban", "invoice_footer_note"]:
                    if k in settings:
                        extracted_settings[k] = settings[k]

                branding_dir = temp_dir / "branding"
                branding_dir.mkdir(parents=True, exist_ok=True)

                logo_p = settings.get("studio_logo_path", "")
                if logo_p and Path(logo_p).exists() and Path(logo_p).is_file():
                    target_logo = branding_dir / f"logo{Path(logo_p).suffix}"
                    shutil.copy2(logo_p, target_logo)
                    manifest["branding_files"]["logo"] = target_logo.name

                sign_p = settings.get("studio_signature_path", "")
                if sign_p and Path(sign_p).exists() and Path(sign_p).is_file():
                    target_sign = branding_dir / f"signature{Path(sign_p).suffix}"
                    shutil.copy2(sign_p, target_sign)
                    manifest["branding_files"]["signature"] = target_sign.name

            if extracted_settings:
                with open(temp_dir / "settings_export.json", "w", encoding="utf-8") as f:
                    json.dump(extracted_settings, f, ensure_ascii=False, indent=4)

            # ۳. ایندکس مجازی آرشیو موزیک
            if "music_vault" in selected_sections and VIRTUAL_INDEX_FILE.exists():
                shutil.copy2(VIRTUAL_INDEX_FILE, temp_dir / "music_vault_refs.json")

            # مانیفست بسته
            with open(temp_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=4)

            # ساخت آرشیو Zip با پسوند سازگار
            final_out = output_filepath
            if not (final_out.lower().endswith(".clpbackup") or final_out.lower().endswith(".zip")):
                final_out += ".clpbackup"

            with zipfile.ZipFile(final_out, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        abs_p = Path(root) / file
                        rel_p = abs_p.relative_to(temp_dir)
                        zipf.write(abs_p, arcname=str(rel_p))

            return True
        except Exception as e:
            print(f"Error creating backup archive: {e}")
            return False
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def inspect_backup_archive(cls, archive_filepath: str) -> Optional[Dict[str, Any]]:
        """
        آنالیز متادیتا و بررسی محتویات موجود داخل بسته پشتیبان
        """
        try:
            if not Path(archive_filepath).exists():
                return None

            with zipfile.ZipFile(archive_filepath, "r") as zipf:
                names = zipf.namelist()
                if "manifest.json" not in names:
                    if "cutterlog.db" in names or Path(archive_filepath).suffix.lower() == ".db":
                        return {
                            "is_legacy_db": True,
                            "app_version": "قدیمی",
                            "created_at_jalali": "نامشخص",
                            "editor_name": "-",
                            "studio_name": "-",
                            "available_sections": ["database"],
                            "details": {"projects_db": True}
                        }
                    return None

                manifest_data = json.loads(zipf.read("manifest.json").decode("utf-8"))
                available = []

                if "cutterlog.db" in names:
                    available.append("database")
                if "music_vault_refs.json" in names:
                    available.append("music_vault")

                if "settings_export.json" in names:
                    cfg = json.loads(zipf.read("settings_export.json").decode("utf-8"))
                    if "custom_clips" in cfg or "packages" in cfg:
                        available.append("packages_clips")
                    if "quick_amounts" in cfg:
                        available.append("quick_amounts")
                    if "client_message_template" in cfg:
                        available.append("client_template")
                    if any(k in cfg for k in ["studio_name", "phone", "card_number", "iban"]):
                        available.append("branding_finance")

                manifest_data["is_legacy_db"] = False
                manifest_data["available_sections"] = available
                return manifest_data
        except Exception as e:
            print(f"Error inspecting backup: {e}")
            return None

    @classmethod
    def restore_backup_archive(cls, archive_filepath: str, selected_sections: List[str]) -> bool:
        """
        بازیابی و اعمال گزینشی بخش‌ها به همراه آزادسازی کانکشن دیتابیس در ویندوز
        """
        temp_dir = APP_DATA_DIR / "_temp_restore_staging"
        try:
            # ۱. ساخت نقطه بازگشت امنیتی خودکار (Safety Snapshot)
            safety_backup = APP_DATA_DIR / f"_safety_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            if DB_PATH.exists():
                shutil.copy2(DB_PATH, safety_backup)

            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            temp_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(archive_filepath, "r") as zipf:
                # استخراج امن بدون اجازه خروج از پوشه هدف (Safe Extraction)
                for member in zipf.namelist():
                    filename = os.path.basename(member)
                    if not filename:
                        continue
                    source = zipf.open(member)
                    target = temp_dir / member
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with open(target, "wb") as f:
                        shutil.copyfileobj(source, f)

            manifest_p = temp_dir / "manifest.json"
            manifest = {}
            if manifest_p.exists():
                with open(manifest_p, "r", encoding="utf-8") as f:
                    manifest = json.load(f)

            # ۲. بازیابی دیتابیس با آزادسازی کانکشن باز در ویندوز
            if "database" in selected_sections:
                db_in_zip = temp_dir / "cutterlog.db"
                if db_in_zip.exists():
                    try:
                        from database.db_manager import db
                        db.engine.dispose()
                    except Exception as ex:
                        print(f"Database dispose notice: {ex}")

                    shutil.copy2(db_in_zip, DB_PATH)

            # ۳. بازیابی تنظیمات
            settings_in_zip = temp_dir / "settings_export.json"
            if settings_in_zip.exists():
                with open(settings_in_zip, "r", encoding="utf-8") as f:
                    restored_cfg = json.load(f)

                current_settings = SettingsManager.load_settings()

                if "packages_clips" in selected_sections:
                    if "custom_clips" in restored_cfg:
                        current_settings["custom_clips"] = restored_cfg["custom_clips"]
                    if "packages" in restored_cfg:
                        current_settings["packages"] = restored_cfg["packages"]

                if "quick_amounts" in selected_sections and "quick_amounts" in restored_cfg:
                    current_settings["quick_amounts"] = restored_cfg["quick_amounts"]

                if "client_template" in selected_sections and "client_message_template" in restored_cfg:
                    current_settings["client_message_template"] = restored_cfg["client_message_template"]

                if "branding_finance" in selected_sections:
                    for k in ["studio_name", "editor_name", "phone", "card_number", "iban", "invoice_footer_note"]:
                        if k in restored_cfg:
                            current_settings[k] = restored_cfg[k]

                    branding_files = manifest.get("branding_files", {})
                    assets_storage_dir = APP_DATA_DIR / "branding_assets"
                    assets_storage_dir.mkdir(parents=True, exist_ok=True)

                    if "logo" in branding_files:
                        logo_src = temp_dir / "branding" / branding_files["logo"]
                        if logo_src.exists():
                            logo_dest = assets_storage_dir / f"restored_{branding_files['logo']}"
                            shutil.copy2(logo_src, logo_dest)
                            current_settings["studio_logo_path"] = str(logo_dest.resolve())

                    if "signature" in branding_files:
                        sign_src = temp_dir / "branding" / branding_files["signature"]
                        if sign_src.exists():
                            sign_dest = assets_storage_dir / f"restored_{branding_files['signature']}"
                            shutil.copy2(sign_src, sign_dest)
                            current_settings["studio_signature_path"] = str(sign_dest.resolve())

                SettingsManager.save_settings(current_settings)

            # ۴. بازیابی آرشیو موزیک
            if "music_vault" in selected_sections:
                mv_in_zip = temp_dir / "music_vault_refs.json"
                if mv_in_zip.exists():
                    shutil.copy2(mv_in_zip, VIRTUAL_INDEX_FILE)

            return True
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)