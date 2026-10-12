# ==================================================
# FILE: widgets/studio_share_dialog.py
# ==================================================
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QTextEdit, QPushButton, QComboBox, QApplication
)
from PySide6.QtCore import Qt, QSize

from core.settings_manager import SettingsManager
from core.project_controller import ProjectController
from core.persian_utils import format_toman, to_persian_numbers, format_studio_title
from core.icon_provider import IconProvider
from widgets.studio_dialog_base import StudioBaseDialog


class StudioShareDialog(StudioBaseDialog):
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent=parent)
        self.project_id = project_id
        self.project = ProjectController.get_project_by_id(project_id)
        self.setFixedWidth(540)
        self.init_ui()
        self._generate_message()

    def init_ui(self):
        couple = self.project.couple_names if self.project else "پروژه"
        self.build_header(
            f"ارسال پیام به استودیو: {couple}",
            "قالب پیام را انتخاب کنید؛ متن به صورت خودکار تکمیل می‌شود",
            icon_name="message",
            icon_color="#6366F1"
        )

        self.container_layout.addWidget(QLabel("نوع پیام / سناریو:"))
        self.combo_template = QComboBox()
        self.combo_template.setFixedHeight(36)
        self.combo_template.setStyleSheet("""
            QComboBox {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                color: #F8FAFC;
                font-size: 12px;
            }
            QComboBox:focus {
                border-color: #6366F1;
            }
        """)
        self.combo_template.addItem("آماده‌سازی و تحویل اولیه کلیپ‌ها 📤", "delivery")
        self.combo_template.addItem("تکمیل دور اصلاحیه و تغییرات 🎬", "revision_done")
        self.combo_template.addItem("یادآوری تسویه‌حساب و مانده فاکتور 💳", "payment_reminder")
        self.combo_template.addItem("ارسال مشخصات کارت و اطلاعات حساب 🏦", "bank_info")
        self.combo_template.currentIndexChanged.connect(self._generate_message)
        self.container_layout.addWidget(self.combo_template)

        self.container_layout.addWidget(QLabel("متن تولید‌شده (قابل ویرایش دستی):"))
        self.txt_message = QTextEdit()
        self.txt_message.setFixedHeight(170)
        self.txt_message.setStyleSheet("""
            QTextEdit {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 10px 12px;
                color: #F8FAFC;
                font-size: 12.5px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border-color: #6366F1;
            }
        """)
        self.container_layout.addWidget(self.txt_message)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_copy = QPushButton("کپی در کلیپ‌بورد 📋")
        self.btn_copy.setFixedHeight(38)
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)
        btn_box.addWidget(self.btn_copy, stretch=2)

        btn_close = QPushButton("بستن")
        btn_close.setFixedHeight(38)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #1E283D; color: #F8FAFC; }
        """)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _generate_message(self):
        if not self.project:
            return

        settings = SettingsManager.load_settings()
        editor_name = settings.get("editor_name", "تدوین‌گر پروژه")
        
        raw_studio = self.project.client.company if (self.project.client and self.project.client.company) else (self.project.client.full_name if self.project.client else "")
        if raw_studio:
            studio_name = format_studio_title(raw_studio)
        else:
            studio_name = "مدیریت محترم استودیو"

        couple = self.project.couple_names or self.project.title
        fin = ProjectController.get_project_financial_summary(self.project)
        rem_str = format_toman(fin["remaining"])
        total_str = format_toman(fin["total_fee"])
        
        card_number = settings.get("card_number", "")
        iban = settings.get("iban", "")

        t_type = self.combo_template.currentData()

        if t_type == "delivery":
            msg = (
                f"سلام و وقت بخیر خدمت {studio_name} عزیز 🌸\n\n"
                f"تدوین، اصلاح رنگ و صداگذاری پکیج مراسم «{couple}» با موفقیت انجام شد و فایل‌های نهایی آماده تحویل و بازبینی هستند.\n\n"
                f"📊 مبلغ کل قرارداد: {total_str}\n"
                f"💰 مانده حساب قابل تسویه: {rem_str}\n\n"
                f"لطفاً پس از بررسی خروجی‌ها، در صورت نیاز به تغییرات، موارد اصلاحیه را ارسال بفرمایید.\n\n"
                f"با احترام، {editor_name}"
            )
        elif t_type == "revision_done":
            active_rev = ProjectController.get_active_revision(self.project)
            rev_title = active_rev.title if active_rev else "اصلاحات درخواستی"
            msg = (
                f"سلام و احترام، {studio_name} گرامی 🎬\n\n"
                f"تمامی تسک‌ها و تغییرات مربوط به «{rev_title}» برای پروژه «{couple}» اعمال و رندر مجدد انجام شد.\n\n"
                f"فایل‌های اصلاح‌شده آماده بازبینی نهایی شما هستند.\n\n"
                f"با تشکر، {editor_name}"
            )
        elif t_type == "payment_reminder":
            msg = (
                f"سلام و عرض ادب خدمت {studio_name} 🌸\n\n"
                f"احتراماً پیرو تحویل پروژه تدوین «{couple}»، صورت‌حساب مالی پروژه به شرح زیر تقدیم حضور می‌گردد:\n\n"
                f"🔹 مبلغ کل قرارداد: {total_str}\n"
                f"🔹 مجموع دریافتی تا کنون: {format_toman(fin['total_paid'])}\n"
                f"🔸 مانده بدهی قابل تسویه: {rem_str}\n\n"
                f"شماره کارت جهت واریز:\n"
                f"💳 {to_persian_numbers(card_number)}\n"
                f"به نام: {editor_name}\n\n"
                f"ممنون از همکاری و حسن اعتماد شما."
            )
        elif t_type == "bank_info":
            msg = (
                f"اطلاعات حساب و واریز وجه ({editor_name}):\n\n"
                f"💳 شماره کارت: {to_persian_numbers(card_number)}\n"
                f"🏦 شماره شبا: {iban}\n"
                f"📌 مربوط به پروژه: {couple} ({studio_name})\n"
                f"مبلغ قابل پرداخت: {rem_str}"
            )
        else:
            msg = ""

        self.txt_message.setPlainText(msg)

    def _copy_to_clipboard(self):
        text = self.txt_message.toPlainText().strip()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.btn_copy.setText("✓ کپی شد!")
            self.btn_copy.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: #6366F1;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 700;
                    padding: 0 16px;
                }
            """)