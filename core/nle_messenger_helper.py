# ==================================================
# FILE: core/nle_messenger_helper.py
# ==================================================
import os
import sys
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any

from PySide6.QtGui import QGuiApplication, QDesktopServices
from PySide6.QtCore import QUrl

from config import open_path_in_os
from core.settings_manager import SettingsManager
from core.persian_utils import gregorian_to_jalali, to_persian_numbers


EXTENSION_COLOR_PALETTE = {
    "PRPROJ": {"label": "PR", "color": "#9999FF", "name": "Adobe Premiere Pro"},
    "DRP": {"label": "DRP", "color": "#FF4A4A", "name": "DaVinci Resolve"},
    "AEP": {"label": "AE", "color": "#D291FF", "name": "Adobe After Effects"},
    "FCPXML": {"label": "FCP", "color": "#38BDF8", "name": "Final Cut Pro XML"},
    "XML": {"label": "XML", "color": "#38BDF8", "name": "Timeline XML"},
    "EDL": {"label": "EDL", "color": "#FBBF24", "name": "Edit Decision List"},
    "PSD": {"label": "PSD", "color": "#31A8FF", "name": "Adobe Photoshop"},
    "AI": {"label": "AI", "color": "#FF9A00", "name": "Adobe Illustrator"},
    "C4D": {"label": "C4D", "color": "#0070FF", "name": "Cinema 4D"},
    "SESX": {"label": "AU", "color": "#00E5FF", "name": "Adobe Audition"},
    "CPR": {"label": "CB", "color": "#EF4444", "name": "Cubase Project"},
    "FLM": {"label": "FL", "color": "#FB923C", "name": "FL Studio"},
    "MOV": {"label": "MOV", "color": "#60A5FA", "name": "QuickTime Video"},
    "MP4": {"label": "MP4", "color": "#38BDF8", "name": "MPEG-4 Video"},
    "MXF": {"label": "MXF", "color": "#818CF8", "name": "Material eXchange Format"}
}


class NleLauncherHelper:
    @staticmethod
    def get_file_badge_info(file_path: str) -> Dict[str, str]:
        if not file_path:
            return {
                "ext": "FILE",
                "label": "FILE",
                "color": "#64748B",
                "name": "فایل تدوین متصل نشده",
                "has_file": False
            }
        
        p = Path(file_path)
        ext_clean = p.suffix.replace(".", "").upper() if p.suffix else "FILE"
        has_file = p.exists() and p.is_file()

        if ext_clean in EXTENSION_COLOR_PALETTE:
            info = EXTENSION_COLOR_PALETTE[ext_clean].copy()
            info["ext"] = ext_clean
            info["has_file"] = has_file
            if not has_file:
                info["color"] = "#64748B"
            return info

        short_label = ext_clean[:4] if len(ext_clean) > 4 else ext_clean
        return {
            "ext": ext_clean,
            "label": short_label,
            "color": "#818CF8" if has_file else "#64748B",
            "name": f"فایل {ext_clean}",
            "has_file": has_file
        }

    @staticmethod
    def launch_project(file_path: str) -> Tuple[bool, str]:
        if not file_path:
            return False, "مسیر فایل پروژه مشخص نشده است."
        
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return False, f"فایل پروژه در مسیر مشخص‌شده یافت نشد:\n{file_path}"
        
        # استفاده امن از متد سیستم‌عامل
        if open_path_in_os(str(p.resolve())):
            badge_info = NleLauncherHelper.get_file_badge_info(file_path)
            return True, f"فایل پروژه ({badge_info['label']}) با موفقیت در نرم‌افزار مربوطه باز شد."
        else:
            return False, "خطا در اجرای فایل پروژه."


class ClientMessengerHelper:
    @staticmethod
    def generate_client_message(project_dict: Dict[str, Any]) -> str:
        settings = SettingsManager.load_settings()
        template = settings.get("client_message_template", "")
        
        couple = project_dict.get("couple_names") or project_dict.get("title", "عروس و داماد")
        studio = project_dict.get("client_name", "استودیو")
        editor = settings.get("editor_name", "تدوین‌گر")
        
        event_dt = project_dict.get("event_date")
        event_str = gregorian_to_jalali(event_dt) if event_dt else "-"
        
        status_info = project_dict.get("status_info", {})
        status_label = status_info.get("label", "در حال انجام")
        progress = project_dict.get("progress_pct", 0)

        message = template.replace("{couple_names}", str(couple))\
                          .replace("{studio_name}", str(studio))\
                          .replace("{editor_name}", str(editor))\
                          .replace("{event_date}", to_persian_numbers(str(event_str)))\
                          .replace("{workflow_status}", str(status_label))\
                          .replace("{progress_pct}", to_persian_numbers(str(progress)))
        return message.strip()

    @staticmethod
    def copy_message_to_clipboard(text_content: str) -> bool:
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(text_content)
            return True
        return False

    @staticmethod
    def launch_messenger_app(app_type: str) -> Tuple[bool, str]:
        try:
            uri = "tg://" if app_type == "telegram" else "whatsapp://" if app_type == "whatsapp" else None
            if not uri:
                return False, "نوع پیام‌رسان نامعتبر است."

            url = QUrl(uri)
            # اولویت اول با هندلر دسکتاپ کیوت
            if QDesktopServices.openUrl(url):
                return True, "متن پیام در کلیپ‌بورد کپی شد و پیام‌رسان باز شد."

            if sys.platform == "win32":
                os.startfile(uri)
                return True, "متن پیام در کلیپ‌بورد کپی شد و پیام‌رسان باز شد."
            elif sys.platform == "darwin":
                subprocess.Popen(["open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, "متن پیام در کلیپ‌بورد کپی شد و پیام‌رسان در macOS باز شد."
            else:
                subprocess.Popen(["xdg-open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, "متن پیام در کلیپ‌بورد کپی شد و پیام‌رسان باز شد."

        except Exception as e:
            return False, f"خطا در باز کردن پیام‌رسان: {e}"