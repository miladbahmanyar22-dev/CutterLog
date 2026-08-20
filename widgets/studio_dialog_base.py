# ==================================================
# FILE: widgets/studio_dialog_base.py
# ==================================================
from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QGraphicsOpacityEffect, QLineEdit
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QGuiApplication
from core.icon_provider import IconProvider


class StudioBaseDialog(QDialog):
    """
    کلاس پایه تمامی پاپ‌آپ‌ها و دیالوگ‌های نرم‌افزار با قابلیت:
    - ریسپانسیو بودن کامل و مهار ابعاد بر اساس ابعاد مانیتور فعال
    - فریم‌لس بودن و انیمیشن Fade-In روان
    - گوشه‌های گرد ۱۲px با بردر ظریف و تم تاریک هماهنگ
    """
    def __init__(self, parent=None, is_danger: bool = False):
        super().__init__(parent)
        self.is_danger = is_danger
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # ساختار ریشه
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(10, 10, 10, 10)

        # کانتینر اصلی
        self.modal_container = QFrame(self)
        self.modal_container.setObjectName("StudioModalContainer")
        
        border_color = "rgba(239, 68, 68, 0.40)" if is_danger else "rgba(255, 255, 255, 0.08)"
        self.modal_container.setStyleSheet(f"""
            QFrame#StudioModalContainer {{
                background-color: #0E131F;
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        self._root_layout.addWidget(self.modal_container)

        self.container_layout = QVBoxLayout(self.modal_container)
        self.container_layout.setContentsMargins(20, 18, 20, 18)
        self.container_layout.setSpacing(14)

        # انیمیشن ورود نرم (Fade-In)
        self._opacity_effect = QGraphicsOpacityEffect(self.modal_container)
        self.modal_container.setGraphicsEffect(self._opacity_effect)
        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(140)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    def showEvent(self, event):
        super().showEvent(event)
        # مهار و ریسپانسیو کردن ابعاد دیالوگ متناسب با مانیتور جاری
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            max_w = int(avail.width() * 0.94)
            max_h = int(avail.height() * 0.92)
            self.setMaximumSize(max_w, max_h)
            if self.width() > max_w or self.height() > max_h:
                self.resize(min(self.width(), max_w), min(self.height(), max_h))
        self._anim.start()

    def build_header(self, title: str, subtitle: str = "", icon_name: str = "info", icon_color: str = "#818CF8"):
        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        header_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap(icon_name, icon_color, size=20))
        header_row.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14px; font-weight: 800; color: #F8FAFC;")
        title_col.addWidget(lbl_t)

        if subtitle:
            lbl_s = QLabel(subtitle)
            lbl_s.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B;")
            title_col.addWidget(lbl_s)

        header_row.addLayout(title_col, stretch=1)

        btn_close = QPushButton("×")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748B;
                font-size: 18px;
                font-weight: bold;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #F8FAFC;
                background-color: rgba(255, 255, 255, 0.06);
            }
        """)
        btn_close.clicked.connect(self.reject)
        header_row.addWidget(btn_close)

        self.container_layout.addLayout(header_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        self.container_layout.addWidget(divider)


class StudioConfirmDialog(StudioBaseDialog):
    """جایگزین مدرن و یکپارچه QMessageBox با استایل بومی نرم‌افزار"""
    def __init__(self, title: str, message: str, details: str = "", confirm_text: str = "تأیید", 
                 is_danger: bool = False, icon_name: str = "alert", parent=None):
        super().__init__(parent=parent, is_danger=is_danger)
        self.setFixedWidth(440)

        icon_color = "#EF4444" if is_danger else "#F59E0B"
        self.build_header(title, "", icon_name=icon_name, icon_color=icon_color)

        # متن پیام
        body_card = QFrame()
        body_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 8px;")
        b_lay = QVBoxLayout(body_card)
        b_lay.setContentsMargins(14, 12, 14, 12)
        b_lay.setSpacing(6)

        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; font-weight: 600; color: #F8FAFC; line-height: 1.5;")
        b_lay.addWidget(lbl_msg)

        if details:
            lbl_det = QLabel(details)
            lbl_det.setWordWrap(True)
            lbl_det.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; line-height: 1.5;")
            b_lay.addWidget(lbl_det)

        self.container_layout.addWidget(body_card)

        # دکمه‌های اقدام
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_confirm = QPushButton(confirm_text)
        btn_confirm.setFixedHeight(36)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_danger:
            btn_confirm.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: #EF4444;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 700;
                    padding: 0 16px;
                }
                QPushButton:hover { background-color: #DC2626; }
            """)
        else:
            btn_confirm.setStyleSheet("""
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
                QPushButton:hover { background-color: #4F46E5; }
            """)
        btn_confirm.clicked.connect(self.accept)
        btn_box.addWidget(btn_confirm, stretch=2)

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
                font-weight: 500;
                padding: 0 14px;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    @classmethod
    def ask(cls, parent, title: str, message: str, details: str = "", confirm_text: str = "تأیید", 
            is_danger: bool = False, icon_name: str = "alert") -> bool:
        diag = cls(title, message, details, confirm_text, is_danger, icon_name, parent)
        return diag.exec() == QDialog.DialogCode.Accepted


class StudioInputDialog(StudioBaseDialog):
    """جایگزین مدرن و یکپارچه QInputDialog برای دریافت ورودی‌های متنی"""
    def __init__(self, title: str, label_text: str, initial_text: str = "", placeholder: str = "", parent=None):
        super().__init__(parent=parent)
        self.setFixedWidth(420)
        self.build_header(title, "", icon_name="edit", icon_color="#6366F1")

        self.container_layout.addWidget(QLabel(label_text))
        
        self.input_field = QLineEdit(initial_text)
        self.input_field.setFixedHeight(36)
        self.input_field.setPlaceholderText(placeholder)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 10px;
                font-family: 'Vazirmatn';
                font-size: 12px;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.input_field.returnPressed.connect(self.accept)
        self.container_layout.addWidget(self.input_field)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_ok = QPushButton("تأیید و ثبت")
        btn_ok.setFixedHeight(36)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok, stretch=2)

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

    @classmethod
    def get_text(cls, parent, title: str, label_text: str, initial_text: str = "", placeholder: str = "") -> Tuple[str, bool]:
        diag = cls(title, label_text, initial_text, placeholder, parent)
        ok = (diag.exec() == QDialog.DialogCode.Accepted)
        return diag.input_field.text().strip(), ok