# ==================================================
# FILE: widgets/project_card_mini.py
# ==================================================
from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
    QPushButton, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, QTimer
import jdatetime

from core.persian_utils import gregorian_to_jalali, to_persian_numbers, clean_studio_display_name
from core.signals import global_signals
from widgets.base_card import BaseProjectCard
from widgets.status_badge import StatusPillBadge, StatusType
from widgets.project_details_dialog import ProjectDetailsDialog
from time_tracking.timer_engine import TimeTrackingEngine


class ProjectCardMini(BaseProjectCard):
    def __init__(self, project_data: dict, parent=None):
        project_id = project_data.get("id", 0)
        project_number = project_data.get("project_number", project_id)
        
        super().__init__(
            project_id=project_id,
            project_number=project_number,
            parent=parent,
            accent_color="#818CF8",
            card_type="dashboard"
        )
        self.project_data = project_data
        self.setFixedHeight(148)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.init_mini_content()

    def init_mini_content(self):
        active_rev_title = self.project_data.get("active_revision_title")
        progress_val = self.project_data.get("progress_pct", 0)
        c_cnt = self.project_data.get("completed_clips", 0)
        t_cnt = self.project_data.get("total_clips", 0)

        # محاسبه وضعیت ددلاین و رنگ نئونی
        is_urgent = False
        is_overdue = False
        deadline_dt = self.project_data.get("deadline")
        dead_str = "تعیین نشده"
        if deadline_dt:
            dead_str = gregorian_to_jalali(deadline_dt)
            now_dt = datetime.utcnow()
            delta_days = (deadline_dt.date() - now_dt.date()).days
            if delta_days < 0 and progress_val < 100:
                is_overdue = True
            elif delta_days <= 2 and progress_val < 100:
                is_urgent = True

        custom_symbol = None

        if is_overdue:
            status_text = "ددلاین گذشته"
            status_type = StatusType.DANGER
            custom_symbol = ""  # حذف آیکون داخل کپسول جهت نمایش متن خالص
            bar_color = "#EF4444"
        elif is_urgent:
            status_text = "ددلاین فوری"
            status_type = StatusType.WARNING
            custom_symbol = ""
            bar_color = "#F59E0B"
        elif active_rev_title:
            progress_val = self.project_data.get("rev_progress_pct", 0)
            status_text = f"اصلاحیه: {to_persian_numbers(progress_val)}٪"
            status_type = StatusType.WARNING
            bar_color = "#EA580C"
        else:
            bar_color = "#10B981" if progress_val >= 100 else "#6366F1"
            if progress_val >= 100:
                status_text = "آماده تحویل ✓"
                status_type = StatusType.COMPLETED
            elif c_cnt == 0:
                status_text = "در انتظار شروع"
                status_type = StatusType.NEUTRAL
            else:
                status_text = f"پیشرفت: {to_persian_numbers(progress_val)}٪"
                status_type = StatusType.ACTIVE

        self.status_badge = StatusPillBadge(
            label=status_text, 
            status_type=status_type, 
            custom_symbol=custom_symbol
        )
        self.header_tags_layout.addWidget(self.status_badge)
        self.header_tags_layout.addStretch()

        # دکمه اکشن شفاف و متناسب با عملکرد انتقال به بخش زمان‌سنج
        btn_start_timer = QPushButton("ثبت زمان در تایمر")
        btn_start_timer.setFixedHeight(24)
        btn_start_timer.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_start_timer.setToolTip("انتخاب این پروژه و انتقال به بخش زمان و راندمان جهت ثبت کارکرد")
        btn_start_timer.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                font-size: 10.5px;
                font-weight: 700;
                background-color: rgba(99, 102, 241, 0.15);
                color: #A5B4FC;
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 5px;
                padding: 0 9px;
            }
            QPushButton:hover {
                background-color: #6366F1;
                border-color: #818CF8;
                color: #FFFFFF;
            }
        """)
        btn_start_timer.clicked.connect(self._start_project_session)
        self.header_layout.addWidget(btn_start_timer)

        # عنوان زوجین و استودیو
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_box.setContentsMargins(0, 2, 0, 2)

        couple_name = self.project_data.get("couple_names") or self.project_data.get("title", "پروژه")
        self.lbl_title = QLabel(couple_name)
        self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        title_box.addWidget(self.lbl_title)

        raw_client = self.project_data.get("client_name") or "بدون استودیو"
        client_display = clean_studio_display_name(raw_client)
        self.lbl_studio = QLabel(f"استودیو: <span style='color:#38BDF8;'>{client_display}</span>")
        self.lbl_studio.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; border: none; background: transparent;")
        title_box.addWidget(self.lbl_studio)

        self.card_layout.addLayout(title_box)

        # نوار پروگرس نئونی
        pb = QProgressBar()
        pb.setRange(0, 100)
        pb.setValue(progress_val)
        pb.setTextVisible(False)
        pb.setFixedHeight(4)
        pb.setStyleSheet(f"""
            QProgressBar {{
                background-color: #1A2234;
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 2px;
            }}
        """)
        self.card_layout.addWidget(pb)

        # فوتر کارت
        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 2, 0, 0)
        footer_row.setSpacing(8)

        lbl_dead_color = "#EF4444" if is_overdue else ("#F59E0B" if is_urgent else "#64748B")
        lbl_dead = QLabel(f"تحویل: <b style='color:{lbl_dead_color};'>{to_persian_numbers(dead_str)}</b>")
        lbl_dead.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #94A3B8; border: none; background: transparent;")
        footer_row.addWidget(lbl_dead)

        footer_row.addStretch()

        btn_view = QLabel("مشاهده پرونده ←")
        btn_view.setStyleSheet("font-family: 'Vazirmatn'; color: #818CF8; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        footer_row.addWidget(btn_view)

        self.card_layout.addLayout(footer_row)
        self.clicked.connect(lambda _: self._open_details())

    def _start_project_session(self):
        engine = TimeTrackingEngine.instance()
        engine.select_context(self.project_id, None)
        global_signals.navigate_to_page.emit(6)

    def _open_details(self):
        win = self.window()
        QTimer.singleShot(0, lambda: ProjectDetailsDialog(self.project_id, win).exec())