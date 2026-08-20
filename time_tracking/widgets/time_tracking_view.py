# ==================================================
# FILE: time_tracking/widgets/time_tracking_view.py
# ==================================================
from datetime import datetime
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QScrollArea, QProgressBar, QGridLayout, 
    QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient

from database.db_manager import db
from database.models import Project, ProjectClipItem
from core.project_controller import ProjectController
from time_tracking.models import WorkSession
from time_tracking.timer_engine import TimeTrackingEngine
from time_tracking.widgets.timer_control_card import TimerControlCard, format_seconds_hms
from time_tracking.widgets.system_monitor_card import SystemMonitorCard
from time_tracking.widgets.end_session_dialog import PauseSessionNoteDialog
from time_tracking.widgets.manual_entry_dialog import ManualTimeEntryDialog
from time_tracking.widgets.daily_goal_dialog import DailyGoalSettingDialog
from widgets.studio_dialog_base import StudioConfirmDialog
from core.persian_utils import to_persian_numbers
from core.icon_provider import IconProvider
from core.signals import global_signals
from sqlalchemy import select, func


class NleStyleTimelineBar(QWidget):
    """
    رندر بصری تایم‌لاین سگمنتی متناسب با طول زمان واقعی هر کلیپ
    فقط کلیپ‌های دارای سابقه زمانی نمایش داده می‌شوند و متن داخل آن‌ها کاملاً وسط‌چین است.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.clips_data: List[dict] = []
        self.active_clip_id: Optional[int] = None
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def set_timeline_data(self, clips: List[dict], active_clip_id: Optional[int] = None):
        # فیلتر کلیپ‌های دارای سابقه زمانی (بیشتر از صفر ثانیه)
        self.clips_data = [c for c in clips if c.get("spent_seconds", 0) > 0]
        self.active_clip_id = active_clip_id
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        track_y = 18.0
        track_h = 32.0

        # خط‌کش زمان (Time Ruler)
        painter.setPen(QPen(QColor(255, 255, 255, 20), 1))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        for x_step in range(0, int(w), 80):
            painter.drawLine(x_step, 0, x_step, 8)
            painter.setPen(QColor("#64748B"))
            painter.drawText(QRectF(x_step - 25, 0, 50, 14), Qt.AlignmentFlag.AlignCenter, f"{x_step // 80:02d}h")
            painter.setPen(QPen(QColor(255, 255, 255, 15), 1))

        if not self.clips_data:
            painter.setPen(QColor("#64748B"))
            painter.setFont(QFont("Vazirmatn", 10))
            painter.drawText(QRectF(0, track_y, w, track_h), Qt.AlignmentFlag.AlignCenter, "هیچ زمان ثبت‌شده‌ای برای کلیپ‌های این پروژه وجود ندارد.")
            painter.end()
            return

        total_clips = len(self.clips_data)
        total_time = sum(c.get("spent_seconds", 0) for c in self.clips_data)
        spacing = 4.0
        available_w = max(10.0, w - (spacing * (total_clips - 1)))

        # تخصیص طول متناسب با زمان با حفظ حداقل طول برای خوانایی متن
        min_width_per_clip = 95.0
        if total_clips * min_width_per_clip > available_w:
            min_width_per_clip = available_w / total_clips

        remaining_w = available_w - (total_clips * min_width_per_clip)
        current_x = 0.0

        for idx, clip in enumerate(self.clips_data):
            dur_sec = clip.get("spent_seconds", 0)
            time_ratio = (dur_sec / total_time) if total_time > 0 else (1.0 / total_clips)
            slot_w = min_width_per_clip + (remaining_w * time_ratio if remaining_w > 0 else 0)

            rect = QRectF(current_x, track_y, slot_w, track_h)

            is_active = (clip.get("id") == self.active_clip_id)
            is_completed = clip.get("is_completed", False)

            grad = QLinearGradient(current_x, track_y, current_x, track_y + track_h)
            if is_active:
                grad.setColorAt(0.0, QColor("#6E62F9"))
                grad.setColorAt(1.0, QColor("#4F46E5"))
                border_pen = QPen(QColor("#A5B4FC"), 1.8)
            elif is_completed:
                grad.setColorAt(0.0, QColor("#10B981"))
                grad.setColorAt(1.0, QColor("#059669"))
                border_pen = QPen(QColor(16, 185, 129, 120), 1.0)
            else:
                grad.setColorAt(0.0, QColor("#1E283D"))
                grad.setColorAt(1.0, QColor("#141B2A"))
                border_pen = QPen(QColor(255, 255, 255, 20), 1.0)

            painter.setPen(border_pen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(rect, 4, 4)

            # محتوای کاملاً وسط‌چین (Center Aligned)
            clip_name = clip.get("name", f"Clip {idx+1}")
            dur_str = format_seconds_hms(dur_sec)

            painter.setFont(QFont("Vazirmatn", 8.5, QFont.Weight.Bold if is_active else QFont.Weight.Normal))
            painter.setPen(QColor("#FFFFFF" if (is_active or is_completed) else "#CBD5E1"))
            painter.drawText(QRectF(current_x + 2, track_y + 2, slot_w - 4, 14), Qt.AlignmentFlag.AlignCenter, clip_name)

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor("#FBBF24" if is_active else ("#E2E8F0" if is_completed else "#94A3B8")))
            painter.drawText(QRectF(current_x + 2, track_y + 16, slot_w - 4, 14), Qt.AlignmentFlag.AlignCenter, to_persian_numbers(dur_str))

            current_x += slot_w + spacing

        painter.end()


class ProjectTimelineDashboardCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(125)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame#NleTimelineCardFrame {
                background-color: #0E1322;
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 10px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.setObjectName("NleTimelineCardFrame")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconProvider.get_pixmap("projects", "#818CF8", size=15))
        top_row.addWidget(lbl_icon)

        self.lbl_proj_title = QLabel("تایم‌لاین تدوین قطعات پروژه:")
        self.lbl_proj_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #F8FAFC;")
        top_row.addWidget(self.lbl_proj_title)

        top_row.addStretch()

        self.lbl_total_time = QLabel("مجموع کارکرد روی پروژه: ۰۰:۰۰:۰۰")
        self.lbl_total_time.setStyleSheet("font-size: 11px; font-weight: 700; color: #10B981; background-color: rgba(16, 185, 129, 0.12); padding: 2px 8px; border-radius: 4px;")
        top_row.addWidget(self.lbl_total_time)

        layout.addLayout(top_row)

        self.timeline_render = NleStyleTimelineBar(self)
        layout.addWidget(self.timeline_render)

    def update_project_timeline(self, project_id: Optional[int], project_name: str, active_clip_id: Optional[int] = None):
        if not project_id:
            self.lbl_proj_title.setText("تایم‌لاین تدوین قطعات پروژه: —")
            self.lbl_total_time.setText("مجموع کارکرد: ۰۰:۰۰:۰۰")
            self.timeline_render.set_timeline_data([], None)
            return

        self.lbl_proj_title.setText(f"تایم‌لاین تدوین قطعات پروژه: <b style='color:#818CF8;'>{project_name}</b>")

        clips_data = []
        total_proj_sec = 0

        with db.get_session() as session:
            clips = session.scalars(select(ProjectClipItem).where(ProjectClipItem.project_id == project_id)).all()

            for c in clips:
                spent_sec = session.execute(
                    select(func.sum(WorkSession.active_duration)).where(WorkSession.clip_id == c.id)
                ).scalar() or 0

                engine = TimeTrackingEngine.instance()
                if engine.is_running and not engine.is_paused and engine.current_clip_id == c.id:
                    spent_sec += engine.active_seconds

                total_proj_sec += spent_sec

                clips_data.append({
                    "id": c.id,
                    "name": c.clip_name,
                    "is_completed": c.is_completed,
                    "spent_seconds": spent_sec
                })

        self.lbl_total_time.setText(f"مجموع کارکرد: {to_persian_numbers(format_seconds_hms(total_proj_sec))}")
        self.timeline_render.set_timeline_data(clips_data, active_clip_id)


class RetroactivePromptBanner(QFrame):
    def __init__(self, on_accept_cb, on_dismiss_cb, parent=None):
        super().__init__(parent)
        self.on_accept_cb = on_accept_cb
        self.on_dismiss_cb = on_dismiss_cb
        self.pending_seconds = 0
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(44)
        self.setVisible(False)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E1B4B, stop:1 #161F30);
                border: 1.5px solid #6366F1;
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_msg = QLabel()
        self.lbl_msg.setStyleSheet("font-size: 11.5px; font-weight: 700; color: #F8FAFC;")
        layout.addWidget(self.lbl_msg, stretch=1)

        btn_accept = QPushButton("+ افزودن به زمان تدوین")
        btn_accept.setFixedHeight(28)
        btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_accept.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; color: #FFFFFF;
                background-color: #10B981; border: none; border-radius: 5px; padding: 0 12px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_accept.clicked.connect(self._accept)
        layout.addWidget(btn_accept)

        btn_dismiss = QPushButton("× نادیده گرفتن")
        btn_dismiss.setFixedHeight(28)
        btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dismiss.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600; color: #94A3B8;
                background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 5px; padding: 0 10px;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_dismiss.clicked.connect(self._dismiss)
        layout.addWidget(btn_dismiss)

    def show_prompt(self, seconds_away: int, app_name: str):
        self.pending_seconds = seconds_away
        mins = max(1, seconds_away // 60)
        self.lbl_msg.setText(f"⏱️ حدود {to_persian_numbers(mins)} دقیقه خارج از نرم‌افزار تدوین ({app_name}) بودید. آیا این زمان صرف هماهنگی یا پروژه شد؟")
        self.setVisible(True)

    def _accept(self):
        self.setVisible(False)
        self.on_accept_cb(self.pending_seconds)

    def _dismiss(self):
        self.setVisible(False)
        self.on_dismiss_cb()


class CompactSummaryCard(QFrame):
    def __init__(self, title: str, main_val: str, sub_val: str, progress_ratio: float = 0.0, accent_color: str = "#818CF8", on_settings_cb=None, parent=None):
        super().__init__(parent)
        self.setObjectName("CompactSummaryCard")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(70)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(3)

        top_row = QHBoxLayout()
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #8F909D; border: none; background: transparent;")
        top_row.addWidget(lbl_t)

        if on_settings_cb:
            btn_gear = QPushButton()
            btn_gear.setIcon(IconProvider.get_icon("settings", "#818CF8", size=11))
            btn_gear.setFixedSize(18, 18)
            btn_gear.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_gear.setToolTip("تغییر هدف کاری امروز")
            btn_gear.setStyleSheet("QPushButton { background: transparent; border: none; padding: 0; } QPushButton:hover { background: rgba(99, 102, 241, 0.2); border-radius: 4px; }")
            btn_gear.clicked.connect(on_settings_cb)
            top_row.addWidget(btn_gear)

        top_row.addStretch()

        self.lbl_sub = QLabel(sub_val)
        self.lbl_sub.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #64748B; border: none; background: transparent;")
        top_row.addWidget(self.lbl_sub)
        layout.addLayout(top_row)

        self.lbl_main = QLabel(main_val)
        self.lbl_main.setStyleSheet(f"font-family: 'Vazirmatn', 'Segoe UI'; font-size: 16px; font-weight: 800; color: {accent_color}; border: none; background: transparent;")
        layout.addWidget(self.lbl_main)

        self.pb = QProgressBar()
        self.pb.setRange(0, 100)
        self.pb.setValue(int(progress_ratio * 100))
        self.pb.setFixedHeight(3)
        self.pb.setTextVisible(False)
        self.pb.setStyleSheet(f"QProgressBar {{ background: #1A2234; border-radius: 1.5px; border: none; }} QProgressBar::chunk {{ background: {accent_color}; border-radius: 1.5px; }}")
        layout.addWidget(self.pb)

        self.setStyleSheet("""
            QFrame#CompactSummaryCard {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)

    def update_values(self, main_val: str, sub_val: str, progress_ratio: float = 0.0):
        self.lbl_main.setText(main_val)
        self.lbl_sub.setText(sub_val)
        self.pb.setValue(int(progress_ratio * 100))


