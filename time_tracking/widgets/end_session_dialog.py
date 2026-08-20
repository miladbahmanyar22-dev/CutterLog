# ==================================================
# FILE: time_tracking/widgets/end_session_dialog.py
# ==================================================
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
from PySide6.QtCore import Qt
from widgets.studio_dialog_base import StudioBaseDialog
from core.persian_utils import to_persian_numbers


class PauseSessionNoteDialog(StudioBaseDialog):
    """پاپ‌آپ دریافت یادداشت جلسه کاری هنگام توقف موقت"""
    def __init__(self, duration_str: str, clip_name: str = "", parent=None):
        super().__init__(parent=parent)
        self.duration_str = duration_str
        self.clip_name = clip_name
        self.session_note = ""

        self.setFixedWidth(440)
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "توقف موقت جلسه کاری", 
            f"مدت زمان ثبت‌شده: {to_persian_numbers(self.duration_str)} | کلیپ: {self.clip_name}", 
            icon_name="pause", 
            icon_color="#F59E0B"
        )

        self.container_layout.addWidget(QLabel("یادداشت جلسه (تغییرات انجام‌شده، نکات خروجی و...):"))
        self.txt_note = QTextEdit()
        self.txt_note.setFixedHeight(85)
        self.txt_note.setPlaceholderText("یادداشت خود را اینجا بنویسید (اختیاری)...")
        self.txt_note.setStyleSheet("""
            QTextEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 8px 10px;
                color: #F8FAFC;
                font-family: 'Vazirmatn';
                font-size: 12px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.container_layout.addWidget(self.txt_note)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_submit = QPushButton("ثبت و توقف جلسه")
        btn_submit.setFixedHeight(36)
        btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_submit.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #F59E0B;
                color: #000000;
                font-weight: 800;
                border-radius: 6px;
                border: none;
                font-size: 12px;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #FBBF24; }
        """)
        btn_submit.clicked.connect(self._submit)
        btn_box.addWidget(btn_submit, stretch=2)

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
                font-weight: 600;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #1E283D; color: #F8FAFC; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _submit(self):
        self.session_note = self.txt_note.toPlainText().strip()
        self.accept()