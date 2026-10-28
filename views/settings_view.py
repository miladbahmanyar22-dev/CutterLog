# ================================================== 
# FILE: views/settings_view.py
# ================================================== 
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, 
    QCheckBox, QTextEdit, QStackedWidget, QButtonGroup, 
    QScrollArea, QGridLayout, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QPixmap
from sqlalchemy import select, text

from config import open_path_in_os
from database.db_manager import db
from database.models import Client
from core.settings_manager import SettingsManager
from core.audio_vault_manager import AudioVaultManager, get_vault_root_dir
from core.icon_provider import IconProvider
from core.signals import global_signals
from core.persian_utils import format_toman, normalize_to_english_digits, to_persian_numbers
from widgets.custom_inputs import ModernNumberStepper
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog
from widgets.support_dialog import SupportDeveloperDialog
from widgets.purge_center_widget import PurgeCenterWidget
from views.about_view import AboutView


NEW_DEFAULT_CLIENT_MESSAGE_TEMPLATE = """سلام {couple_names} عزیز 🌸
امیدواریم حالتون عالی باشه.

روند تدوین فیلم مراسم شما رسماً در استودیو {studio_name} آغاز شد.

🎬 وضعیت پروژه: {workflow_status}
📅 تاریخ مراسم: {event_date}
⏳ موعد تقریبی تحویل نسخه اولیه: {approx_deadline}

🎵 طراحی ریتم و انتخاب موسیقی:
موسیقی در فیلم مراسم، بر اساس انرژی هر پلان، حس واقعی صحنه‌ها و ریتم اختصاصی حرکات دوربین انتخاب و سینک می‌شود تا فیلم حالتی پیوسته، جذاب و ماندگار داشته باشد. به همین دلیل پیشنهاد ما این است که با خیالی آسوده، انتخاب قطعات را به سلیقه تخصصی تیم تدوین بسپارید.
با این حال، اگر آهنگ خاطره‌انگیز بسیار خاصی دارید، حداکثر تا ۲۴ ساعت آینده برای ما بفرستید تا در صورت هم‌خوانی با ریتم کلی فیلم، از آن استفاده شود.

📌 بازبینی و اصلاحات نسخه اولیه:
- مهلت بررسی تا ۳ روز کاری پس از تحویل پیش‌نمایش است.
- اصلاحات باید دقیق همراه با دقیقه و ثانیه (تایم‌کد) ارسال شوند.
- پس از تایید نهایی شما، نسخه اصلی و کامل تقدیم خواهد شد.
{telegram_section}
با احترام،
تیم تدوین استودیو {studio_name}"""


