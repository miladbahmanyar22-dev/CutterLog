# ==================================================
# FILE: widgets/support_dialog.py
# ==================================================
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QApplication
)
from PySide6.QtCore import Qt
from core.signals import global_signals
from widgets.studio_dialog_base import StudioBaseDialog


class BankCardPlate(QFrame):
    """کارت بانکی دیجیتال مدرن، مینیمال و استاندارد"""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.owner_name = "میلاد بهمنیار"
        # فرمت‌بندی خوانا برای شماره کارت و شبا
        self.card_number = "6219 8619 8022 3514"
        self.iban = "IR 29 0560 6118 2800 5106 4215 02"

        self.setObjectName("BankCardPlateFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("""
            QFrame#BankCardPlateFrame {
                background-color: #0E131F;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 12px;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        # ردیف هدر کارت: اطلاعات صاحب حساب و بج شتاب
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_owner_title = QLabel("صاحب حساب:")
        lbl_owner_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B; border: none; background: transparent;")
        top_row.addWidget(lbl_owner_title)

        lbl_owner_name = QLabel(self.owner_name)
        lbl_owner_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 700; color: #F8FAFC; border: none; background: transparent;")
        top_row.addWidget(lbl_owner_name)
        
        top_row.addStretch()

        lbl_badge = QLabel("💳  کارت شتاب")
        lbl_badge.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 700; color: #F59E0B; background-color: rgba(245, 158, 11, 0.10); border-radius: 6px; padding: 4px 10px; border: 1px solid rgba(245, 158, 11, 0.2);")
        top_row.addWidget(lbl_badge)
        
        layout.addLayout(top_row)

        # خط جداکننده بسیار محو داخل کارت
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.04); border: none;")
        layout.addWidget(divider)

        # ردیف شماره کارت
        card_box = QHBoxLayout()
        card_box.setSpacing(10)

        self.lbl_card = QLabel(self.card_number)
        self.lbl_card.setFixedHeight(40)
        self.lbl_card.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_card.setStyleSheet("""
            font-family: 'Segoe UI', monospace;
            font-size: 14.5px;
            font-weight: 700;
            color: #FBBF24;
            letter-spacing: 1px;
            background-color: #141B2A;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 0 12px;
        """)
        card_box.addWidget(self.lbl_card, stretch=1)

        self.btn_copy_card = QPushButton("کپی کارت")
        self.btn_copy_card.setFixedSize(110, 40)
        self.btn_copy_card.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_card.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #F59E0B;
                color: #000000;
                font-weight: 800;
                font-size: 12px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #FBBF24; }
        """)
        self.btn_copy_card.clicked.connect(self._copy_card)
        card_box.addWidget(self.btn_copy_card)
        layout.addLayout(card_box)

        # ردیف شماره شبا
        if self.iban:
            iban_box = QHBoxLayout()
            iban_box.setSpacing(10)

            self.lbl_iban = QLabel(self.iban)
            self.lbl_iban.setFixedHeight(40)
            self.lbl_iban.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_iban.setStyleSheet("""
                font-family: 'Segoe UI', monospace;
                font-size: 11.5px;
                font-weight: 600;
                color: #94A3B8;
                letter-spacing: 0.5px;
                background-color: #141B2A;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 0 10px;
            """)
            iban_box.addWidget(self.lbl_iban, stretch=1)

            self.btn_copy_iban = QPushButton("کپی شبا")
            self.btn_copy_iban.setFixedSize(110, 40)
            self.btn_copy_iban.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_copy_iban.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: #1A243D;
                    color: #818CF8;
                    border: 1px solid rgba(99, 102, 241, 0.25);
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: 700;
                }
                QPushButton:hover { background-color: #6366F1; color: #FFFFFF; border-color: #6366F1; }
            """)
            self.btn_copy_iban.clicked.connect(self._copy_iban)
            iban_box.addWidget(self.btn_copy_iban)
            layout.addLayout(iban_box)

    def _copy_card(self):
        clean_num = self.card_number.replace(" ", "").replace("-", "")
        QApplication.clipboard().setText(clean_num)
        self.btn_copy_card.setText("✓ کپی شد")
        self.btn_copy_card.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 12px;
                border: none;
                border-radius: 8px;
            }
        """)
        global_signals.show_toast.emit("شماره کارت در کلیپ‌بورد کپی شد.", "success")

    def _copy_iban(self):
        clean_iban = self.iban.replace(" ", "").replace("-", "")
        QApplication.clipboard().setText(clean_iban)
        self.btn_copy_iban.setText("✓ کپی شد")
        self.btn_copy_iban.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: 800;
                font-size: 12px;
                border: none;
                border-radius: 8px;
            }
        """)
        global_signals.show_toast.emit("شماره شبا در کلیپ‌بورد کپی شد.", "success")


class SupportDeveloperDialog(StudioBaseDialog):
    """پاپ‌آپ کاملاً استاندارد و بازطراحی‌شده حمایت مالی"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setFixedWidth(480)
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "حمایت از توسعه دهنده CutterLog Pro", 
            "یک فنجان قهوه برای سازنده نرم‌افزار ☕", 
            icon_name="sparkles", 
            icon_color="#F59E0B"
        )

        desc_card = QFrame()
        desc_card.setStyleSheet("""
            background-color: #121826;
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        """)
        d_lay = QVBoxLayout(desc_card)
        d_lay.setContentsMargins(18, 14, 18, 14)
        d_lay.setSpacing(6)

        msg_text = (
            "توسعه، بهینه‌سازی و اضافه شدن امکانات جدید به <b>CutterLog Pro</b> به‌صورت کاملاً مستقل انجام می‌شود.\n\n"
            "اگر این نرم‌افزار در نظم، سرعت تدوین و مدیریت حساب‌های پروژه‌های شما مفید بوده است، "
            "می‌توانید با حمایت مالی دلخواه، در تداوم توسعه نسخه‌های آینده سهیم باشید."
        )
        lbl_msg = QLabel(msg_text)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8; line-height: 1.65; border: none; background: transparent;")
        d_lay.addWidget(lbl_msg)
        self.container_layout.addWidget(desc_card)

        card_plate = BankCardPlate(parent=self)
        self.container_layout.addWidget(card_plate)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        
        btn_close = QPushButton("بستن")
        btn_close.setFixedSize(100, 38)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        self.container_layout.addLayout(btn_box)