# ==================================================
# FILE: time_tracking/widgets/end_session_dialog.py
# ==================================================
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QFrame, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from widgets.studio_dialog_base import StudioBaseDialog
from core.persian_utils import to_persian_numbers
from core.icon_provider import IconProvider


class PauseSessionNoteDialog(StudioBaseDialog):
    """دیالوگ استودیویی و مدرن توقف جلسه کاری همراه با تگ‌های سریع و نمایش زنده آمار"""
    def __init__(self, duration_str: str, clip_name: str = "", parent=None):
        super().__init__(parent=parent)
        self.duration_str = duration_str
        self.clip_name = clip_name or "کارکرد عمومی"
        self.session_note = ""

        self.setFixedWidth(480)
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "توقف موقت جلسه کاری", 
            "یادداشت تغییرات اعمال‌شده را جهت ثبت در سوابق پایپ‌لاین وارد نمایید", 
            icon_name="pause", 
            icon_color="#F59E0B"
        )

        # ۱. کارت شیشه‌ای خلاصه وضعیت سشن جاری
        stats_card = QFrame()
        stats_card.setStyleSheet("""
            QFrame {
                background-color: #121826;
                border: 1px solid rgba(245, 158, 11, 0.25);
                border-radius: 8px;
            }
        """)
        s_lay = QHBoxLayout(stats_card)
        s_lay.setContentsMargins(14, 10, 14, 10)
        s_lay.setSpacing(12)

        col_clip = QVBoxLayout()
        col_clip.setSpacing(2)
        lbl_c_title = QLabel("قطعه در حال تدوین:")
        lbl_c_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #8F909D; border: none; background: transparent;")
        col_clip.addWidget(lbl_c_title)
        
        lbl_clip = QLabel(f"🎬 {self.clip_name}")
        lbl_clip.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        col_clip.addWidget(lbl_clip)
        s_lay.addLayout(col_clip, stretch=1)

        # خط جداکننده
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFixedHeight(28)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: none;")
        s_lay.addWidget(div)

        col_dur = QVBoxLayout()
        col_dur.setSpacing(2)
        col_dur.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lbl_d_title = QLabel("زمان ثبت‌شده:")
        lbl_d_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #8F909D; border: none; background: transparent;")
        col_dur.addWidget(lbl_d_title)

        lbl_time = QLabel(to_persian_numbers(self.duration_str))
        lbl_time.setStyleSheet("font-family: 'Segoe UI', 'Vazirmatn'; font-size: 13.5px; font-weight: 900; color: #FBBF24; border: none; background: transparent;")
        col_dur.addWidget(lbl_time)
        s_lay.addLayout(col_dur)

        self.container_layout.addWidget(stats_card)

        # ۲. تگ‌های انتخاب سریع (Quick Preset Chips)
        tag_box = QVBoxLayout()
        tag_box.setSpacing(6)
        
        lbl_chips_head = QLabel("تگ‌های سریع گزارش کار (کلیک برای درج):")
        lbl_chips_head.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600; color: #94A3B8;")
        tag_box.addWidget(lbl_chips_head)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)

        presets = [
            ("راف‌کات اولیه", "راف‌کات اولیه سکانس انجام شد."),
            ("اصلاح رنگ و نور", "تصحیح رنگ و نور اعمال گردید."),
            ("سینک صدا و افکت", "صداگذاری و سینک موزیک انجام شد."),
            ("خروجی بازبینی", "خروجی اولیه جهت بررسی گرفته شد.")
        ]

        for label, full_text in presets:
            btn = QPushButton(f"+ {label}")
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    font-size: 10.5px;
                    font-weight: 600;
                    color: #818CF8;
                    background-color: rgba(99, 102, 241, 0.10);
                    border: 1px solid rgba(99, 102, 241, 0.25);
                    border-radius: 5px;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background-color: #6366F1;
                    color: #FFFFFF;
                    border-color: #818CF8;
                }
            """)
            btn.clicked.connect(lambda _, t=full_text: self._append_preset(t))
            chips_row.addWidget(btn)

        chips_row.addStretch()
        tag_box.addLayout(chips_row)
        self.container_layout.addLayout(tag_box)

        # ۳. کادر متنی ورودی یادداشت
        self.txt_note = QTextEdit()
        self.txt_note.setFixedHeight(85)
        self.txt_note.setPlaceholderText("یادداشت یا تغییرات این جلسه را بنویسید (اختیاری)...")
        self.txt_note.setStyleSheet("""
            QTextEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 10px 12px;
                color: #F8FAFC;
                font-family: 'Vazirmatn';
                font-size: 12px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border: 1px solid #6366F1;
                background-color: #1A2438;
            }
        """)
        self.container_layout.addWidget(self.txt_note)

        # ۴. دکمه‌های اکشن
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_submit = QPushButton("ثبت و توقف موقت جلسه")
        btn_submit.setFixedHeight(38)
        btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_submit.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #F59E0B;
                color: #000000;
                font-weight: 800;
                border-radius: 7px;
                border: none;
                font-size: 12px;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #FBBF24; }
        """)
        btn_submit.clicked.connect(self._submit)
        btn_box.addWidget(btn_submit, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #1E283D; color: #F8FAFC; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _append_preset(self, text_to_add: str):
        cur = self.txt_note.toPlainText().strip()
        if cur:
            self.txt_note.setPlainText(f"{cur}\n• {text_to_add}")
        else:
            self.txt_note.setPlainText(f"• {text_to_add}")

    def _submit(self):
        self.session_note = self.txt_note.toPlainText().strip()
        self.accept()


class FinishClipConfirmDialog(StudioBaseDialog):
    """دیالوگ اختصاصی و شیک تأیید خروجی نهایی قطعه"""
    def __init__(self, clip_name: str, total_time_str: str = "", parent=None):
        super().__init__(parent=parent)
        self.clip_name = clip_name
        self.total_time_str = total_time_str
        self.setFixedWidth(460)
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "تأیید خروجی نهایی قطعه",
            "ثبت وضعیت تکمیل و آماده‌سازی جهت تحویل به آتلیه",
            icon_name="check",
            icon_color="#10B981"
        )

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #121826;
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 8px;
            }
        """)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(14, 12, 14, 12)
        c_lay.setSpacing(6)

        lbl_name = QLabel(f"عنوان قطعه: <b style='color:#F8FAFC;'>{self.clip_name}</b>")
        lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; color: #94A3B8; border: none; background: transparent;")
        c_lay.addWidget(lbl_name)

        if self.total_time_str:
            lbl_time = QLabel(f"مجموع زمان کارکرد: <b style='color:#10B981;'>{to_persian_numbers(self.total_time_str)}</b>")
            lbl_time.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8; border: none; background: transparent;")
            c_lay.addWidget(lbl_time)

        lbl_desc = QLabel("با تأیید این مرحله، قطعه در وضعیت «تکمیل ۱۰۰٪» قرار گرفته و به تایم‌لاین پروژه اعمال می‌شود.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; border: none; background: transparent; margin-top: 4px;")
        c_lay.addWidget(lbl_desc)

        self.container_layout.addWidget(card)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_confirm = QPushButton("✓ تأیید و ثبت نهایی")
        btn_confirm.setFixedHeight(38)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 7px;
                font-weight: 800;
                font-size: 12px;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_confirm.clicked.connect(self.accept)
        btn_box.addWidget(btn_confirm, stretch=2)

        btn_cancel = QPushButton("ادامه تدوین")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #1E283D; color: #F8FAFC; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)