class GridClipButton(QPushButton):
    def __init__(self, clip_id: int, clip_name: str, is_completed: bool, spent_seconds: int = 0, is_active: bool = False, on_click_cb=None, parent=None):
        super().__init__(parent)
        self.clip_id = clip_id
        self.clip_name = clip_name
        self.spent_seconds = spent_seconds
        self.is_completed = is_completed
        self.on_click_cb = on_click_cb
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._update_text()
        self.set_active_state(is_active, is_completed)
        self.clicked.connect(lambda: self.on_click_cb(self.clip_id, self.clip_name) if self.on_click_cb else None)

    def _update_text(self):
        time_badge = f" ({to_persian_numbers(format_seconds_hms(self.spent_seconds))})" if self.spent_seconds > 0 else ""
        self.setText(f"{self.clip_name}{time_badge}")

    def update_spent_seconds(self, seconds: int):
        self.spent_seconds = seconds
        self._update_text()

    def set_active_state(self, is_active: bool, is_completed: bool = False):
        self.is_completed = is_completed
        if is_active:
            self.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: #6E62F9;
                    color: #FFFFFF;
                    border: 1px solid #8B80F9;
                    border-radius: 6px;
                    font-size: 11.5px;
                    font-weight: 800;
                    padding: 0 8px;
                }
            """)
        else:
            border_color = "rgba(16, 185, 129, 0.35)" if is_completed else "rgba(255, 255, 255, 0.04)"
            text_color = "#34D399" if is_completed else "#E2E8F0"
            self.setStyleSheet(f"""
                QPushButton {{
                    font-family: 'Vazirmatn';
                    background-color: #151D2D;
                    color: {text_color};
                    border: 1px solid {border_color};
                    border-radius: 6px;
                    font-size: 11.5px;
                    font-weight: 600;
                    padding: 0 8px;
                }}
                QPushButton:hover {{
                    background-color: #1C273C;
                    color: #FFFFFF;
                    border-color: rgba(99, 102, 241, 0.4);
                }}
            """)


class SessionGridCard(QFrame):
    def __init__(self, session_data: dict, on_delete_cb, parent=None):
        super().__init__(parent)
        self.session_data = session_data
        self.on_delete_cb = on_delete_cb
        self.setFixedHeight(62)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QFrame {
                background-color: #0E1322;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #13192C;
                border-color: rgba(99, 102, 241, 0.3);
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        top_row.setAlignment(Qt.AlignmentFlag.AlignRight)

        st_str = self.session_data.get("start_str", "--:--")
        et_str = self.session_data.get("end_str", "--:--")
        lbl_time_range = QLabel(f"{to_persian_numbers(st_str)} تا {to_persian_numbers(et_str)}")
        lbl_time_range.setStyleSheet("font-family: 'Segoe UI', 'Vazirmatn'; font-size: 11px; font-weight: 700; color: #818CF8;")
        top_row.addWidget(lbl_time_range)

        dur_str = to_persian_numbers(self.session_data.get("duration_hms", "00:00:00"))
        lbl_dur = QLabel(f"⏱️ {dur_str}")
        lbl_dur.setStyleSheet("font-family: 'Segoe UI', 'Vazirmatn'; font-size: 10.5px; font-weight: 800; color: #10B981; background-color: rgba(16, 185, 129, 0.12); padding: 1px 5px; border-radius: 4px;")
        top_row.addWidget(lbl_dur)

        clip_name = self.session_data.get("clip_name", "کارکرد عمومی")
        lbl_clip = QLabel(f"| {clip_name}")
        lbl_clip.setStyleSheet("font-size: 11px; font-weight: 800; color: #F8FAFC;")
        top_row.addWidget(lbl_clip)

        if self.session_data.get("is_manual"):
            lbl_badge = QLabel("دستی")
            lbl_badge.setStyleSheet("font-size: 9px; font-weight: bold; color: #F59E0B; background-color: rgba(245,158,11,0.15); border-radius: 3px; padding: 1px 4px;")
            top_row.addWidget(lbl_badge)

        top_row.addStretch()
        info_col.addLayout(top_row)

        note_text = self.session_data.get("note") or ""
        note_display = f"یادداشت: {note_text}" if note_text else "بدون یادداشت ثبت‌شده"
        note_color = "#C084FC" if note_text else "#64748B"
        lbl_note = QLabel(note_display)
        lbl_note.setStyleSheet(f"font-size: 10px; color: {note_color}; font-weight: 500;")
        info_col.addWidget(lbl_note)

        layout.addLayout(info_col, stretch=1)

        btn_del = QPushButton()
        btn_del.setIcon(IconProvider.get_icon("trash", "#EF4444", size=12))
        btn_del.setFixedSize(24, 24)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setToolTip("حذف این جلسه کاری")
        btn_del.setStyleSheet("QPushButton { background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 4px; } QPushButton:hover { background-color: #EF4444; }")
        btn_del.clicked.connect(lambda: self.on_delete_cb(self.session_data["id"]))
        layout.addWidget(btn_del)


class TimeTrackingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.engine = TimeTrackingEngine.instance()
        
        self.selected_project_id: Optional[int] = None
        self.cached_uncompleted_projects: List[dict] = []
        self.clip_buttons: List[GridClipButton] = []

        self.init_ui()
        self._connect_signals()
        self.refresh_dashboard()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 14, 20, 14)
        main_layout.setSpacing(10)

        # ۱. بنر جبران زمان
        self.retro_banner = RetroactivePromptBanner(
            on_accept_cb=self._on_retroactive_accepted,
            on_dismiss_cb=lambda: None,
            parent=self
        )
        main_layout.addWidget(self.retro_banner)

        # ۲. سربرگ
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        lbl_title = QLabel("مدیریت زمان و پایش راندمان")
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 18px; font-weight: 800; color: #F8FAFC;")
        lbl_desc = QLabel("پایش هوشمند جلسات، تشخیص رندر خودکار و ماشین وضعیت زمینه کاری")
        lbl_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_desc)
        header_row.addLayout(title_col, stretch=1)

        btn_manual = QPushButton("+ ثبت دستی زمان")
        btn_manual.setIcon(IconProvider.get_icon("edit", "#818CF8", size=12))
        btn_manual.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_manual.setFixedHeight(30)
        btn_manual.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; background-color: #161F30; color: #818CF8;
                border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 6px; padding: 0 12px;
                font-size: 11px; font-weight: 700;
            }
            QPushButton:hover { background-color: #6366F1; color: #FFFFFF; }
        """)
        btn_manual.clicked.connect(self._open_manual_entry_dialog)
        header_row.addWidget(btn_manual)

        main_layout.addLayout(header_row)

        # ۳. کارت‌های ۳ گانه خلاصه روز
        self.summary_row = QHBoxLayout()
        self.summary_row.setSpacing(8)

        self.card_today_time = CompactSummaryCard("کارکرد امروز", "00:00", "هدف: 08:00", progress_ratio=0.0, accent_color="#10B981")
        self.card_goal = CompactSummaryCard(
            "هدف امروز", "۰٪", "۸ ساعت باقی‌مانده", 
            progress_ratio=0.0, accent_color="#6366F1",
            on_settings_cb=self._open_goal_settings_dialog
        )
        self.card_focus = CompactSummaryCard("تمرکز امروز", "۸۵٪", "تمرکز مطلوب", progress_ratio=0.85, accent_color="#F59E0B")

        self.summary_row.addWidget(self.card_today_time)
        self.summary_row.addWidget(self.card_goal)
        self.summary_row.addWidget(self.card_focus)
        main_layout.addLayout(self.summary_row)

        # ۴. Hero Timer + System Monitoring
        mid_row = QHBoxLayout()
        mid_row.setSpacing(10)

        self.timer_card = TimerControlCard(
            on_pause_cb=self._handle_pause_with_note,
            on_finish_clip_cb=self._handle_finish_clip_direct,
            parent=self
        )
        mid_row.addWidget(self.timer_card, stretch=3)

        self.monitor_card = SystemMonitorCard(self)
        mid_row.addWidget(self.monitor_card, stretch=2)

        main_layout.addLayout(mid_row)

        # ۵. اسکرول پایینی
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(10)
        c_lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        c_lay.addWidget(self._build_project_clip_container())

        # کارت تایم‌لاین گرافیکی قطعات
        self.nle_timeline_card = ProjectTimelineDashboardCard(self)
        c_lay.addWidget(self.nle_timeline_card)

        # تاریخچه جلسات کاری
        c_lay.addWidget(self._build_session_history_section())
        c_lay.addStretch(1)

        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

    def _on_retroactive_accepted(self, seconds: int):
        self.engine.apply_retroactive_time(seconds)
        self.refresh_dashboard()

    def _open_goal_settings_dialog(self):
        cur_mins = self.engine.get_daily_goal_minutes()
        diag = DailyGoalSettingDialog(current_minutes=cur_mins, parent=self.window())
        if diag.exec():
            self.engine.set_daily_goal_minutes(diag.target_minutes)
            global_signals.show_toast.emit(f"هدف کاری روزانه روی {to_persian_numbers(diag.target_minutes // 60)} ساعت و {to_persian_numbers(diag.target_minutes % 60)} دقیقه تنظیم شد.", "success")
            self.refresh_dashboard()

    def _build_project_clip_container(self) -> QWidget:
        card = QFrame()
        card.setObjectName("ActiveProjectClipBox")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setStyleSheet("""
            QFrame#ActiveProjectClipBox {
                background-color: #0E1322;
                border: 1.5px solid #4F46E5;
                border-radius: 10px;
            }
        """)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(8)

        header_bar = QHBoxLayout()
        header_bar.setSpacing(10)

        self.lbl_project_header = QLabel("پروژه (استودیو)")
        self.lbl_project_header.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 900; color: #F8FAFC; background: transparent; border: none;")
        header_bar.addWidget(self.lbl_project_header)

        header_bar.addStretch()

        lbl_filter = QLabel("پروژه:")
        lbl_filter.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #8F909D; background: transparent; border: none;")
        header_bar.addWidget(lbl_filter)

        self.combo_filter_projects = QComboBox()
        self.combo_filter_projects.setFixedHeight(26)
        self.combo_filter_projects.setMinimumWidth(210)
        self.combo_filter_projects.setStyleSheet("""
            QComboBox {
                font-family: 'Vazirmatn'; background-color: #161F30; border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px; padding: 1px 8px; color: #F8FAFC; font-size: 11px; font-weight: 600;
            }
            QComboBox:hover { border-color: #6366F1; }
            QComboBox QAbstractItemView {
                background-color: #121826; color: #F8FAFC; selection-background-color: #6366F1;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        self.combo_filter_projects.currentIndexChanged.connect(self._on_filter_project_changed)
        header_bar.addWidget(self.combo_filter_projects)

        lay.addLayout(header_bar)

        self.clips_grid_layout = QGridLayout()
        self.clips_grid_layout.setSpacing(6)
        self.clips_grid_layout.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(self.clips_grid_layout)

        return card

    def _build_session_history_section(self) -> QWidget:
        box = QFrame()
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        box.setStyleSheet("QFrame { background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; }")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        self.lbl_history_title = QLabel("تاریخچه جلسات کاری امروز:")
        self.lbl_history_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        lay.addWidget(self.lbl_history_title)

        self.sessions_grid_layout = QGridLayout()
        self.sessions_grid_layout.setSpacing(6)
        self.sessions_grid_layout.setContentsMargins(0, 0, 0, 0)
        for i in range(3):
            self.sessions_grid_layout.setColumnStretch(i, 1)

        lay.addLayout(self.sessions_grid_layout)
        return box

    def _connect_signals(self):
        trigger = lambda *args: QTimer.singleShot(0, self.refresh_dashboard)
        global_signals.session_started.connect(trigger)
        global_signals.session_ended.connect(trigger)
        global_signals.project_created.connect(trigger)
        global_signals.project_updated.connect(trigger)
        global_signals.clip_status_toggled.connect(trigger)
        global_signals.timer_tick.connect(self._on_timer_tick)
        self.engine.retroactive_prompt_requested.connect(self.retro_banner.show_prompt)

    def _on_timer_tick(self, snap: dict):
        today_sec = self.engine.get_today_total_active_seconds()
        h = today_sec // 3600
        m = (today_sec % 3600) // 60
        goal_mins = self.engine.get_daily_goal_minutes()
        ratio = today_sec / (goal_mins * 60) if goal_mins > 0 else 0.0

        self.card_today_time.update_values(
            main_val=f"{h:02d}:{m:02d}",
            sub_val=f"هدف: {goal_mins//60:02d}:{goal_mins%60:02d}",
            progress_ratio=ratio
        )

        cur_proj = next((p for p in self.cached_uncompleted_projects if p["id"] == self.selected_project_id), None)
        if cur_proj and hasattr(self, "nle_timeline_card"):
            self.nle_timeline_card.update_project_timeline(
                self.selected_project_id,
                cur_proj["couple_names"],
                self.engine.current_clip_id
            )

    def refresh_dashboard(self):
        today_sec = self.engine.get_today_total_active_seconds()
        h = today_sec // 3600
        m = (today_sec % 3600) // 60
        goal_mins = self.engine.get_daily_goal_minutes()
        ratio = min(1.0, today_sec / (goal_mins * 60)) if goal_mins > 0 else 0.0

        pct_val = int(ratio * 100)
        rem_sec = max(0, (goal_mins * 60) - today_sec)
        rem_h = rem_sec // 3600
        rem_m = (rem_sec % 3600) // 60

        self.card_today_time.update_values(
            main_val=f"{h:02d}:{m:02d}",
            sub_val=f"هدف: {goal_mins//60:02d}:{goal_mins%60:02d}",
            progress_ratio=ratio
        )
        self.card_goal.update_values(
            main_val=f"{to_persian_numbers(pct_val)}٪",
            sub_val=f"{rem_h:02d}:{rem_m:02d} باقی‌مانده",
            progress_ratio=ratio
        )

        self._load_uncompleted_projects()
        self._refresh_session_history()

    def _load_uncompleted_projects(self):
        raw_projects = ProjectController.get_active_projects()
        
        uncompleted_list = []
        for p in raw_projects:
            if not p.clips:
                continue
            completed_cnt, total_cnt, pct = ProjectController.calculate_project_progress(p)
            if pct < 100:
                studio_name = p.client.company if (p.client and p.client.company) else (p.client.full_name if p.client else "بدون استودیو")
                uncompleted_list.append({
                    "id": p.id,
                    "project_number": p.project_number or p.id,
                    "couple_names": p.couple_names or p.title,
                    "title": p.title,
                    "studio_name": studio_name,
                    "progress_pct": pct,
                    "clips": [{"id": c.id, "name": c.clip_name, "is_completed": c.is_completed} for c in p.clips]
                })

        uncompleted_list.sort(key=lambda x: x["progress_pct"], reverse=True)
        self.cached_uncompleted_projects = uncompleted_list

        self.combo_filter_projects.blockSignals(True)
        self.combo_filter_projects.clear()

        for p in self.cached_uncompleted_projects:
            display_text = f"{p['couple_names']} ({p['studio_name']}) — {to_persian_numbers(p['progress_pct'])}٪"
            self.combo_filter_projects.addItem(display_text, p["id"])

        if self.cached_uncompleted_projects:
            target_pid = self.engine.current_project_id or self.selected_project_id
            if target_pid and target_pid in [p["id"] for p in self.cached_uncompleted_projects]:
                self.selected_project_id = target_pid
            else:
                self.selected_project_id = self.cached_uncompleted_projects[0]["id"]
            
            idx = self.combo_filter_projects.findData(self.selected_project_id)
            if idx >= 0:
                self.combo_filter_projects.setCurrentIndex(idx)
        else:
            self.selected_project_id = None
            self.combo_filter_projects.addItem("تمام پروژه‌ها ۱۰۰٪ تکمیل شده‌اند ✓", None)

        self.combo_filter_projects.blockSignals(False)
        self._render_clips_grid()

    def _on_filter_project_changed(self):
        p_id = self.combo_filter_projects.currentData()
        if p_id:
            self.selected_project_id = p_id
            self._render_clips_grid()
            self._refresh_session_history()

    def _render_clips_grid(self):
        while self.clips_grid_layout.count():
            item = self.clips_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.clip_buttons.clear()

        cur_proj = next((p for p in self.cached_uncompleted_projects if p["id"] == self.selected_project_id), None)
        if not cur_proj:
            self.lbl_project_header.setText("پروژه‌ای برای انجام باقی نمانده است ✓")
            self.timer_card.set_context("پروژه‌ای انتخاب نشده", "—", "—", False, 0)
            if hasattr(self, "nle_timeline_card"):
                self.nle_timeline_card.update_project_timeline(None, "")
            return

        couple_name = cur_proj["couple_names"]
        studio_name = cur_proj["studio_name"]
        self.lbl_project_header.setText(f"{couple_name}  <span style='color:#38BDF8;'>(استودیو {studio_name})</span>")
        
        clips = cur_proj.get("clips", [])
        
        if not self.engine.current_clip_id or self.engine.current_clip_id not in [c["id"] for c in clips]:
            first_uncompleted = next((c for c in clips if not c["is_completed"]), clips[0] if clips else None)
            if first_uncompleted:
                self.engine.select_context(cur_proj["id"], first_uncompleted["id"])

        columns_count = 5
        active_clip_spent_seconds = 0
        active_clip_is_completed = False

        with db.get_session() as session:
            for idx, c in enumerate(clips):
                is_active = (self.engine.current_clip_id == c["id"])
                
                # محاسبه مجموع زمان ثبت‌شده برای این کلیپ
                spent_sec = session.execute(
                    select(func.sum(WorkSession.active_duration)).where(WorkSession.clip_id == c["id"])
                ).scalar() or 0

                if is_active:
                    active_clip_spent_seconds = spent_sec
                    active_clip_is_completed = c["is_completed"]

                btn = GridClipButton(
                    clip_id=c["id"],
                    clip_name=c["name"],
                    is_completed=c["is_completed"],
                    spent_seconds=spent_sec,
                    is_active=is_active,
                    on_click_cb=self._select_clip
                )
                row = idx // columns_count
                col = idx % columns_count
                self.clips_grid_layout.addWidget(btn, row, col)
                self.clip_buttons.append(btn)

        active_clip = next((c for c in clips if c["id"] == self.engine.current_clip_id), None)
        active_clip_name = active_clip["name"] if active_clip else "—"
        
        self.timer_card.set_context(
            couple_name, 
            studio_name, 
            active_clip_name, 
            is_completed=active_clip_is_completed, 
            accumulated_seconds=active_clip_spent_seconds
        )

        if hasattr(self, "nle_timeline_card"):
            self.nle_timeline_card.update_project_timeline(
                self.selected_project_id,
                couple_name,
                self.engine.current_clip_id
            )

    def _select_clip(self, clip_id: int, clip_name: str):
        self.engine.select_context(self.selected_project_id, clip_id)
        
        cur_proj = next((p for p in self.cached_uncompleted_projects if p["id"] == self.selected_project_id), None)
        active_spent_sec = 0
        active_is_completed = False

        with db.get_session() as session:
            clip_obj = session.get(ProjectClipItem, clip_id)
            if clip_obj:
                active_is_completed = clip_obj.is_completed
            active_spent_sec = session.execute(
                select(func.sum(WorkSession.active_duration)).where(WorkSession.clip_id == clip_id)
            ).scalar() or 0

        if cur_proj:
            self.timer_card.set_context(
                cur_proj["couple_names"], 
                cur_proj["studio_name"], 
                clip_name, 
                is_completed=active_is_completed, 
                accumulated_seconds=active_spent_sec
            )
            if hasattr(self, "nle_timeline_card"):
                self.nle_timeline_card.update_project_timeline(
                    self.selected_project_id,
                    cur_proj["couple_names"],
                    clip_id
                )
        
        for btn in self.clip_buttons:
            is_act = (btn.clip_id == clip_id)
            is_comp = False
            if cur_proj:
                c_item = next((c for c in cur_proj["clips"] if c["id"] == btn.clip_id), None)
                if c_item:
                    is_comp = c_item["is_completed"]
            btn.set_active_state(is_act, is_comp)

        self.timer_card.update_display_state()
        self._refresh_session_history()

    def _refresh_session_history(self):
        while self.sessions_grid_layout.count():
            item = self.sessions_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        with db.get_session() as session:
            stmt = select(WorkSession).where(WorkSession.start_time >= today_start)

            if self.engine.current_clip_id:
                stmt = stmt.where(WorkSession.clip_id == self.engine.current_clip_id)
                clip_obj = session.get(ProjectClipItem, self.engine.current_clip_id)
                c_title = clip_obj.clip_name if clip_obj else "کلیپ انتخابی"
                self.lbl_history_title.setText(f"تاریخچه جلسات امروز کلیپ: <span style='color:#818CF8;'>{c_title}</span>")
            else:
                self.lbl_history_title.setText("تاریخچه تمام جلسات کاری امروز:")

            stmt = stmt.order_by(WorkSession.start_time.desc())
            sessions = session.scalars(stmt).all()

            if not sessions:
                empty_msg = "برای این کلیپ هنوز جلسه کاری ثبت نشده است." if self.engine.current_clip_id else "امروز هنوز جلسه کاری ثبت نشده است."
                empty_lbl = QLabel(empty_msg)
                empty_lbl.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; padding: 8px 0;")
                empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.sessions_grid_layout.addWidget(empty_lbl, 0, 0, 1, 3)
                return

            cols = 3
            for idx, s in enumerate(sessions):
                st_str = s.start_time.strftime("%H:%M:%S") if s.start_time else "--:--:--"
                et_str = s.end_time.strftime("%H:%M:%S") if s.end_time else "--:--:--"
                dur_hms = format_seconds_hms(s.active_duration or 0)

                s_data = {
                    "id": s.id,
                    "start_str": st_str,
                    "end_str": et_str,
                    "duration_hms": dur_hms,
                    "project_name": s.project.couple_names if s.project else "پروژه",
                    "clip_name": s.clip.clip_name if s.clip else "کارکرد عمومی",
                    "note": s.note,
                    "is_manual": s.is_manual
                }
                card = SessionGridCard(s_data, on_delete_cb=self._delete_session)
                r = idx // cols
                c = idx % cols
                self.sessions_grid_layout.addWidget(card, r, c)

    def _delete_session(self, session_id: int):
        if StudioConfirmDialog.ask(
            self.window(),
            title="حذف جلسه کاری",
            message="آیا از حذف این جلسه کاری اطمینان دارید؟",
            details="مدت زمان این جلسه از مجموع کارکرد پروژه و کلیپ کسر خواهد شد.",
            confirm_text="حذف جلسه",
            is_danger=True,
            icon_name="trash"
        ):
            with db.get_session() as session:
                sess = session.get(WorkSession, session_id)
                if sess:
                    session.delete(sess)
                    session.commit()
            
            global_signals.session_ended.emit(0)
            global_signals.show_toast.emit("جلسه کاری با موفقیت حذف شد.", "info")
            self.refresh_dashboard()

    def _handle_pause_with_note(self):
        active_sec = self.engine.active_seconds
        dur_str = format_seconds_hms(active_sec)
        clip_name = "کلیپ انتخابی"
        
        cur_proj = next((p for p in self.cached_uncompleted_projects if p["id"] == self.engine.current_project_id), None)
        if cur_proj:
            for c in cur_proj.get("clips", []):
                if c["id"] == self.engine.current_clip_id:
                    clip_name = c["name"]
                    break

        diag = PauseSessionNoteDialog(dur_str, clip_name=clip_name, parent=self.window())
        if diag.exec():
            if self.engine.active_session_id:
                with db.get_session() as session:
                    sess = session.get(WorkSession, self.engine.active_session_id)
                    if sess:
                        sess.note = diag.session_note
                        session.commit()

            self.engine.pause_session(auto=False)
            global_signals.show_toast.emit("جلسه کاری متوقف شد.", "info")
            self.refresh_dashboard()

    def _handle_finish_clip_direct(self):
        cur_proj = next((p for p in self.cached_uncompleted_projects if p["id"] == self.engine.current_project_id), None)
        clip_name = "کلیپ"
        if cur_proj:
            for c in cur_proj.get("clips", []):
                if c["id"] == self.engine.current_clip_id:
                    clip_name = c["name"]
                    break

        if StudioConfirmDialog.ask(
            self.window(),
            title="تکمیل نهایی کلیپ",
            message=f"آیا کار روی کلیپ «{clip_name}» به پایان رسیده است؟",
            details="وضعیت این کلیپ ۱۰۰٪ تکمیل شده ثبت می‌شود و تایمر آن قفل خواهد شد.",
            confirm_text="✓ بله، کلیپ تکمیل شد",
            is_danger=False,
            icon_name="check"
        ):
            self.engine.end_session(note="تکمیل ۱۰۰٪ کلیپ", mark_clip_completed=True)
            global_signals.show_toast.emit(f"کلیپ «{clip_name}» تکمیل و قفل شد.", "success")
            self.refresh_dashboard()

    def _open_manual_entry_dialog(self):
        diag = ManualTimeEntryDialog(
            initial_project_id=self.selected_project_id,
            initial_clip_id=self.engine.current_clip_id,
            parent=self.window()
        )
        if diag.exec():
            self.refresh_dashboard()