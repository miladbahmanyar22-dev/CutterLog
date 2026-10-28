# ==================================================
# FILE: core/nle_messenger_helper.py
# ==================================================
import os
import re
import webbrowser
from pathlib import Path
from PySide6.QtGui import QGuiApplication, QDesktopServices
from PySide6.QtCore import QUrl
from core.persian_utils import to_persian_numbers, gregorian_to_jalali, clean_studio_display_name


class NleLauncherHelper:
    """اجرای مستقیم فایل‌های پروژه‌های تدوین در سیستم‌عامل"""

    @staticmethod
    def launch_project(file_path: str) -> tuple[bool, str]:
        if not file_path:
            return False, "مسیر فایل پروژه مشخص نشده است."
        
        p = Path(file_path)
        if not p.exists():
            return False, f"فایل پروژه در مسیر یافت نشد:\n{file_path}"
        
        try:
            os.startfile(str(p))
            return True, "پروژه تدوین اجرا شد."
        except Exception as e:
            return False, f"خطا در اجرای فایل تدوین: {str(e)}"


class ClientMessengerHelper:
    """
    تولید پیام داینامیک و مدیریت ارتباط با پیام‌رسان‌ها
    """

    @staticmethod
    def _format_telegram_link(telegram_input: str) -> str:
        """تبدیل خودکار آیدی تلگرام به لینک استاندارد"""
        if not telegram_input or not telegram_input.strip():
            return ""
        
        raw = telegram_input.strip()
        username = re.sub(r'^(https?://t\.me/|@)', '', raw).strip()
        
        if not username:
            return ""
            
        link = f"https://t.me/{username}"
        return f"\nارتباط مستقیم با واحد تدوین در تلگرام:\n📲 {link}\n"

    @classmethod
    def launch_messenger_app(cls, app_type: str, recipient: str = "") -> bool:
        """
        اجرای مستقیم اپلیکیشن‌های پیام‌رسان یا باز کردن پروتکل وب آن‌ها
        """
        app_type = app_type.lower().strip()
        
        if app_type in ["telegram", "tg"]:
            if recipient:
                clean_rec = re.sub(r'^(https?://t\.me/|@)', '', recipient).strip()
                url = QUrl(f"tg://resolve?domain={clean_rec}")
                if not QDesktopServices.openUrl(url):
                    webbrowser.open(f"https://t.me/{clean_rec}")
            else:
                url = QUrl("tg://open")
                if not QDesktopServices.openUrl(url):
                    webbrowser.open("https://web.telegram.org")
            return True

        elif app_type in ["whatsapp", "wa"]:
            if recipient:
                clean_phone = re.sub(r'[^0-9+]', '', recipient)
                url = QUrl(f"whatsapp://send?phone={clean_phone}")
                if not QDesktopServices.openUrl(url):
                    webbrowser.open(f"https://web.whatsapp.com/send?phone={clean_phone}")
            else:
                url = QUrl("whatsapp://")
                if not QDesktopServices.openUrl(url):
                    webbrowser.open("https://web.whatsapp.com")
            return True

        return False

    @classmethod
    def generate_client_message(cls, project_data: dict, custom_template: str = None) -> str:
        """
        جایگزینی متغیرهای داینامیک بر اساس اطلاعات پروژه همراه با موعد تحویل تقریبی
        """
        couple = project_data.get("couple_names") or project_data.get("title") or "مشتری گرامی"
        
        raw_client = project_data.get("client_name") or ""
        studio = clean_studio_display_name(raw_client) if raw_client else "استودیو"

        # استخراج و تبدیل تاریخ مراسم
        ev_date = project_data.get("event_date")
        date_str = gregorian_to_jalali(ev_date) if ev_date else "ثبت‌نشده"

        # استخراج و تبدیل ددلاین تقریبی
        p_deadline = project_data.get("deadline")
        deadline_str = gregorian_to_jalali(p_deadline) if p_deadline else "به‌زودی هماهنگ می‌شود"

        prog_pct = to_persian_numbers(project_data.get("progress_pct", 0))
        status_info = project_data.get("status_info", {})
        status_text = status_info.get("text", "در حال تدوین")

        telegram_handle = project_data.get("telegram_id", "")
        telegram_section = cls._format_telegram_link(telegram_handle)

        template = custom_template
        if not template or not template.strip():
            template = (
                "سلام {couple_names} عزیز 🌸\n"
                "امیدواریم حالتون عالی باشه.\n\n"
                "روند تدوین فیلم مراسم شما رسماً در استودیو {studio_name} آغاز شد.\n\n"
                "🎬 وضعیت پروژه: {workflow_status}\n"
                "📅 تاریخ مراسم: {event_date}\n"
                "⏳ موعد تقریبی تحویل نسخه اولیه: {approx_deadline}\n\n"
                "🎵 طراحی ریتم و انتخاب موسیقی:\n"
                "موسیقی در فیلم مراسم، بر اساس انرژی هر پلان، حس واقعی صحنه‌ها و ریتم اختصاصی حرکات دوربین انتخاب و سینک می‌شود تا فیلم حالتی پیوسته، جذاب و ماندگار داشته باشد. به همین دلیل پیشنهاد ما این است که با خیالی آسوده، انتخاب قطعات را به سلیقه تخصصی تیم تدوین بسپارید.\n"
                "با این حال، اگر آهنگ خاطره‌انگیز بسیار خاصی دارید، حداکثر تا ۲۴ ساعت آینده برای ما بفرستید تا در صورت هم‌خوانی با ریتم کلی فیلم، از آن استفاده شود.\n\n"
                "📌 بازبینی و اصلاحات نسخه اولیه:\n"
                "• مهلت بررسی تا ۳ روز کاری پس از تحویل پیش‌نمایش است.\n"
                "• اصلاحات باید دقیق همراه با دقیقه و ثانیه (تایم‌کد) ارسال شوند.\n"
                "• پس از تایید نهایی شما، نسخه اصلی و کامل تقدیم خواهد شد.\n"
                "{telegram_section}"
                "با احترام،\n"
                "تیم تدوین استودیو {studio_name}"
            )

        replacements = {
            "{couple_names}": couple,
            "{studio_name}": studio,
            "{event_date}": to_persian_numbers(date_str),
            "{approx_deadline}": to_persian_numbers(deadline_str),
            "{progress_pct}": str(prog_pct),
            "{status_text}": status_text,
            "{workflow_status}": status_text,
            "{telegram_section}": telegram_section
        }

        final_text = template
        for key, value in replacements.items():
            final_text = final_text.replace(key, str(value))

        final_text = re.sub(r'\n{3,}', '\n\n', final_text).strip()
        return final_text

    @staticmethod
    def copy_message_to_clipboard(text: str) -> bool:
        """کپی کردن مستقیم در کلیپ‌بورد سیستم"""
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            return True
        return False