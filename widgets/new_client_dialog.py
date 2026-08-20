# ==================================================
# FILE: widgets/new_client_dialog.py
# ==================================================
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton
)
from PySide6.QtCore import Qt, QSize

from database.db_manager import db
from database.models import Client
from core.signals import global_signals
from core.icon_provider import IconProvider
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog


class NewClientDialog(StudioBaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setFixedWidth(460)
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "ثبت کارفرما / استودیوی جدید",
            "مشخصات تماس و یادداشت‌های هماهنگی را وارد کنید",
            icon_name="plus",
            icon_color="#6366F1"
        )

        self.container_layout.addWidget(QLabel("نام و نام خانوادگی:"))
        self.input_name = QLineEdit()
        self.input_name.setFixedHeight(36)
        self.input_name.setPlaceholderText("مثال: علی رضایی")
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

        self.container_layout.addWidget(QLabel("نام برند / شرکت (اختیاری):"))
        self.input_company = QLineEdit()
        self.input_company.setFixedHeight(36)
        self.input_company.setPlaceholderText("مثال: استودیو فیلم‌سازی آوا")
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
        self.container_layout.addWidget(self.input_company)

        self.container_layout.addWidget(QLabel("شماره تماس:"))
        self.input_phone = QLineEdit()
        self.input_phone.setFixedHeight(36)
        self.input_phone.setPlaceholderText("مثال: 09123456789")
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
        self.container_layout.addWidget(self.input_phone)

        self.container_layout.addWidget(QLabel("یادداشت و توافقات مالی:"))
        self.input_notes = QTextEdit()
        self.input_notes.setPlaceholderText("نرخ پایه ساعتی، رزولوشن درخواستی، توضیحات قرارداد...")
        self.input_notes.setFixedHeight(80)
        self.input_notes.setStyleSheet("""
            QTextEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 8px 12px;
                font-family: 'Vazirmatn';
                font-size: 12px;
                color: #F8FAFC;
            }
            QTextEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.container_layout.addWidget(self.input_notes)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        btn_submit = QPushButton("ذخیره کارفرما")
        btn_submit.setFixedHeight(38)
        btn_submit.setIcon(IconProvider.get_icon("save", "#FFFFFF", size=14))
        btn_submit.setIconSize(QSize(14, 14))
        btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_submit.setStyleSheet("""
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
            QPushButton:hover {
                background-color: #4F46E5;
            }
        """)
        btn_submit.clicked.connect(self._submit)
        btn_layout.addWidget(btn_submit, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
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
            QPushButton:hover {
                background-color: #1E283D;
                color: #F8FAFC;
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_layout)

    def _submit(self):
        name = self.input_name.text().strip()
        if not name:
            StudioConfirmDialog.ask(self, "خطا در ثبت", "لطفاً نام کارفرما را وارد کنید.", icon_name="alert")
            return

        company = self.input_company.text().strip() or None
        phone = self.input_phone.text().strip() or None
        notes = self.input_notes.toPlainText().strip() or None

        with db.get_session() as session:
            client = Client(
                full_name=name,
                company=company,
                phone=phone,
                notes=notes
            )
            session.add(client)
            session.commit()
            client_id = client.id

        global_signals.client_balance_updated.emit(client_id)
        self.accept()