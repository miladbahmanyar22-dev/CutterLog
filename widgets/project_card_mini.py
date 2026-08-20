# ==================================================
# FILE: widgets/project_card_mini.py
# ==================================================
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
import jdatetime

from core.persian_utils import gregorian_to_jalali, to_persian_numbers
from core.signals import global_signals
from widgets.base_card import BaseProjectCard
from widgets.status_badge import StatusPillBadge, StatusType
from widgets.project_details_dialog import ProjectDetailsDialog


def progress_pct_to_words(pct: int, completed_clips: int, total_clips: int) -> str:
    if total_clips == 0:
        return "بدون کلیپ"
    if completed_clips == 0:
        return "شروع نشده"
    if pct >= 100 or completed_clips == total_clips:
        return "تکمیل شده"

    ones = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"]
    teens = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"]
    tens = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]

    def _num_to_text(n: int) -> str:
        if n <= 0:
            return "صفر"
        if n < 10:
            return ones[n]
        if n < 20:
            return teens[n - 10]
        if n < 100:
            t = n // 10
            o = n % 10
            if o > 0:
                return f"{tens[t]} و {ones[o]}"
            return tens[t]
        return "صد"

    return f"{_num_to_text(pct)} درصد انجام شده"


class ProjectCardMini(BaseProjectCard):
    """
    کارت فشرده پیشخوان با دکمه پرش مستقیم به تب پروژه‌ها و فوکوس روی کارت
    """
    def __init__(self, project_data: dict, parent=None):
        project_id = project_data.get("id", 0)
        project_number = project_data.get("project_number", project_id)
        
        super().__init__(
            project_id=project_id,
            project_number=project_number,
            parent=parent,
            accent_color="#6366F1",
            card_type="dashboard"
        )
        self.project_data = project_data
        # ارتفاع افزایش‌یافته برای نمایش کامل نام پروژه بدون تداخل با بج‌ها و فوتر
        self.setFixedHeight(145)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.init_mini_content()

    def init_mini_content(self):
        # ۱. ردیف بالا: وضعیت + دکمه پرش به پروژه
        active_rev_title = self.project_data.get("active_revision_title")
        if active_rev_title:
            progress_val = self.project_data.get("rev_progress_pct", 0)
            completed_cnt = self.project_data.get("rev_completed_tasks", 0)
            total_cnt = self.project_data.get("rev_total_tasks", 0)
            status_text = f"اصلاحیه: {progress_pct_to_words(progress_val, completed_cnt, total_cnt)}"
            status_type = StatusType.WARNING
            status_symbol = "●"
            bar_color = "#EA580C"
        else:
            progress_val = self.project_data.get("progress_pct", 0)
            completed_cnt = self.project_data.get("completed_clips", 0)
            total_cnt = self.project_data.get("total_clips", 0)
            status_text = progress_pct_to_words(progress_val, completed_cnt, total_cnt)
            bar_color = "#10B981" if progress_val >= 100 else "#6366F1"
            
            if progress_val >= 100 or (total_cnt > 0 and completed_cnt == total_cnt):
                status_type = StatusType.COMPLETED
                status_symbol = "✓"
            elif completed_cnt == 0:
                status_type = StatusType.NEUTRAL
                status_symbol = "○"
            else:
                status_type = StatusType.ACTIVE
                status_symbol = "●"

        self.status_badge = StatusPillBadge(
            label=status_text,
            status_type=status_type,
            custom_symbol=status_symbol
        )
        self.header_tags_layout.addWidget(self.status_badge)
        self.header_tags_layout.addStretch()

        self.btn_focus_project = QPushButton("↗")
        self.btn_focus_project.setFixedSize(22, 22)
        self.btn_focus_project.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_focus_project.setToolTip("مشاهده و فوکوس روی این پروژه در تب پروژه‌ها")
        self.btn_focus_project.setStyleSheet("""
            QPushButton {
                font-family: 'Segoe UI', 'Vazirmatn';
                background-color: #1A2234;
                color: #818CF8;
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 5px;
                font-size: 13px;
                font-weight: bold;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background-color: #6366F1;
                color: #FFFFFF;
                border-color: #6366F1;
            }
        """)
        self.btn_focus_project.clicked.connect(self._go_to_project_tab)
        self.header_layout.addWidget(self.btn_focus_project)

        # ۲. عنوان و استودیو با چیدمان آزاد
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 4, 0, 4)

        couple_name = self.project_data.get("couple_names") or self.project_data.get("title", "پروژه بدون نام")
        self.lbl_title = QLabel(couple_name)
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14px; font-weight: 800; color: #F8FAFC; background: transparent; border: none; padding: 1px 0;")
        title_box.addWidget(self.lbl_title)

        client_name = self.project_data.get("client_name") or "بدون استودیو"
        self.lbl_studio = QLabel(f"استودیو: {client_name}")
        self.lbl_studio.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; font-weight: 500; background: transparent; border: none;")
        title_box.addWidget(self.lbl_studio)

        self.card_layout.addLayout(title_box)

        # ۳. پروگرس‌بار باریک
        pb = QProgressBar()
        pb.setRange(0, 100)
        pb.setValue(progress_val)
        pb.setTextVisible(False)
        pb.setFixedHeight(3)
        pb.setStyleSheet(f"""
            QProgressBar {{
                background-color: #242E42;
                border: none;
                border-radius: 1.5px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 1.5px;
            }}
        """)
        self.card_layout.addWidget(pb)

        # ۴. فوتر
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 2, 0, 0)
        footer_row.setSpacing(6)

        deadline_dt = self.project_data.get("deadline")
        if deadline_dt:
            dead_str = gregorian_to_jalali(deadline_dt)
            today = jdatetime.date.today()
            try:
                dead_j = jdatetime.date.fromgregorian(date=deadline_dt.date())
                days_left = (dead_j - today).days
                if days_left < 0:
                    dead_color = "#EF4444"
                elif days_left <= 2:
                    dead_color = "#F59E0B"
                else:
                    dead_color = "#64748B"
            except Exception:
                dead_color = "#64748B"

            lbl_dead = QLabel(f"تحویل: {dead_str}")
            lbl_dead.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 10.5px; color: {dead_color}; background: transparent; border: none;")
            footer_row.addWidget(lbl_dead)

        footer_row.addStretch()

        btn_view = QLabel("پرونده ←")
        btn_view.setStyleSheet("font-family: 'Vazirmatn'; color: #6366F1; font-size: 11px; font-weight: 700; background: transparent; border: none;")
        footer_row.addWidget(btn_view)

        self.card_layout.addLayout(footer_row)
        self.clicked.connect(lambda _: self._open_details())

    def _go_to_project_tab(self):
        global_signals.navigate_and_focus_project.emit(self.project_id)

    def _open_details(self):
        proj_id = self.project_id
        win = self.window()
        QTimer.singleShot(0, lambda: ProjectDetailsDialog(proj_id, win).exec())