class SidebarNavButton(QFrame):
    clicked = Signal()

    def __init__(self, title: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.title_text = title
        self.icon_name = icon_name
        self.is_checked = False

        self.setObjectName("SidebarNavBtnFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 0, 12, 0)
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(16, 16)
        self.lbl_icon.setScaledContents(True)
        self.layout.addWidget(self.lbl_icon)

        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; border: none; background: transparent;")
        self.layout.addWidget(self.lbl_title)

        self.layout.addStretch()
        self.update_state()

    def setChecked(self, checked: bool):
        self.is_checked = checked
        self.update_state()

    def update_state(self):
        if self.is_checked:
            self.setStyleSheet("""
                QFrame#SidebarNavBtnFrame {
                    background-color: #6366F1;
                    border-radius: 7px;
                    border: none;
                }
            """)
            self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; font-weight: 700; color: #FFFFFF; border: none; background: transparent;")
            self.lbl_icon.setPixmap(IconProvider.get_icon(self.icon_name, "#FFFFFF", size=16).pixmap(16, 16))
        else:
            self.setStyleSheet("""
                QFrame#SidebarNavBtnFrame {
                    background-color: transparent;
                    border-radius: 7px;
                    border: none;
                }
                QFrame#SidebarNavBtnFrame:hover {
                    background-color: #161F30;
                }
            """)
            self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; font-weight: 600; color: #94A3B8; border: none; background: transparent;")
            self.lbl_icon.setPixmap(IconProvider.get_icon(self.icon_name, "#94A3B8", size=16).pixmap(16, 16))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.clicked.emit()
            return
        super().mouseReleaseEvent(event)


class SettingsSectionCard(QFrame):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsSectionCardFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 18, 20, 18)
        self.layout.setSpacing(14)

        header_box = QVBoxLayout()
        header_box.setSpacing(2)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        header_box.addWidget(lbl_title)

        if subtitle:
            lbl_sub = QLabel(subtitle)
            lbl_sub.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B; border: none; background: transparent;")
            header_box.addWidget(lbl_sub)

        self.layout.addLayout(header_box)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        self.layout.addWidget(divider)

        self.setStyleSheet("""
            QFrame#SettingsSectionCardFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)

    def add_setting_row(self, row_widget: QWidget):
        self.layout.addWidget(row_widget)

    def add_custom_layout(self, custom_layout):
        self.layout.addLayout(custom_layout)


class SettingRow(QWidget):
    def __init__(self, title: str, description: str = "", control_widget: QWidget = None, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 600; color: #F8FAFC; border: none; background: transparent;")
        info_col.addWidget(lbl_title)

        if description:
            lbl_desc = QLabel(description)
            lbl_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #8F909D; border: none; background: transparent;")
            lbl_desc.setWordWrap(True)
            info_col.addWidget(lbl_desc)

        layout.addLayout(info_col, stretch=1)

        if control_widget:
            layout.addWidget(control_widget, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


class QuickPackageDialog(StudioBaseDialog):
    def __init__(self, package_name: str = "", selected_clips: List[str] = None, available_clips: List[str] = None, parent=None):
        super().__init__(parent=parent)
        self.package_name = package_name
        self.selected_clips = selected_clips or []
        self.available_clips = available_clips or []
        self.clip_checkboxes = []

        self.setFixedSize(480, 480)
        self.init_ui()

    def init_ui(self):
        title = "ویرایش پکیج سریع کلیپ‌ها" if self.package_name else "ساخت پکیج سریع جدید"
        self.build_header(title, "انتخاب گروهی کلیپ‌ها برای ثبت سریع پروژه", icon_name="rings", icon_color="#6366F1")

        self.container_layout.addWidget(QLabel("نام پکیج:"))
        self.input_name = QLineEdit(self.package_name)
        self.input_name.setFixedHeight(36)
        self.input_name.setPlaceholderText("مثال: پکیج کامل VIP، اقتصادی...")
        self.input_name.setStyleSheet("""
            QLineEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-family: 'Vazirmatn';
                font-size: 12px;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.container_layout.addWidget(self.input_name)

        self.container_layout.addWidget(QLabel("انتخاب کلیپ‌های پیش‌فرض:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background-color: #121826; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;")
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(8)

        for clip_name in self.available_clips:
            cb = QCheckBox(clip_name)
            cb.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #F8FAFC; border: none; background: transparent;")
            if clip_name in self.selected_clips:
                cb.setChecked(True)
            c_layout.addWidget(cb)
            self.clip_checkboxes.append((cb, clip_name))

        scroll.setWidget(container)
        self.container_layout.addWidget(scroll, stretch=1)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_save = QPushButton("ذخیره پکیج")
        btn_save.setFixedHeight(36)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                font-weight: 700;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        btn_save.clicked.connect(self._save)
        btn_box.addWidget(btn_save, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _save(self):
        name = self.input_name.text().strip()
        if not name:
            StudioConfirmDialog.ask(self, "خطا در ثبت", "لطفاً یک نام برای پکیج مشخص کنید.", icon_name="alert")
            return
        chosen = [name for cb, name in self.clip_checkboxes if cb.isChecked()]
        if not chosen:
            StudioConfirmDialog.ask(self, "خطا در ثبت", "لطفاً حداقل یک کلیپ انتخاب کنید.", icon_name="alert")
            return
        self.package_name = name
        self.selected_clips = chosen
        self.accept()


class QuickAmountDialog(StudioBaseDialog):
    def __init__(self, amount_name: str = "", amount_val: int = 0, parent=None):
        super().__init__(parent=parent)
        self.amount_name = amount_name
        self.amount_val = amount_val

        self.setFixedSize(420, 310)
        self.init_ui()

    def init_ui(self):
        title = "ویرایش مبلغ سریع" if self.amount_name else "تعریف مبلغ سریع جدید"
        self.build_header(title, "تنظیم مقادیر پیش‌فرض مبالغ قراردادها", icon_name="dollar", icon_color="#10B981")

        self.container_layout.addWidget(QLabel("عنوان مبلغ:"))
        self.input_name = QLineEdit(self.amount_name)
        self.input_name.setFixedHeight(36)
        self.input_name.setPlaceholderText("مثال: پکیج اقتصادی، فرمالیته...")
        self.input_name.setStyleSheet("""
            QLineEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-family: 'Vazirmatn';
                font-size: 12px;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.container_layout.addWidget(self.input_name)

        self.container_layout.addWidget(QLabel("مبلغ به تومان:"))
        self.input_amount = QLineEdit(str(self.amount_val) if self.amount_val > 0 else "")
        self.input_amount.setFixedHeight(36)
        self.input_amount.setPlaceholderText("مثال: 15000000")
        self.input_amount.setStyleSheet("""
            QLineEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-family: 'Vazirmatn';
                font-size: 12px;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.input_amount.textChanged.connect(self._preview)
        self.container_layout.addWidget(self.input_amount)

        self.lbl_preview = QLabel()
        self.lbl_preview.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #10B981; font-weight: 700;")
        self._preview(self.input_amount.text())
        self.container_layout.addWidget(self.lbl_preview)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_save = QPushButton("ذخیره مبلغ")
        btn_save.setFixedHeight(36)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: 700;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_save.clicked.connect(self._save)
        btn_box.addWidget(btn_save, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _preview(self, text_val: str):
        clean = normalize_to_english_digits(text_val)
        if clean.isdigit() and int(clean) > 0:
            self.lbl_preview.setText(f"معادل: {format_toman(int(clean))}")
        else:
            self.lbl_preview.setText("")

    def _save(self):
        name = self.input_name.text().strip()
        clean_amount = normalize_to_english_digits(self.input_amount.text())

        if not name:
            StudioConfirmDialog.ask(self, "خطا در ثبت", "لطفاً یک عنوان برای مبلغ وارد کنید.", icon_name="alert")
            return

        if not clean_amount.isdigit() or int(clean_amount) <= 0:
            StudioConfirmDialog.ask(self, "خطا در ثبت", "لطفاً مبلغ معتبری به تومان وارد کنید.", icon_name="alert")
            return

        self.amount_name = name
        self.amount_val = int(clean_amount)
        self.accept()


class EditStudioDialog(StudioBaseDialog):
    """دیالوگ ویرایش مشخصات و شماره تماس استودیو / آتلیه"""
    def __init__(self, client_id: int, company: str = "", manager: str = "", phone: str = "", parent=None):
        super().__init__(parent=parent)
        self.client_id = client_id
        self.company_val = company or ""
        self.manager_val = manager or ""
        self.phone_val = phone or ""

        self.setFixedWidth(460)
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "ویرایش مشخصات استودیو",
            "اصلاح نام برند، مدیریت و شماره تماس طرف قرارداد",
            icon_name="edit",
            icon_color="#6366F1"
        )

        self.container_layout.addWidget(QLabel("نام برند / آتلیه:*"))
        self.input_company = QLineEdit(self.company_val)
        self.input_company.setFixedHeight(36)
        self.input_company.setPlaceholderText("نام برند استودیو...")
        self.input_company.setStyleSheet("""
            QLineEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-family: 'Vazirmatn';
                font-size: 12px;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.input_company.returnPressed.connect(self._save)
        self.container_layout.addWidget(self.input_company)

        self.container_layout.addWidget(QLabel("نام مدیریت (اختیاری):"))
        self.input_manager = QLineEdit(self.manager_val)
        self.input_manager.setFixedHeight(36)
        self.input_manager.setPlaceholderText("نام و نام خانوادگی مدیر آتلیه...")
        self.input_manager.setStyleSheet("""
            QLineEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-family: 'Vazirmatn';
                font-size: 12px;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.input_manager.returnPressed.connect(self._save)
        self.container_layout.addWidget(self.input_manager)

        self.container_layout.addWidget(QLabel("شماره تماس (اختیاری):"))
        self.input_phone = QLineEdit(self.phone_val)
        self.input_phone.setFixedHeight(36)
        self.input_phone.setPlaceholderText("شماره تماس استودیو...")
        self.input_phone.setStyleSheet("""
            QLineEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-family: 'Vazirmatn';
                font-size: 12px;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.input_phone.returnPressed.connect(self._save)
        self.container_layout.addWidget(self.input_phone)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_save = QPushButton("ذخیره تغییرات")
        btn_save.setFixedHeight(36)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                font-weight: 700;
                border: none;
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        btn_save.clicked.connect(self._save)
        btn_box.addWidget(btn_save, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _save(self):
        comp = self.input_company.text().strip()
        manager = self.input_manager.text().strip()
        raw_phone = self.input_phone.text().strip()
        phone = normalize_to_english_digits(raw_phone) if raw_phone else ""

        if not comp and not manager:
            StudioConfirmDialog.ask(self, "خطا در ثبت", "لطفاً حداقل نام برند یا نام مدیریت را وارد کنید.", icon_name="alert")
            return

        self.company_val = comp or manager
        self.manager_val = manager or comp
        self.phone_val = phone
        self.accept()


class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.settings = SettingsManager.load_settings()
        self.nav_buttons: List[SidebarNavButton] = []
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 20, 28, 20)
        main_layout.setSpacing(16)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(3)
        title = QLabel("مرکز پیکربندی و تنظیمات سیستم")
        title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 22px; font-weight: 800; color: #F8FAFC; border: none;")
        subtitle = QLabel("تغییرات به صورت خودکار و بلادرنگ ذخیره و در پایپ‌لاین تدوین اعمال می‌شوند.")
        subtitle.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; color: #94A3B8; border: none;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)

        # سایدبار تنظیمات
        sidebar_frame = QFrame()
        sidebar_frame.setFixedWidth(230)
        sidebar_frame.setObjectName("SettingsSidebarFrame")
        sidebar_frame.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        sidebar_frame.setStyleSheet("""
            QFrame#SettingsSidebarFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(8, 10, 8, 10)
        sidebar_layout.setSpacing(4)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        categories_data = [
            ("عمومی و پیام‌رسانی", "folder", 0),
            ("پکیج‌ها، کلیپ‌ها و استودیوها", "rings", 1),
            ("مالی، مبالغ و برندینگ", "dollar", 2),
            ("ایمنی، مسیرها و بکاپ", "save", 3),
            ("مرکز بازنشانی و پاکسازی", "trash", 4),
            ("درباره نرم‌افزار", "info", 5),
        ]

        for title_text, icon_name, idx in categories_data:
            btn = SidebarNavButton(title_text, icon_name, sidebar_frame)
            btn.clicked.connect(lambda p_idx=idx: self._switch_category(p_idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        btn_donate = QPushButton("☕ حمایت از توسعه دهنده")
        btn_donate.setFixedHeight(38)
        btn_donate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_donate.setToolTip("حمایت مالی و خرید یک فنجان قهوه برای سازنده نرم‌افزار")
        btn_donate.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(245, 158, 11, 0.12);
                color: #FBBF24;
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 8px;
                font-weight: 800;
                font-size: 12px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #F59E0B;
                color: #000000;
                border-color: #F59E0B;
            }
        """)
        btn_donate.clicked.connect(self._open_support_dialog)
        sidebar_layout.addWidget(btn_donate)

        body_layout.addWidget(sidebar_frame)

        self.pages_stack = QStackedWidget()
        self.pages_stack.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.pages_stack.addWidget(self._build_general_tab())
        self.pages_stack.addWidget(self._build_packages_studios_tab())
        self.pages_stack.addWidget(self._build_finance_branding_tab())
        self.pages_stack.addWidget(self._build_security_data_tab())
        self.pages_stack.addWidget(self._build_reset_danger_tab())
        self.pages_stack.addWidget(AboutView(self))
        body_layout.addWidget(self.pages_stack, stretch=1)

        self._switch_category(0)
        main_layout.addLayout(body_layout, stretch=1)

    def _open_support_dialog(self):
        diag = SupportDeveloperDialog(self.window())
        diag.exec()

    def _switch_category(self, index: int):
        self.pages_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        if index == 4 and hasattr(self, "purge_center") and self.purge_center:
            self.purge_center.refresh_metrics()

    def _persist_settings(self):
        SettingsManager.save_settings(self.settings)
        try:
            from core.project_controller import ProjectController
            ProjectController.check_and_process_auto_archive_delivered()
        except Exception:
            pass
        global_signals.settings_updated.emit()

    def _build_general_tab(self) -> QWidget:
        scroll = self._create_scrollable_container()
        container = scroll.widget()
        layout = container.layout()

        card = SettingsSectionCard("تنظیمات محیط کاری و پایپ‌لاین تدوین", "پیکربندی هویت تدوین‌گر ارشد، هشدارهای ددلاین و اتوماسیون آرشیو")

        self.input_editor = QLineEdit(self.settings.get("editor_name", ""))
        self.input_editor.setFixedHeight(36)
        self.input_editor.setFixedWidth(260)
        self.input_editor.setPlaceholderText("نام تدوین‌گر...")
        self.input_editor.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        self.input_editor.textChanged.connect(self._on_editor_name_changed)
        card.add_setting_row(SettingRow("نام تدوین‌گر ارشد / مسئول پروژه:", "این عنوان در پیش‌فاکتورها و پیام‌های ارسالی به استودیو و مشتری درج می‌شود.", self.input_editor))

        self.stepper_deadline = ModernNumberStepper(
            min_val=1, max_val=30,
            initial_val=self.settings.get("alert_days_before_deadline", 5),
            unit="روز مانده"
        )
        self.stepper_deadline.valueChanged.connect(self._on_deadline_stepper_changed)
        card.add_setting_row(SettingRow("آستانه هشدار نزدیک شدن به ددلاین:", "کارت پروژه‌هایی که به این بازه برسند با نشان هشدار متمایز می‌شوند.", self.stepper_deadline))

        self.stepper_auto_archive = ModernNumberStepper(
            min_val=0, max_val=30,
            initial_val=self.settings.get("auto_archive_delivered_days", 7),
            unit="روز پس از تحویل",
            zero_text="غیرفعال (دستی)"
        )
        self.stepper_auto_archive.valueChanged.connect(self._on_auto_archive_stepper_changed)
        card.add_setting_row(SettingRow("انتقال خودکار به آرشیو پس از تحویل:", "در صورت عدم ارسال اصلاحیه در این بازه، پروژه به بخش آرشیو منتقل می‌شود.", self.stepper_auto_archive))

        self.chk_auto_open = QCheckBox("فعال")
        self.chk_auto_open.setChecked(self.settings.get("auto_open_folder", True))
        self.chk_auto_open.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #F8FAFC; border: none;")
        self.chk_auto_open.toggled.connect(self._on_auto_open_toggled)
        card.add_setting_row(SettingRow("باز شدن خودکار پوشه هارد در سیستم‌عامل:", "هنگام ثبت پروژه جدید، مسیر راش‌ها بلافاصله در فایل‌منیجر باز می‌شود.", self.chk_auto_open))

        layout.addWidget(card)

        card_msg = SettingsSectionCard(
            "قالب پیام‌رسانی سریع به مشتری (Client Message Template)", 
            "تنظیم متن آماده برای ارسال به عروس و داماد در تلگرام و واتساپ"
        )

        self.txt_client_template = QTextEdit()
        self.txt_client_template.setFixedHeight(220)
        
        current_tpl = self.settings.get("client_message_template", "")
        if not current_tpl or not current_tpl.strip():
            current_tpl = NEW_DEFAULT_CLIENT_MESSAGE_TEMPLATE
            self.settings["client_message_template"] = NEW_DEFAULT_CLIENT_MESSAGE_TEMPLATE

        self.txt_client_template.setPlainText(current_tpl)
        self.txt_client_template.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 10px; font-size: 12px; color: #F8FAFC; line-height: 1.6;")
        self.txt_client_template.textChanged.connect(self._on_client_template_changed)

        tag_row = QHBoxLayout()
        tag_row.setSpacing(6)
        tags = [
            ("{couple_names}", "نام زوجین"),
            ("{studio_name}", "نام استودیو"),
            ("{event_date}", "تاریخ مراسم"),
            ("{approx_deadline}", "موعد تقریبی"),
            ("{progress_pct}", "درصد پیشرفت"),
            ("{workflow_status}", "وضعیت پروژه"),
            ("{telegram_section}", "بخش تلگرام")
        ]
        for tag, desc in tags:
            btn_tag = QPushButton(f"+ {desc}")
            btn_tag.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_tag.setStyleSheet("background-color: rgba(99, 102, 241, 0.12); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 4px; padding: 2px 6px; font-size: 10.5px;")
            btn_tag.clicked.connect(lambda _, t=tag: self.txt_client_template.insertPlainText(t))
            tag_row.addWidget(btn_tag)
        tag_row.addStretch()

        btn_reset_tpl = QPushButton("بازنشانی به پیش‌فرض جدید")
        btn_reset_tpl.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_tpl.setStyleSheet("background: transparent; color: #F59E0B; border: none; font-size: 11px; font-weight: bold;")
        btn_reset_tpl.clicked.connect(self._reset_client_template)
        tag_row.addWidget(btn_reset_tpl)

        card_msg.add_custom_layout(tag_row)
        card_msg.add_setting_row(SettingRow("متن قالب پیام سفارشی:", "این متن هنگام کلیک روی آیکون پیام در کارت پروژه، به صورت خودکار پر و کپی می‌شود.", self.txt_client_template))
        layout.addWidget(card_msg)

        layout.addStretch()
        return scroll

    def _on_editor_name_changed(self, text_val: str):
        self.settings["editor_name"] = text_val.strip()
        self._persist_settings()

    def _on_deadline_stepper_changed(self, val: int):
        self.settings["alert_days_before_deadline"] = val
        self._persist_settings()

    def _on_auto_archive_stepper_changed(self, val: int):
        self.settings["auto_archive_delivered_days"] = val
        self._persist_settings()

    def _on_auto_open_toggled(self, checked: bool):
        self.settings["auto_open_folder"] = checked
        self._persist_settings()

    def _on_client_template_changed(self):
        self.settings["client_message_template"] = self.txt_client_template.toPlainText()
        self._persist_settings()

    def _reset_client_template(self):
        self.txt_client_template.setPlainText(NEW_DEFAULT_CLIENT_MESSAGE_TEMPLATE)
        self.settings["client_message_template"] = NEW_DEFAULT_CLIENT_MESSAGE_TEMPLATE
        self._persist_settings()
        global_signals.show_toast.emit("قالب پیام به متن جدید و استاندارد بازنشانی شد.", "info")

    def _build_packages_studios_tab(self) -> QWidget:
        scroll = self._create_scrollable_container()
        container = scroll.widget()
        layout = container.layout()

        card_pkg = SettingsSectionCard("پکیج‌های سریع کلیپ‌ها (Quick Packages)", "تعریف پکیج‌های آماده جهت انتخاب گروهی کلیپ‌ها در زمان تعریف پروژه")
        btn_add_pkg = QPushButton("+ پکیج جدید")
        btn_add_pkg.setFixedHeight(30)
        btn_add_pkg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_pkg.setStyleSheet("background-color: rgba(99, 102, 241, 0.15); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 6px; padding: 0 12px; font-weight: 700; font-size: 11.5px;")
        btn_add_pkg.clicked.connect(self._create_new_package)
        
        top_row_pkg = QHBoxLayout()
        top_row_pkg.addWidget(QLabel("<span style='color:#94A3B8; font-size:11.5px;'>پکیج‌های فعال برای انتخاب در فرم ثبت پروژه:</span>"))
        top_row_pkg.addStretch()
        top_row_pkg.addWidget(btn_add_pkg)
        card_pkg.add_custom_layout(top_row_pkg)

        self.packages_grid_widget = QWidget()
        self.packages_grid_widget.setStyleSheet("background: transparent; border: none;")
        self.packages_grid = QGridLayout(self.packages_grid_widget)
        self.packages_grid.setContentsMargins(0, 4, 0, 4)
        self.packages_grid.setHorizontalSpacing(8)
        self.packages_grid.setVerticalSpacing(8)
        card_pkg.add_setting_row(self.packages_grid_widget)
        layout.addWidget(card_pkg)

        card_clips = SettingsSectionCard("بانک عناوین کلیپ‌های مراسم", "فهرست کلیپ‌های پیش‌فرض قابل انتخاب برای پروژه‌ها و پکیج‌ها")
        add_clip_box = QHBoxLayout()
        add_clip_box.setSpacing(8)
        self.input_new_clip = QLineEdit()
        self.input_new_clip.setFixedHeight(34)
        self.input_new_clip.setPlaceholderText("عنوان کلیپ جدید (مثال: فرمالیته کویر، تیزر ۱ دقیقه‌ای)...")
        self.input_new_clip.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        self.input_new_clip.returnPressed.connect(self._add_clip)
        add_clip_box.addWidget(self.input_new_clip, stretch=1)

        btn_add_c = QPushButton("افزودن کلیپ")
        btn_add_c.setFixedHeight(34)
        btn_add_c.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_c.setStyleSheet("background-color: #6366F1; color: #FFFFFF; font-weight: bold; border: none; border-radius: 6px; padding: 0 14px; font-size: 12px;")
        btn_add_c.clicked.connect(self._add_clip)
        add_clip_box.addWidget(btn_add_c)
        card_clips.add_custom_layout(add_clip_box)

        self.clips_grid_widget = QWidget()
        self.clips_grid_widget.setStyleSheet("background: transparent; border: none;")
        self.clips_grid = QGridLayout(self.clips_grid_widget)
        self.clips_grid.setContentsMargins(0, 4, 0, 4)
        self.clips_grid.setHorizontalSpacing(6)
        self.clips_grid.setVerticalSpacing(6)
        card_clips.add_setting_row(self.clips_grid_widget)
        layout.addWidget(card_clips)

        # کارت دایرکتوری استودیوها با فیلد شماره تماس تمیز و بدون متن اضافه
        card_studio = SettingsSectionCard("دایرکتوری استودیوها و آتلیه‌ها", "مدیریت آتلیه‌های طرف قرارداد و شماره تماس جهت درج در فاکتورها")
        add_studio_row = QHBoxLayout()
        add_studio_row.setSpacing(8)
        
        self.input_studio_company = QLineEdit()
        self.input_studio_company.setFixedHeight(34)
        self.input_studio_company.setPlaceholderText("نام آتلیه / برند...")
        self.input_studio_company.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        add_studio_row.addWidget(self.input_studio_company, stretch=2)

        self.input_studio_manager = QLineEdit()
        self.input_studio_manager.setFixedHeight(34)
        self.input_studio_manager.setPlaceholderText("نام مدیریت...")
        self.input_studio_manager.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        add_studio_row.addWidget(self.input_studio_manager, stretch=2)

        self.input_studio_phone = QLineEdit()
        self.input_studio_phone.setFixedHeight(34)
        self.input_studio_phone.setPlaceholderText("شماره تماس...")
        self.input_studio_phone.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        add_studio_row.addWidget(self.input_studio_phone, stretch=2)

        btn_add_s = QPushButton("ثبت استودیو")
        btn_add_s.setFixedHeight(34)
        btn_add_s.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_s.setStyleSheet("background-color: #6366F1; color: #FFFFFF; font-weight: bold; border: none; border-radius: 6px; padding: 0 14px; font-size: 12px;")
        btn_add_s.clicked.connect(self._add_studio_to_db)
        add_studio_row.addWidget(btn_add_s)
        card_studio.add_custom_layout(add_studio_row)

        self.studios_grid_widget = QWidget()
        self.studios_grid_widget.setStyleSheet("background: transparent; border: none;")
        self.studios_grid = QGridLayout(self.studios_grid_widget)
        self.studios_grid.setContentsMargins(0, 4, 0, 4)
        self.studios_grid.setHorizontalSpacing(6)
        self.studios_grid.setVerticalSpacing(6)
        card_studio.add_setting_row(self.studios_grid_widget)
        layout.addWidget(card_studio)

        self._refresh_packages_grid()
        self._refresh_clips_grid()
        self._refresh_studios_grid()

        layout.addStretch()
        return scroll

    def _build_finance_branding_tab(self) -> QWidget:
        scroll = self._create_scrollable_container()
        container = scroll.widget()
        layout = container.layout()

        card_quick_amounts = SettingsSectionCard("مبالغ سریع و پرتکرار قراردادها", "مبالغ پیش‌فرض جهت پر کردن سریع فیلد قیمت هنگام ثبت پروژه")
        btn_add_qa = QPushButton("+ مبلغ جدید")
        btn_add_qa.setFixedHeight(30)
        btn_add_qa.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_qa.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 6px; padding: 0 12px; font-weight: 700; font-size: 11.5px;")
        btn_add_qa.clicked.connect(self._create_new_amount)

        top_row_qa = QHBoxLayout()
        top_row_qa.addWidget(QLabel("<span style='color:#94A3B8; font-size:11.5px;'>مبالغ آماده قرارداد به تومان:</span>"))
        top_row_qa.addStretch()
        top_row_qa.addWidget(btn_add_qa)
        card_quick_amounts.add_custom_layout(top_row_qa)

        self.amounts_grid_widget = QWidget()
        self.amounts_grid_widget.setStyleSheet("background: transparent; border: none;")
        self.amounts_grid = QGridLayout(self.amounts_grid_widget)
        self.amounts_grid.setContentsMargins(0, 4, 0, 4)
        self.amounts_grid.setHorizontalSpacing(8)
        self.amounts_grid.setVerticalSpacing(8)
        card_quick_amounts.add_setting_row(self.amounts_grid_widget)
        layout.addWidget(card_quick_amounts)

        card_brand = SettingsSectionCard("اطلاعات استودیو، حساب بانکی و فاکتورها", "مشخصات درج‌شده در فاکتور رسمی، شناسنامه پروژه و پیام‌های واریز")
        
        self.input_studio = QLineEdit(self.settings.get("studio_name", ""))
        self.input_studio.setFixedHeight(36)
        self.input_studio.setFixedWidth(280)
        self.input_studio.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        self.input_studio.textChanged.connect(lambda v: self._update_key("studio_name", v))
        card_brand.add_setting_row(SettingRow("نام برند / استودیوی تدوین:", "عنوان رسمی نمایش‌داده‌شده در سربرگ فاکتورها و شناسنامه‌ها.", self.input_studio))

        self.input_phone = QLineEdit(self.settings.get("phone", ""))
        self.input_phone.setFixedHeight(36)
        self.input_phone.setFixedWidth(280)
        self.input_phone.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        self.input_phone.textChanged.connect(lambda v: self._update_key("phone", v))
        card_brand.add_setting_row(SettingRow("شماره تماس هماهنگی استودیو:", "شماره پشتیبانی جهت درج در فاکتور رسمی و صورت‌حساب‌ها.", self.input_phone))

        self.input_card = QLineEdit(self.settings.get("card_number", ""))
        self.input_card.setFixedHeight(36)
        self.input_card.setFixedWidth(280)
        self.input_card.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        self.input_card.textChanged.connect(lambda v: self._update_key("card_number", v))
        card_brand.add_setting_row(SettingRow("شماره کارت بانکی جهت واریز:", "در پیام‌های یادآوری تسویه و انتهای فاکتور درج می‌گردد.", self.input_card))

        self.input_iban = QLineEdit(self.settings.get("iban", ""))
        self.input_iban.setFixedHeight(36)
        self.input_iban.setFixedWidth(280)
        self.input_iban.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        self.input_iban.textChanged.connect(lambda v: self._update_key("iban", v))
        card_brand.add_setting_row(SettingRow("شماره شبا (IBAN):", "شماره حساب بین‌بانکی جهت تسویه‌های مبالغ بالا.", self.input_iban))

        self.input_invoice_note = QTextEdit()
        self.input_invoice_note.setPlainText(self.settings.get("invoice_footer_note", ""))
        self.input_invoice_note.setFixedHeight(65)
        self.input_invoice_note.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 8px 10px; font-size: 12px; color: #F8FAFC;")
        self.input_invoice_note.textChanged.connect(lambda: self._update_key("invoice_footer_note", self.input_invoice_note.toPlainText()))
        
        note_row = QVBoxLayout()
        note_row.setSpacing(4)
        note_row.addWidget(QLabel("<b style='color:#F8FAFC; font-size:12px;'>متن پاورقی و شرایط حقوقی فاکتورها:</b>"))
        note_row.addWidget(self.input_invoice_note)
        card_brand.add_custom_layout(note_row)

        layout.addWidget(card_brand)

        card_assets = SettingsSectionCard(
            "هویت بصری و اعتبارنامه رسمی (لوگو و امضا)",
            "تصاویر لوگو و مهر/امضای رسمی جهت درج در شناسنامه رسمی و اسناد صادره"
        )

        assets_row = QHBoxLayout()
        assets_row.setSpacing(20)

        # لوگو
        logo_box = QVBoxLayout()
        logo_box.setSpacing(6)
        logo_box.addWidget(QLabel("<b style='color:#F8FAFC; font-size:12px;'>لوگوی رسمی استودیو:</b>"))

        self.lbl_logo_preview = QLabel()
        self.lbl_logo_preview.setFixedSize(110, 110)
        self.lbl_logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo_preview.setStyleSheet("background-color: #161F30; border: 1px dashed rgba(255,255,255,0.15); border-radius: 8px;")
        logo_box.addWidget(self.lbl_logo_preview)

        logo_btn_row = QHBoxLayout()
        logo_btn_row.setSpacing(6)
        btn_upload_logo = QPushButton("انتخاب لوگو...")
        btn_upload_logo.setFixedHeight(30)
        btn_upload_logo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_upload_logo.setStyleSheet("background-color: #6366F1; color: #FFFFFF; font-size: 11px; font-weight: bold; border-radius: 5px; padding: 0 10px;")
        btn_upload_logo.clicked.connect(self._upload_logo)
        logo_btn_row.addWidget(btn_upload_logo)

        btn_del_logo = QPushButton("حذف")
        btn_del_logo.setFixedHeight(30)
        btn_del_logo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_logo.setStyleSheet("background-color: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid rgba(239,68,68,0.3); font-size: 11px; font-weight: bold; border-radius: 5px; padding: 0 8px;")
        btn_del_logo.clicked.connect(self._remove_logo)
        logo_btn_row.addWidget(btn_del_logo)
        logo_box.addLayout(logo_btn_row)

        assets_row.addLayout(logo_box)

        # امضا
        sign_box = QVBoxLayout()
        sign_box.setSpacing(6)
        sign_box.addWidget(QLabel("<b style='color:#F8FAFC; font-size:12px;'>امضا یا مهر دیجیتال:</b>"))

        self.lbl_sign_preview = QLabel()
        self.lbl_sign_preview.setFixedSize(160, 110)
        self.lbl_sign_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sign_preview.setStyleSheet("background-color: #161F30; border: 1px dashed rgba(255,255,255,0.15); border-radius: 8px;")
        sign_box.addWidget(self.lbl_sign_preview)

        sign_btn_row = QHBoxLayout()
        sign_btn_row.setSpacing(6)
        btn_upload_sign = QPushButton("انتخاب امضا...")
        btn_upload_sign.setFixedHeight(30)
        btn_upload_sign.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_upload_sign.setStyleSheet("background-color: #10B981; color: #FFFFFF; font-size: 11px; font-weight: bold; border-radius: 5px; padding: 0 10px;")
        btn_upload_sign.clicked.connect(self._upload_signature)
        sign_btn_row.addWidget(btn_upload_sign)

        btn_del_sign = QPushButton("حذف")
        btn_del_sign.setFixedHeight(30)
        btn_del_sign.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_sign.setStyleSheet("background-color: rgba(239, 68, 68, 0.15); color: #EF4444; border: 1px solid rgba(239,68,68,0.3); font-size: 11px; font-weight: bold; border-radius: 5px; padding: 0 8px;")
        btn_del_sign.clicked.connect(self._remove_signature)
        sign_btn_row.addWidget(btn_del_sign)
        sign_box.addLayout(sign_btn_row)

        assets_row.addLayout(sign_box)
        assets_row.addStretch()

        card_assets.add_custom_layout(assets_row)
        layout.addWidget(card_assets)

        self._refresh_amounts_grid()
        self._refresh_branding_previews()

        layout.addStretch()
        return scroll

    def _update_key(self, key: str, value: str):
        self.settings[key] = value.strip()
        self._persist_settings()

    def _refresh_branding_previews(self):
        logo_path = self.settings.get("studio_logo_path", "")
        if logo_path and Path(logo_path).exists():
            pix = QPixmap(logo_path).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_logo_preview.setPixmap(pix)
        else:
            self.lbl_logo_preview.setText("<span style='color:#64748B; font-size:11px;'>لوگو ثبت نشده</span>")

        sign_path = self.settings.get("studio_signature_path", "")
        if sign_path and Path(sign_path).exists():
            pix = QPixmap(sign_path).scaled(150, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_sign_preview.setPixmap(pix)
        else:
            self.lbl_sign_preview.setText("<span style='color:#64748B; font-size:11px;'>امضا ثبت نشده</span>")

    def _upload_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "انتخاب لوگوی استودیو", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.settings["studio_logo_path"] = path
            self._persist_settings()
            self._refresh_branding_previews()
            global_signals.show_toast.emit("لوگوی استودیو با موفقیت به‌روزرسانی شد.", "success")

    def _remove_logo(self):
        self.settings["studio_logo_path"] = ""
        self._persist_settings()
        self._refresh_branding_previews()
        global_signals.show_toast.emit("لوگوی استودیو حذف گردید.", "info")

    def _upload_signature(self):
        path, _ = QFileDialog.getOpenFileName(self, "انتخاب امضا یا مهر دیجیتال", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if path:
            self.settings["studio_signature_path"] = path
            self._persist_settings()
            self._refresh_branding_previews()
            global_signals.show_toast.emit("مهر/امضای دیجیتال با موفقیت ثبت شد.", "success")

    def _remove_signature(self):
        self.settings["studio_signature_path"] = ""
        self._persist_settings()
        self._refresh_branding_previews()
        global_signals.show_toast.emit("مهر/امضای دیجیتال حذف گردید.", "info")

    def _build_security_data_tab(self) -> QWidget:
        scroll = self._create_scrollable_container()
        container = scroll.widget()
        layout = container.layout()
        layout.setSpacing(12)

        chk_path = IconProvider.get_checkbox_checked_icon_path()

        # ۱. بنر وضعیت سلامت مخزن داده
        health_banner = QFrame()
        health_banner.setFixedHeight(68)
        health_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #091220, stop:0.5 #0F1D32, stop:1 #091220);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 9px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        hb_lay = QHBoxLayout(health_banner)
        hb_lay.setContentsMargins(16, 0, 16, 0)
        hb_lay.setSpacing(12)
        hb_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        hb_icon_frame = QFrame()
        hb_icon_frame.setFixedSize(36, 36)
        hb_icon_frame.setStyleSheet("background-color: rgba(56, 189, 248, 0.14); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 7px;")
        hb_if_lay = QVBoxLayout(hb_icon_frame)
        hb_if_lay.setContentsMargins(0, 0, 0, 0)
        hb_if_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hb_icon = QLabel()
        hb_icon.setPixmap(IconProvider.get_pixmap("shield_check", "#38BDF8", size=17))
        hb_if_lay.addWidget(hb_icon)
        hb_lay.addWidget(hb_icon_frame)

        hb_info = QVBoxLayout()
        hb_info.setSpacing(1)
        hb_info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_hb_title = QLabel("پایش یکپارچگی مسیرها و مخازن ذخیره‌سازی")
        lbl_hb_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #F8FAFC;")
        hb_info.addWidget(lbl_hb_title)

        lbl_hb_sub = QLabel("پیکربندی استانداردهای دسترسی مستقیم NLE، امنیت فایل‌ها و ذخیره‌سازی داده‌های پایپ‌لاین")
        lbl_hb_sub.setStyleSheet("font-size: 10px; color: #94A3B8;")
        hb_info.addWidget(lbl_hb_sub)
        hb_lay.addLayout(hb_info, stretch=1)

        badge_status = QLabel("● سیستم پایدار")
        badge_status.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 10px;
                font-weight: 700;
                color: #38BDF8;
                background-color: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 5px;
                padding: 4px 10px;
            }
        """)
        hb_lay.addWidget(badge_status)
        layout.addWidget(health_banner)

        # ۲. کارت‌های تنظیم مسیرها در گرید منظم
        paths_wrap = QFrame()
        paths_wrap.setStyleSheet("""
            QFrame#PathsWrapFrame {
                background-color: #101625;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }
        """)
        paths_wrap.setObjectName("PathsWrapFrame")
        pw_lay = QVBoxLayout(paths_wrap)
        pw_lay.setContentsMargins(14, 12, 14, 12)
        pw_lay.setSpacing(10)

        lbl_paths_head = QLabel("مسیرهای اصلی پایپ‌لاین و مخازن مدیا:")
        lbl_paths_head.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; font-weight: 800; color: #F8FAFC; background: transparent; border: none;")
        pw_lay.addWidget(lbl_paths_head)

        paths_grid = QGridLayout()
        paths_grid.setSpacing(10)
        paths_grid.setColumnStretch(0, 1)
        paths_grid.setColumnStretch(1, 1)

        # کارت ۱: هارد پیش‌فرض راش‌ها
        card_drive = QFrame()
        card_drive.setFixedHeight(126)
        card_drive.setStyleSheet("""
            QFrame {
                background-color: #121828;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: rgba(99, 102, 241, 0.35);
                background-color: #151D30;
            }
        """)
        cd_lay = QVBoxLayout(card_drive)
        cd_lay.setContentsMargins(12, 10, 12, 10)
        cd_lay.setSpacing(6)

        cd_top = QHBoxLayout()
        cd_top.setSpacing(8)
        lbl_cd_icon = QLabel()
        lbl_cd_icon.setPixmap(IconProvider.get_pixmap("folder", "#818CF8", size=15))
        cd_top.addWidget(lbl_cd_icon)
        lbl_cd_title = QLabel("هارد پیش‌فرض پروژه‌ها و راش‌ها")
        lbl_cd_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        cd_top.addWidget(lbl_cd_title)
        cd_top.addStretch()
        cd_lay.addLayout(cd_top)

        lbl_cd_desc = QLabel("هنگام ثبت پروژه جدید، دیالوگ انتخاب فایل و راش‌ها از این مسیر باز می‌شود.")
        lbl_cd_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 9.5px; color: #8F98A8; border: none; background: transparent;")
        cd_lay.addWidget(lbl_cd_desc)

        cd_bar = QHBoxLayout()
        cd_bar.setSpacing(6)
        self.input_default_drive = QLineEdit(self.settings.get("default_drive_path", ""))
        self.input_default_drive.setFixedHeight(30)
        self.input_default_drive.setReadOnly(True)
        self.input_default_drive.setPlaceholderText("مسیری تعیین نشده...")
        self.input_default_drive.setStyleSheet("font-family: 'Segoe UI', monospace; font-size: 10.5px; background-color: #0E1320; border: 1px solid rgba(255,255,255,0.06); border-radius: 5px; padding: 0 8px; color: #CBD5E1;")
        cd_bar.addWidget(self.input_default_drive, stretch=1)

        btn_browse_drive = QPushButton("انتخاب هارد...")
        btn_browse_drive.setFixedHeight(30)
        btn_browse_drive.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_drive.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 700;
                background-color: rgba(99, 102, 241, 0.15); color: #818CF8;
                border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 5px;
                padding: 0 10px;
            }
            QPushButton:hover { background-color: #6366F1; color: #FFFFFF; }
        """)
        btn_browse_drive.clicked.connect(self._browse_default_drive)
        cd_bar.addWidget(btn_browse_drive)
        cd_lay.addLayout(cd_bar)
        paths_grid.addWidget(card_drive, 0, 0)

        # کارت ۲: مخزن صوتی و آرشیو موزیک
        card_music = QFrame()
        card_music.setFixedHeight(126)
        card_music.setStyleSheet("""
            QFrame {
                background-color: #121828;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: rgba(56, 189, 248, 0.35);
                background-color: #151D30;
            }
        """)
        cm_lay = QVBoxLayout(card_music)
        cm_lay.setContentsMargins(12, 10, 12, 10)
        cm_lay.setSpacing(6)

        cm_top = QHBoxLayout()
        cm_top.setSpacing(8)
        lbl_cm_icon = QLabel()
        lbl_cm_icon.setPixmap(IconProvider.get_pixmap("music", "#38BDF8", size=15))
        cm_top.addWidget(lbl_cm_icon)
        lbl_cm_title = QLabel("پوشه ذخیره‌سازی آرشیو صوتی استودیو")
        lbl_cm_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        cm_top.addWidget(lbl_cm_title)
        cm_top.addStretch()
        cm_lay.addLayout(cm_top)

        lbl_cm_desc = QLabel("مسیر فیزیکی یا مجازی نگهداری فایل‌های صوتی و دسته‌بندی‌های اختصاصی.")
        lbl_cm_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 9.5px; color: #8F98A8; border: none; background: transparent;")
        cm_lay.addWidget(lbl_cm_desc)

        cm_bar = QHBoxLayout()
        cm_bar.setSpacing(6)
        self.input_music_drive = QLineEdit(str(get_vault_root_dir().resolve()))
        self.input_music_drive.setFixedHeight(30)
        self.input_music_drive.setReadOnly(True)
        self.input_music_drive.setStyleSheet("font-family: 'Segoe UI', monospace; font-size: 10.5px; background-color: #0E1320; border: 1px solid rgba(255,255,255,0.06); border-radius: 5px; padding: 0 8px; color: #CBD5E1;")
        cm_bar.addWidget(self.input_music_drive, stretch=1)

        btn_browse_music = QPushButton("انتخاب مسیر...")
        btn_browse_music.setFixedHeight(30)
        btn_browse_music.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_music.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 700;
                background-color: rgba(56, 189, 248, 0.15); color: #38BDF8;
                border: 1px solid rgba(56, 189, 248, 0.35); border-radius: 5px;
                padding: 0 10px;
            }
            QPushButton:hover { background-color: #0284C7; color: #FFFFFF; }
        """)
        btn_browse_music.clicked.connect(self._browse_music_vault_drive)
        cm_bar.addWidget(btn_browse_music)

        btn_open_music = QPushButton("نمایش در فایل‌منیجر ↗")
        btn_open_music.setFixedHeight(30)
        btn_open_music.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_music.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 600;
                background-color: #1A2234; color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 5px;
                padding: 0 8px;
            }
            QPushButton:hover { color: #FFFFFF; background-color: #242E42; }
        """)
        btn_open_music.clicked.connect(lambda: open_path_in_os(self.input_music_drive.text()))
        cm_bar.addWidget(btn_open_music)
        cm_lay.addLayout(cm_bar)
        paths_grid.addWidget(card_music, 0, 1)

        pw_lay.addLayout(paths_grid)

        # سوئیچ حالت کپی فایل‌های صوتی
        copy_mode_card = QFrame()
        copy_mode_card.setStyleSheet(f"""
            QFrame {{
                background-color: #121828;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }}
            QCheckBox {{
                font-family: 'Vazirmatn';
                font-size: 11.5px;
                font-weight: 700;
                color: #F8FAFC;
                spacing: 8px;
                background: transparent;
                border: none;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                background-color: #1E283D;
                border: 1.5px solid rgba(255, 255, 255, 0.22);
                border-radius: 4px;
            }}
            QCheckBox::indicator:hover {{
                border-color: #38BDF8;
                background-color: #242E42;
            }}
            QCheckBox::indicator:checked {{
                background-color: #0284C7;
                border: 1.5px solid #38BDF8;
                image: url("{chk_path}");
            }}
        """)
        cmc_lay = QHBoxLayout(copy_mode_card)
        cmc_lay.setContentsMargins(14, 10, 14, 10)
        cmc_lay.setSpacing(10)

        self.chk_copy_audio = QCheckBox("کپی فیزیکی فایل‌های صوتی در پوشه آرشیو (Physical Copy Mode)")
        self.chk_copy_audio.setChecked(self.settings.get("copy_audio_to_vault", True))
        self.chk_copy_audio.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_copy_audio.toggled.connect(self._on_copy_audio_toggled)
        cmc_lay.addWidget(self.chk_copy_audio)

        lbl_cmc_hint = QLabel("(در صورت خاموش بودن، فایل‌ها کپی نشده و فقط مسیر اصلی به‌صورت مرجع خوانده می‌شود)")
        lbl_cmc_hint.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10px; color: #8F98A8; border: none; background: transparent;")
        cmc_lay.addWidget(lbl_cmc_hint)
        cmc_lay.addStretch()

        pw_lay.addWidget(copy_mode_card)
        layout.addWidget(paths_wrap)

        # ۳. کارت کنسول پشتیبان‌گیری و بازیابی استودیو
        backup_card = QFrame()
        backup_card.setStyleSheet("""
            QFrame#BackupConsoleCardFrame {
                background-color: #101625;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }
        """)
        backup_card.setObjectName("BackupConsoleCardFrame")
        bc_lay = QVBoxLayout(backup_card)
        bc_lay.setContentsMargins(14, 12, 14, 12)
        bc_lay.setSpacing(10)

        bc_top_bar = QHBoxLayout()
        bc_top_bar.setSpacing(8)
        lbl_bc_title = QLabel("کنسول پشتیبان‌گیری جامع استودیو (Disaster Recovery & Backup):")
        lbl_bc_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; font-weight: 800; color: #F8FAFC; background: transparent; border: none;")
        bc_top_bar.addWidget(lbl_bc_title)
        bc_top_bar.addStretch()
        bc_lay.addLayout(bc_top_bar)

        bc_grid = QHBoxLayout()
        bc_grid.setSpacing(10)

        # پنل ۱: استخراج بکاپ جامع
        btn_backup_panel = QFrame()
        btn_backup_panel.setFixedHeight(78)
        btn_backup_panel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_backup_panel.setStyleSheet("""
            QFrame {
                background-color: #121828;
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #162432;
                border-color: #10B981;
            }
        """)
        bb_lay = QHBoxLayout(btn_backup_panel)
        bb_lay.setContentsMargins(14, 10, 14, 10)
        bb_lay.setSpacing(12)
        bb_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        bb_icon = QLabel()
        bb_icon.setPixmap(IconProvider.get_pixmap("save", "#10B981", size=22))
        bb_lay.addWidget(bb_icon)

        bb_text_col = QVBoxLayout()
        bb_text_col.setSpacing(2)
        bb_text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        lbl_bb_t = QLabel("تهیه بسته پشتیبان جامع استودیو (.clpbackup)")
        lbl_bb_t.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; font-weight: 800; color: #FFFFFF; border: none; background: transparent;")
        bb_text_col.addWidget(lbl_bb_t)
        lbl_bb_d = QLabel("بسته‌بندی تفکیک‌شده پروژه‌ها، امور مالی، برندینگ و تنظیمات در قالب یک فایل فشرده")
        lbl_bb_d.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        bb_text_col.addWidget(lbl_bb_d)
        bb_lay.addLayout(bb_text_col, stretch=1)

        btn_backup_panel.mousePressEvent = lambda e: self._backup_db() if e.button() == Qt.MouseButton.LeftButton else None
        bc_grid.addWidget(btn_backup_panel)

        # پنل ۲: بازیابی از بسته پشتیبان
        btn_restore_panel = QFrame()
        btn_restore_panel.setFixedHeight(78)
        btn_restore_panel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_restore_panel.setStyleSheet("""
            QFrame {
                background-color: #121828;
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #242018;
                border-color: #F59E0B;
            }
        """)
        br_lay = QHBoxLayout(btn_restore_panel)
        br_lay.setContentsMargins(14, 10, 14, 10)
        br_lay.setSpacing(12)
        br_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        br_icon = QLabel()
        br_icon.setPixmap(IconProvider.get_pixmap("revision", "#F59E0B", size=22))
        br_lay.addWidget(br_icon)

        br_text_col = QVBoxLayout()
        br_text_col.setSpacing(2)
        br_text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        lbl_br_t = QLabel("بازیابی هوشمند و گزینشی از بسته پشتیبان")
        lbl_br_t.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; font-weight: 800; color: #FFFFFF; border: none; background: transparent;")
        br_text_col.addWidget(lbl_br_t)
        lbl_br_d = QLabel("آنالیز محتوای بسته پشتیبان و انتخاب بخش‌های مدنظر جهت اعمال با پوشش ایمنی کامل")
        lbl_br_d.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10px; color: #94A3B8; border: none; background: transparent;")
        br_text_col.addWidget(lbl_br_d)
        br_lay.addLayout(br_text_col, stretch=1)

        btn_restore_panel.mousePressEvent = lambda e: self._restore_db() if e.button() == Qt.MouseButton.LeftButton else None
        bc_grid.addWidget(btn_restore_panel)

        bc_lay.addLayout(bc_grid)
        layout.addWidget(backup_card)

        layout.addStretch()
        return scroll

    def _on_copy_audio_toggled(self, checked: bool):
        self.settings["copy_audio_to_vault"] = checked
        self._persist_settings()
        msg = "حالت کپی فیزیکی فایل‌های صوتی فعال شد." if checked else "حالت فقط خواندن (Reference Mode) فعال شد؛ از این پس هیچ فایل یا پوشه‌ای روی هارد کپی نمی‌شود."
        global_signals.show_toast.emit(msg, "info")

    def _build_reset_danger_tab(self) -> QWidget:
        scroll = self._create_scrollable_container()
        container = scroll.widget()
        layout = container.layout()

        card = SettingsSectionCard(
            "مرکز پاک‌سازی هوشمند و بازنشانی داده‌ها (Purge & Reset Hub)",
            "مدیریت هدفمند پاک‌سازی کش، آرشیو فصول گذشته و بازنشانی تنظیمات با ضمانت ایمنی کامل"
        )

        self.purge_center = PurgeCenterWidget(self)
        card.add_setting_row(self.purge_center)

        layout.addWidget(card)
        layout.addStretch()
        return scroll

    def _create_scrollable_container(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        container.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        scroll.setWidget(container)
        return scroll

    def _refresh_packages_grid(self):
        while self.packages_grid.count():
            item = self.packages_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        packages = self.settings.get("packages", {})
        if not packages:
            empty = QLabel("هنوز پکیج سریعی ثبت نشده است.")
            empty.setStyleSheet("color: #64748B; font-size: 11.5px; border: none;")
            self.packages_grid.addWidget(empty, 0, 0)
            return

        for idx, (pkg_name, clips) in enumerate(packages.items()):
            chip = QFrame()
            chip.setStyleSheet("""
                QFrame {
                    background-color: #161F30;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                }
                QFrame:hover {
                    border-color: rgba(99, 102, 241, 0.4);
                    background-color: #1A253A;
                }
            """)
            c_lay = QHBoxLayout(chip)
            c_lay.setContentsMargins(10, 6, 8, 6)
            c_lay.setSpacing(6)

            lbl_title = QLabel(f"⚡ <b>{pkg_name}</b>")
            lbl_title.setStyleSheet("font-family: 'Vazirmatn'; color: #F8FAFC; font-size: 11.5px; border: none;")
            c_lay.addWidget(lbl_title, stretch=1)

            lbl_cnt = QLabel(f"{to_persian_numbers(len(clips))} کلیپ")
            lbl_cnt.setStyleSheet("background-color: rgba(99, 102, 241, 0.15); color: #818CF8; border-radius: 4px; padding: 2px 6px; font-size: 10.5px; font-weight: bold; border: none;")
            c_lay.addWidget(lbl_cnt)

            btn_edit = QPushButton("✎")
            btn_edit.setFixedSize(22, 22)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("background: transparent; color: #818CF8; border: none; font-size: 12px; font-weight: bold;")
            btn_edit.clicked.connect(lambda _, n=pkg_name, c=clips: self._edit_package(n, c))
            c_lay.addWidget(btn_edit)

            btn_del = QPushButton("×")
            btn_del.setFixedSize(22, 22)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background: transparent; color: #EF4444; border: none; font-size: 15px; font-weight: bold;")
            btn_del.clicked.connect(lambda _, n=pkg_name: self._delete_package(n))
            c_lay.addWidget(btn_del)

            row = idx // 2
            col = idx % 2
            self.packages_grid.addWidget(chip, row, col)

    def _refresh_clips_grid(self):
        while self.clips_grid.count():
            item = self.clips_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        clips = self.settings.get("custom_clips", [])
        if not clips:
            empty = QLabel("هیچ کلیپی در بانک عناوین وجود ندارد.")
            empty.setStyleSheet("color: #64748B; font-size: 11.5px; border: none;")
            self.clips_grid.addWidget(empty, 0, 0)
            return

        for idx, clip_name in enumerate(clips):
            chip = QFrame()
            chip.setStyleSheet("""
                QFrame {
                    background-color: #161F30;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 6px;
                }
                QFrame:hover { border-color: rgba(99, 102, 241, 0.35); }
            """)
            c_lay = QHBoxLayout(chip)
            c_lay.setContentsMargins(8, 4, 6, 4)
            c_lay.setSpacing(6)

            lbl_txt = QLabel(clip_name)
            lbl_txt.setStyleSheet("font-family: 'Vazirmatn'; color: #F8FAFC; font-size: 11.5px; border: none;")
            c_lay.addWidget(lbl_txt, stretch=1)

            btn_del = QPushButton("×")
            btn_del.setFixedSize(18, 18)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background: transparent; color: #EF4444; border: none; font-size: 13px; font-weight: bold;")
            btn_del.clicked.connect(lambda _, n=clip_name: self._delete_clip_by_name(n))
            c_lay.addWidget(btn_del)

            row = idx // 3
            col = idx % 3
            self.clips_grid.addWidget(chip, row, col)

    def _refresh_studios_grid(self):
        while self.studios_grid.count():
            item = self.studios_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        with db.get_session() as session:
            clients = session.scalars(select(Client).order_by(Client.created_at.desc())).all()

            if not clients:
                empty = QLabel("هنوز استودیویی ثبت نشده است.")
                empty.setStyleSheet("color: #64748B; font-size: 11.5px; border: none;")
                self.studios_grid.addWidget(empty, 0, 0)
                return

            for idx, c in enumerate(clients):
                card = QFrame()
                card.setStyleSheet("""
                    QFrame {
                        background-color: #161F30;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 6px;
                    }
                    QFrame:hover { border-color: rgba(99, 102, 241, 0.4); }
                """)
                c_lay = QHBoxLayout(card)
                c_lay.setContentsMargins(10, 6, 8, 6)
                c_lay.setSpacing(6)

                info_col = QVBoxLayout()
                info_col.setSpacing(1)

                display_name = c.company or c.full_name
                lbl_name = QLabel(f"🏢 <b>{display_name}</b>")
                lbl_name.setStyleSheet("font-family: 'Vazirmatn'; color: #F8FAFC; font-size: 11.5px; border: none;")
                info_col.addWidget(lbl_name)

                sub_details = []
                if c.company and c.full_name and c.company != c.full_name:
                    sub_details.append(f"مدیریت: {c.full_name}")
                if c.phone:
                    sub_details.append(f"تلفن: {to_persian_numbers(c.phone)}")

                if sub_details:
                    lbl_sub = QLabel(" | ".join(sub_details))
                    lbl_sub.setStyleSheet("font-family: 'Vazirmatn'; color: #94A3B8; font-size: 10px; border: none;")
                    info_col.addWidget(lbl_sub)

                c_lay.addLayout(info_col, stretch=1)

                btn_edit = QPushButton("✎")
                btn_edit.setFixedSize(22, 22)
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setToolTip("ویرایش مشخصات و شماره تماس استودیو")
                btn_edit.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #818CF8;
                        border: none;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: rgba(99, 102, 241, 0.18);
                        border-radius: 4px;
                        color: #A5B4FC;
                    }
                """)
                btn_edit.clicked.connect(lambda _, cid=c.id: self._edit_studio_by_id(cid))
                c_lay.addWidget(btn_edit)

                btn_del = QPushButton("×")
                btn_del.setFixedSize(22, 22)
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setToolTip("حذف استودیو")
                btn_del.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #EF4444;
                        border: none;
                        font-size: 15px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: rgba(239, 68, 68, 0.18);
                        border-radius: 4px;
                    }
                """)
                btn_del.clicked.connect(lambda _, cid=c.id: self._delete_studio_by_id(cid))
                c_lay.addWidget(btn_del)

                row = idx // 2
                col = idx % 2
                self.studios_grid.addWidget(card, row, col)

    def _refresh_amounts_grid(self):
        while self.amounts_grid.count():
            item = self.amounts_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        amounts = self.settings.get("quick_amounts", {})
        if not amounts:
            empty = QLabel("هنوز مبلغ سریعی ثبت نشده است.")
            empty.setStyleSheet("color: #64748B; font-size: 11.5px; border: none;")
            self.amounts_grid.addWidget(empty, 0, 0)
            return

        for idx, (name, val) in enumerate(amounts.items()):
            chip = QFrame()
            chip.setStyleSheet("""
                QFrame {
                    background-color: #161F30;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                }
                QFrame:hover {
                    border-color: rgba(16, 185, 129, 0.4);
                    background-color: #1A253A;
                }
            """)
            c_lay = QHBoxLayout(chip)
            c_lay.setContentsMargins(10, 6, 8, 6)
            c_lay.setSpacing(6)

            lbl_title = QLabel(f"💳 <b>{name}</b>: <span style='color:#10B981;'>{format_toman(val)}</span>")
            lbl_title.setStyleSheet("font-family: 'Vazirmatn'; color: #F8FAFC; font-size: 11.5px; border: none;")
            c_lay.addWidget(lbl_title, stretch=1)

            btn_edit = QPushButton("✎")
            btn_edit.setFixedSize(22, 22)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("background: transparent; color: #10B981; border: none; font-size: 12px; font-weight: bold;")
            btn_edit.clicked.connect(lambda _, n=name, v=val: self._edit_amount(n, v))
            c_lay.addWidget(btn_edit)

            btn_del = QPushButton("×")
            btn_del.setFixedSize(22, 22)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet("background: transparent; color: #EF4444; border: none; font-size: 15px; font-weight: bold;")
            btn_del.clicked.connect(lambda _, n=name: self._delete_amount(n))
            c_lay.addWidget(btn_del)

            row = idx // 2
            col = idx % 2
            self.amounts_grid.addWidget(chip, row, col)

    def _create_new_amount(self):
        diag = QuickAmountDialog("", 0, self.window())
        if diag.exec():
            if "quick_amounts" not in self.settings:
                self.settings["quick_amounts"] = {}
            self.settings["quick_amounts"][diag.amount_name] = diag.amount_val
            self._persist_settings()
            self._refresh_amounts_grid()
            global_signals.show_toast.emit(f"مبلغ سریع «{diag.amount_name}» با موفقیت اضافه شد.", "success")

    def _edit_amount(self, old_name: str, old_val: int):
        diag = QuickAmountDialog(old_name, old_val, self.window())
        if diag.exec():
            if diag.amount_name != old_name and old_name in self.settings.get("quick_amounts", {}):
                del self.settings["quick_amounts"][old_name]
            self.settings["quick_amounts"][diag.amount_name] = diag.amount_val
            self._persist_settings()
            self._refresh_amounts_grid()
            global_signals.show_toast.emit("مبلغ سریع با موفقیت ویرایش شد.", "success")

    def _delete_amount(self, amount_name: str):
        if StudioConfirmDialog.ask(
            self.window(),
            title="تأیید حذف مبلغ",
            message=f"آیا از حذف مبلغ سریع «{amount_name}» اطمینان دارید؟",
            confirm_text="حذف مبلغ",
            is_danger=True,
            icon_name="trash"
        ):
            if "quick_amounts" in self.settings and amount_name in self.settings["quick_amounts"]:
                del self.settings["quick_amounts"][amount_name]
                self._persist_settings()
                self._refresh_amounts_grid()
                global_signals.show_toast.emit(f"مبلغ «{amount_name}» حذف گردید.", "info")

    def _create_new_package(self):
        avail_clips = self.settings.get("custom_clips", [])
        diag = QuickPackageDialog("", [], avail_clips, self.window())
        if diag.exec():
            if "packages" not in self.settings:
                self.settings["packages"] = {}
            self.settings["packages"][diag.package_name] = diag.selected_clips
            self._persist_settings()
            self._refresh_packages_grid()
            global_signals.show_toast.emit(f"پکیج «{diag.package_name}» با موفقیت ایجاد شد.", "success")

    def _edit_package(self, pkg_name: str, current_clips: list):
        avail_clips = self.settings.get("custom_clips", [])
        diag = QuickPackageDialog(pkg_name, current_clips, avail_clips, self.window())
        if diag.exec():
            if diag.package_name != pkg_name and pkg_name in self.settings.get("packages", {}):
                del self.settings["packages"][pkg_name]
            self.settings["packages"][diag.package_name] = diag.selected_clips
            self._persist_settings()
            self._refresh_packages_grid()
            global_signals.show_toast.emit("پکیج با موفقیت به‌روزرسانی شد.", "success")

    def _delete_package(self, pkg_name: str):
        if StudioConfirmDialog.ask(
            self.window(),
            title="تأیید حذف پکیج",
            message=f"آیا از حذف پکیج سریع «{pkg_name}» اطمینان دارید؟",
            confirm_text="حذف پکیج",
            is_danger=True,
            icon_name="trash"
        ):
            if "packages" in self.settings and pkg_name in self.settings["packages"]:
                del self.settings["packages"][pkg_name]
                self._persist_settings()
                self._refresh_packages_grid()
                global_signals.show_toast.emit(f"پکیج «{pkg_name}» حذف شد.", "info")

    def _add_clip(self):
        txt = self.input_new_clip.text().strip()
        if txt and txt not in self.settings.get("custom_clips", []):
            if "custom_clips" not in self.settings:
                self.settings["custom_clips"] = []
            self.settings["custom_clips"].append(txt)
            self.input_new_clip.clear()
            self._persist_settings()
            self._refresh_clips_grid()
            global_signals.show_toast.emit(f"کلیپ «{txt}» به بانک عناوین اضافه شد.", "success")

    def _delete_clip_by_name(self, clip_name: str):
        if "custom_clips" in self.settings and clip_name in self.settings["custom_clips"]:
            self.settings["custom_clips"].remove(clip_name)
            self._persist_settings()
            self._refresh_clips_grid()
            global_signals.show_toast.emit(f"کلیپ «{clip_name}» حذف گردید.", "info")

    def _add_studio_to_db(self):
        comp = self.input_studio_company.text().strip()
        manager = self.input_studio_manager.text().strip()
        raw_phone = self.input_studio_phone.text().strip()
        phone = normalize_to_english_digits(raw_phone) if raw_phone else None
        
        if not comp and not manager:
            StudioConfirmDialog.ask(self.window(), "خطا در ثبت", "لطفاً نام آتلیه یا نام مدیریت را وارد کنید.", icon_name="alert")
            return

        with db.get_session() as session:
            client = Client(
                full_name=manager or comp, 
                company=comp or manager,
                phone=phone
            )
            session.add(client)
            session.commit()
            client_id = client.id

        self.input_studio_company.clear()
        self.input_studio_manager.clear()
        self.input_studio_phone.clear()
        self._refresh_studios_grid()
        global_signals.client_balance_updated.emit(client_id)
        global_signals.settings_updated.emit()
        global_signals.show_toast.emit(f"استودیوی «{comp or manager}» با موفقیت ثبت شد.", "success")

    def _edit_studio_by_id(self, client_id: int):
        with db.get_session() as session:
            client = session.get(Client, client_id)
            if not client:
                return
            company = client.company or ""
            manager = client.full_name or ""
            phone = client.phone or ""

        diag = EditStudioDialog(client_id, company=company, manager=manager, phone=phone, parent=self.window())
        if diag.exec():
            with db.get_session() as session:
                target_client = session.get(Client, client_id)
                if target_client:
                    target_client.company = diag.company_val
                    target_client.full_name = diag.manager_val
                    target_client.phone = diag.phone_val or None
                    session.commit()

            self._refresh_studios_grid()
            global_signals.client_balance_updated.emit(client_id)
            global_signals.project_updated.emit(0)
            global_signals.settings_updated.emit()
            global_signals.show_toast.emit("مشخصات استودیو با موفقیت به‌روزرسانی شد.", "success")

    def _delete_studio_by_id(self, client_id: int):
        with db.get_session() as session:
            client = session.get(Client, client_id)
            if not client:
                return

            client_name = client.company or client.full_name
            projects_count = len(client.projects)

            details_text = f"توجه: تعداد {to_persian_numbers(projects_count)} پروژه به این استودیو متصل هستند و به استودیوی «بدون استودیو / متفرقه» منتقل می‌شوند." if projects_count > 0 else ""

            if not StudioConfirmDialog.ask(
                self.window(),
                title="تأیید حذف استودیو",
                message=f"آیا از حذف استودیو «{client_name}» اطمینان دارید؟",
                details=details_text,
                confirm_text="حذف استودیو",
                is_danger=True,
                icon_name="trash"
            ):
                return

            fallback_client = session.scalars(
                select(Client).where((Client.company == "بدون استودیو / متفرقه") | (Client.full_name == "استودیوی عمومی"))
            ).first()

            if not fallback_client:
                fallback_client = Client(
                    full_name="استودیوی عمومی",
                    company="بدون استودیو / متفرقه",
                    notes="استودیوی سیستمی جهت نگهداری پروژه‌های بدون صاحب"
                )
                session.add(fallback_client)
                session.flush()

            fallback_id = fallback_client.id

            if client.id == fallback_id:
                StudioConfirmDialog.ask(self.window(), "عملیات غیرمجاز", "امکان حذف استودیوی پیش‌فرض سیستمی وجود ندارد.", icon_name="alert")
                return

            session.execute(
                text("UPDATE projects SET client_id = :new_id WHERE client_id = :old_id"),
                {"new_id": fallback_id, "old_id": client_id}
            )
            session.execute(
                text("UPDATE transactions SET client_id = :new_id WHERE client_id = :old_id"),
                {"new_id": fallback_id, "old_id": client_id}
            )

            client.projects.clear()
            client.transactions.clear()

            session.delete(client)
            session.commit()

        self._refresh_studios_grid()
        global_signals.client_balance_updated.emit(fallback_id)
        global_signals.project_updated.emit(0)
        global_signals.settings_updated.emit()
        global_signals.show_toast.emit(f"استودیوی «{client_name}» حذف شد.", "info")

    def _browse_default_drive(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه پیش‌فرض ذخیره‌سازی")
        if folder:
            self.input_default_drive.setText(folder)
            self.settings["default_drive_path"] = folder
            self._persist_settings()
            global_signals.show_toast.emit("مسیر پیش‌فرض هارد راش‌ها تنظیم شد.", "success")

    def _browse_music_vault_drive(self):
        current = self.input_music_drive.text()
        chosen = QFileDialog.getExistingDirectory(self, "انتخاب پوشه مقصد برای آرشیو موزیک", current)
        if chosen and chosen != current:
            if AudioVaultManager.set_custom_vault_path(chosen):
                self.input_music_drive.setText(str(Path(chosen).resolve()))
                self.settings["music_vault_path"] = str(Path(chosen).resolve())
                self._persist_settings()
                global_signals.show_toast.emit("مسیر آرشیو موزیک با موفقیت به‌روزرسانی شد.", "success")
            else:
                StudioConfirmDialog.ask(self.window(), "خطا", "خطا در تنظیم مسیر پوشه انتخابی.", icon_name="alert")

    def _backup_db(self):
        from widgets.studio_backup_dialogs import StudioExportBackupDialog
        from core.backup_manager import StudioBackupManager
        import jdatetime

        diag = StudioExportBackupDialog(self.window())
        if not diag.exec():
            return

        selected_sections = diag.selected_sections
        if not selected_sections:
            return

        today_clean = jdatetime.date.today().strftime("%Y_%m_%d")
        default_filename = f"CutterLog_Studio_Backup_{today_clean}.clpbackup"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره بسته پشتیبان جامع استودیو",
            default_filename,
            "CutterLog Studio Backup (*.clpbackup);;Zip Archive (*.zip)"
        )
        if path:
            if StudioBackupManager.create_backup_archive(path, selected_sections):
                StudioConfirmDialog.ask(
                    self.window(),
                    title="پشتیبان‌گیری موفق",
                    message="بسته پشتیبان استودیو با موفقیت بسته‌بندی و ذخیره شد.",
                    details=f"بخش‌های ذخیره‌شده: {len(selected_sections)} بخش\nمسیر فایل:\n{path}",
                    confirm_text="متوجه شدم",
                    icon_name="check"
                )
            else:
                StudioConfirmDialog.ask(
                    self.window(),
                    title="خطا در پشتیبان‌گیری",
                    message="خطایی در ذخیره بسته پشتیبان رخ داد.",
                    is_danger=True,
                    icon_name="alert"
                )

    def _restore_db(self):
        from widgets.studio_backup_dialogs import StudioImportBackupDialog
        from core.backup_manager import StudioBackupManager

        path, _ = QFileDialog.getOpenFileName(
            self,
            "انتخاب فایل پشتیبان استودیو",
            "",
            "CutterLog Backups (*.clpbackup *.zip *.db);;All Files (*.*)"
        )
        if not path:
            return

        manifest_info = StudioBackupManager.inspect_backup_archive(path)
        if not manifest_info:
            StudioConfirmDialog.ask(
                self.window(),
                title="فایل نامعتبر",
                message="فایل انتخاب‌شده ساختار پشتیبان معتبر CutterLog Pro را ندارد.",
                is_danger=True,
                icon_name="alert"
            )
            return

        diag = StudioImportBackupDialog(manifest_info, self.window())
        if not diag.exec():
            return

        selected_sections = diag.selected_sections
        if not selected_sections:
            return

        if StudioBackupManager.restore_backup_archive(path, selected_sections):
            self.settings = SettingsManager.load_settings()

            if hasattr(self, "input_editor"):
                self.input_editor.blockSignals(True)
                self.input_editor.setText(self.settings.get("editor_name", ""))
                self.input_editor.blockSignals(False)

            if hasattr(self, "input_studio"):
                self.input_studio.blockSignals(True)
                self.input_studio.setText(self.settings.get("studio_name", ""))
                self.input_studio.blockSignals(False)

            if hasattr(self, "input_phone"):
                self.input_phone.blockSignals(True)
                self.input_phone.setText(self.settings.get("phone", ""))
                self.input_phone.blockSignals(False)

            if hasattr(self, "input_card"):
                self.input_card.blockSignals(True)
                self.input_card.setText(self.settings.get("card_number", ""))
                self.input_card.blockSignals(False)

            if hasattr(self, "input_iban"):
                self.input_iban.blockSignals(True)
                self.input_iban.setText(self.settings.get("iban", ""))
                self.input_iban.blockSignals(False)

            if hasattr(self, "txt_client_template"):
                self.txt_client_template.blockSignals(True)
                self.txt_client_template.setPlainText(self.settings.get("client_message_template", ""))
                self.txt_client_template.blockSignals(False)

            if hasattr(self, "input_invoice_note"):
                self.input_invoice_note.blockSignals(True)
                self.input_invoice_note.setPlainText(self.settings.get("invoice_footer_note", ""))
                self.input_invoice_note.blockSignals(False)

            if hasattr(self, "stepper_deadline"):
                self.stepper_deadline.setValue(self.settings.get("alert_days_before_deadline", 5))

            if hasattr(self, "stepper_auto_archive"):
                self.stepper_auto_archive.setValue(self.settings.get("auto_archive_delivered_days", 7))

            self._refresh_packages_grid()
            self._refresh_clips_grid()
            self._refresh_studios_grid()
            self._refresh_amounts_grid()
            self._refresh_branding_previews()

            global_signals.settings_updated.emit()
            global_signals.project_updated.emit(0)

            StudioConfirmDialog.ask(
                self.window(),
                title="بازیابی موفق",
                message="بخش‌های انتخاب‌شده با موفقیت بازیابی و اعمال شدند.",
                details="پیشنهاد می‌شود جهت پاکسازی کش سیستم و رندر فونت‌ها، برنامه را یک‌بار مجدداً راه‌اندازی کنید.",
                confirm_text="متوجه شدم",
                icon_name="check"
            )
        else:
            StudioConfirmDialog.ask(
                self.window(),
                title="خطا در بازیابی",
                message="خطایی در فرآیند استخراج و اعمال اطلاعات رخ داد.",
                is_danger=True,
                icon_name="alert"
            )