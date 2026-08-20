# ==================================================
# FILE: widgets/header_summary_pill.py
# ==================================================
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from core.persian_utils import to_persian_numbers


class HeaderSummaryPill(QFrame):
    """
    کامپوننت استاندارد و مینیمال برای نمایش خلاصه وضعیت تعداد در هدر صفحات (پروژه‌ها و آرشیو)
    """
    def __init__(self, title: str, count: int = 0, sub_text: str = "", accent_color: str = "#6366F1", parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderSummaryPillFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.accent_color = accent_color
        self.title_text = title
        self.sub_text = sub_text

        self.setFixedHeight(40)
        self.init_ui()
        self.set_count(count)

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # نشانگر وضعیت بسیار ظریف (Status Dot Indicator)
        self.dot_indicator = QLabel()
        self.dot_indicator.setFixedSize(7, 7)
        self.dot_indicator.setStyleSheet(f"""
            background-color: {self.accent_color};
            border-radius: 3.5px;
            border: none;
        """)
        layout.addWidget(self.dot_indicator)

        # بخش عنوان و توضیح
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setStyleSheet("""
            font-family: 'Vazirmatn';
            font-size: 11.5px;
            font-weight: 500;
            color: #8F909D;
            background: transparent;
            border: none;
        """)
        text_col.addWidget(self.lbl_title)

        if self.sub_text:
            self.lbl_sub = QLabel(self.sub_text)
            self.lbl_sub.setStyleSheet("""
                font-family: 'Vazirmatn';
                font-size: 9.5px;
                font-weight: 400;
                color: #64748B;
                background: transparent;
                border: none;
            """)
            text_col.addWidget(self.lbl_sub)

        layout.addLayout(text_col)

        # خط جداکننده داخلی ظریف
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFixedHeight(18)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: none;")
        layout.addWidget(divider)

        # عدد اصلی و برجسته
        self.lbl_count = QLabel("۰")
        self.lbl_count.setStyleSheet(f"""
            font-family: 'Vazirmatn';
            font-size: 15px;
            font-weight: 800;
            color: {self.accent_color};
            background: transparent;
            border: none;
            padding-right: 2px;
        """)
        layout.addWidget(self.lbl_count)

        self.setStyleSheet("""
            QFrame#HeaderSummaryPillFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            QFrame#HeaderSummaryPillFrame:hover {
                background-color: #161F30;
                border-color: rgba(255, 255, 255, 0.12);
            }
        """)

    def set_count(self, count: int):
        self.lbl_count.setText(to_persian_numbers(count))