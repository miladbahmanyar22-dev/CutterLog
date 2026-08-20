# ==================================================
# FILE: widgets/empty_state.py
# ==================================================
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from core.icon_provider import IconProvider


class ModernEmptyStateWidget(QWidget):
    """
    نمایش وضعیت خالی مینیمال، مدرن و متناسب با تم تاریک سیستم
    """
    action_clicked = Signal()

    def __init__(
        self, 
        title: str = "هیچ پروژه‌ای یافت نشد", 
        description: str = "برای شروع تدوین و ایجاد پایپ‌لاین، اولین پروژه را ثبت کنید.",
        button_text: str = "+ تعریف پروژه جدید",
        icon_name: str = "folder",
        parent=None
    ):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # آیکون
        lbl_icon = QLabel()
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setPixmap(IconProvider.get_icon(icon_name, "#475569", size=42).pixmap(42, 42))
        layout.addWidget(lbl_icon)

        # عنوان
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 15px; font-weight: 800; color: #F8FAFC;")
        layout.addWidget(lbl_title)

        # توضیحات
        lbl_desc = QLabel(description)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #64748B; max-width: 380px;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        if button_text:
            layout.addSpacing(6)
            btn_action = QPushButton(button_text)
            btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_action.setFixedHeight(38)
            btn_action.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: #6366F1;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 8px;
                    padding: 0 20px;
                    font-size: 12.5px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #4F46E5;
                }
            """)
            btn_action.clicked.connect(self.action_clicked.emit)
            layout.addWidget(btn_action, alignment=Qt.AlignmentFlag.AlignCenter)