# ==================================================
# FILE: views/copilot_view.py
# ==================================================
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QPushButton, QProgressBar, QSizePolicy,
    QGridLayout
)
from PySide6.QtCore import Qt, QTimer, QSize
from sqlalchemy import select

from database.db_manager import db
from database.models import Project, ProjectEventLog
from time_tracking.models import WorkSession
from core.copilot_engine import CopilotEngine
from core.icon_provider import IconProvider
from core.settings_manager import SettingsManager
from core.project_controller import ProjectController
from core.finance_controller import FinanceController
from core.nle_messenger_helper import NleLauncherHelper
from core.persian_utils import format_toman, to_persian_numbers, gregorian_to_jalali
from core.signals import global_signals
from widgets.studio_dialog_base import StudioInputDialog


class CommandHeaderBar(QFrame):
    """هدر فشرده و زنده مرکز فرماندهی"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(44)
        self.setStyleSheet("""
            QFrame {
                background-color: #0E131F;
                border: 1px solid rgba(255, 255, 255, 0.05);
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

        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconProvider.get_pixmap("sparkles", "#818CF8", size=17))
        layout.addWidget(lbl_icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_title = QLabel("مرکز فرماندهی هوشمند تدوین (CutterLog Copilot)")
        lbl_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #F8FAFC;")
        title_col.addWidget(lbl_title)

        layout.addLayout(title_col)

        self.lbl_live_status = QLabel("● تحلیل خودکار فعال")
        self.lbl_live_status.setStyleSheet("""
            font-size: 10px; font-weight: 700; color: #10B981;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 4px; padding: 2px 7px;
        """)
        layout.addWidget(self.lbl_live_status)

        layout.addStretch()

        self.lbl_last_sync = QLabel("بروزرسانی: همین الان")
        self.lbl_last_sync.setStyleSheet("font-size: 10.5px; color: #64748B;")
        layout.addWidget(self.lbl_last_sync)

        btn_settings = QPushButton()
        btn_settings.setIcon(IconProvider.get_icon("settings", "#94A3B8", size=13))
        btn_settings.setFixedSize(28, 28)
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.setToolTip("تنظیمات دستیار")
        btn_settings.setStyleSheet("""
            QPushButton {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1E283D; border-color: #6366F1; }
        """)
        btn_settings.clicked.connect(lambda: global_signals.navigate_to_page.emit(5))
        layout.addWidget(btn_settings)

    def set_last_sync_time(self, time_str: str):
        self.lbl_last_sync.setText(f"آخرین تحلیل خودکار: {to_persian_numbers(time_str)}")


class TodayOverviewBar(QFrame):
    """نوار افقی پیام وضعیت و ۴ کارت شاخص کلیدی روزانه"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(66)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QFrame#TodayOverviewCard {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.setObjectName("TodayOverviewCard")
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        greeting_col = QVBoxLayout()
        greeting_col.setSpacing(2)
        greeting_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_greeting = QLabel("سلام 👋")
        self.lbl_greeting.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #F8FAFC;")
        greeting_col.addWidget(self.lbl_greeting)

        self.lbl_attention = QLabel("امروز ۲ موضوع مهم نیازمند اقدام فوری شماست.")
        self.lbl_attention.setStyleSheet("font-size: 11px; color: #94A3B8;")
        greeting_col.addWidget(self.lbl_attention)

        layout.addLayout(greeting_col, stretch=2)
        layout.addWidget(self._create_v_line())

        self.kpi_proj = self._create_kpi_cell("پیشرفت پایپ‌لاین:", "۰٪", "#818CF8")
        self.kpi_fin = self._create_kpi_cell("وصول مالی:", "۰٪", "#10B981")
        self.kpi_time = self._create_kpi_cell("کارکرد امروز:", "۰۰:۰۰", "#FBBF24")
        self.kpi_tasks = self._create_kpi_cell("اقدامات معوق:", "۰ مورد", "#F87171")

        layout.addLayout(self.kpi_proj["layout"], stretch=1)
        layout.addLayout(self.kpi_fin["layout"], stretch=1)
        layout.addLayout(self.kpi_time["layout"], stretch=1)
        layout.addLayout(self.kpi_tasks["layout"], stretch=1)

    def _create_v_line(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFixedHeight(28)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        return line

    def _create_kpi_cell(self, label: str, val: str, col: str) -> dict:
        box = QVBoxLayout()
        box.setSpacing(1)
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_k = QLabel(label)
        lbl_k.setStyleSheet("font-size: 10.5px; color: #64748B;")
        box.addWidget(lbl_k)

        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"font-size: 13.5px; font-weight: 800; color: {col};")
        box.addWidget(lbl_v)

        return {"layout": box, "val_lbl": lbl_v, "key_lbl": lbl_k}

    def update_metrics(self, editor_name: str, attention_text: str, proj_pct: int, fin_pct: int, time_hms: str, tasks_cnt: int):
        self.lbl_greeting.setText(f"سلام {editor_name} 👋")
        self.lbl_attention.setText(attention_text)
        self.kpi_proj["val_lbl"].setText(f"{to_persian_numbers(proj_pct)}٪")
        self.kpi_fin["val_lbl"].setText(f"{to_persian_numbers(fin_pct)}٪")
        self.kpi_time["val_lbl"].setText(to_persian_numbers(time_hms))
        self.kpi_tasks["val_lbl"].setText(f"{to_persian_numbers(tasks_cnt)} مورد")


class MainCopilotDecisionCard(QFrame):
    """کارت اصلی تصمیم هوشمند دستیار"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
        self.setObjectName("MainCopilotCard")
        self.setStyleSheet("""
            QFrame#MainCopilotCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #151D30, stop:1 #0F1524);
                border: 1.5px solid rgba(99, 102, 241, 0.35);
                border-radius: 10px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.is_explanation_open = False
        self.current_project_id: Optional[int] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        lbl_badge = QLabel("🧠 پیشنهاد اولویت اول Copilot")
        lbl_badge.setStyleSheet("font-size: 12.5px; font-weight: 900; color: #818CF8;")
        top_row.addWidget(lbl_badge)

        self.lbl_reason_tag = QLabel("تحلیل زنده • بر مبنای ددلاین و راش‌های پروژه")
        self.lbl_reason_tag.setStyleSheet("font-size: 9.5px; color: #94A3B8; background-color: rgba(255,255,255,0.03); border-radius: 4px; padding: 2px 6px;")
        top_row.addWidget(self.lbl_reason_tag)

        top_row.addStretch()

        self.btn_why = QPushButton("چرا این پیشنهاد؟ ▾")
        self.btn_why.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_why.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 700; color: #38BDF8;
                background-color: rgba(56, 189, 248, 0.10); border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 5px; padding: 3px 8px;
            }
            QPushButton:hover { background-color: #38BDF8; color: #000; }
        """)
        self.btn_why.clicked.connect(self._toggle_why)
        top_row.addWidget(self.btn_why)

        layout.addLayout(top_row)

        self.lbl_main_insight = QLabel("در حال ارزیابی پروژه‌های فعال...")
        self.lbl_main_insight.setWordWrap(True)
        self.lbl_main_insight.setStyleSheet("font-size: 13px; font-weight: 700; color: #F8FAFC; line-height: 1.5;")
        layout.addWidget(self.lbl_main_insight)

        self.why_panel = QFrame()
        self.why_panel.setVisible(False)
        self.why_panel.setStyleSheet("""
            QFrame {
                background-color: #0E131F;
                border: 1px dashed rgba(56, 189, 248, 0.3);
                border-radius: 6px;
            }
        """)
        why_lay = QVBoxLayout(self.why_panel)
        why_lay.setContentsMargins(12, 8, 12, 8)
        why_lay.setSpacing(4)

        self.lbl_why_details = QLabel()
        self.lbl_why_details.setWordWrap(True)
        self.lbl_why_details.setStyleSheet("font-size: 11px; color: #CBD5E1; line-height: 1.4;")
        why_lay.addWidget(self.lbl_why_details)

        layout.addWidget(self.why_panel)

        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.btn_action_start = QPushButton("شروع جلسه تدوین ⏱️")
        self.btn_action_start.setFixedHeight(34)
        self.btn_action_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action_start.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #FFFFFF;
                background-color: #10B981; border: none; border-radius: 6px; padding: 0 14px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_action_start.clicked.connect(self._on_start_work)
        btn_bar.addWidget(self.btn_action_start)

        self.btn_action_nle = QPushButton("اجرای فایل NLE 🎬")
        self.btn_action_nle.setFixedHeight(34)
        self.btn_action_nle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action_nle.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: #FFFFFF;
                background-color: #6366F1; border: none; border-radius: 6px; padding: 0 14px;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        self.btn_action_nle.clicked.connect(self._on_launch_nle)
        btn_bar.addWidget(self.btn_action_nle)

        self.btn_action_view = QPushButton("مشاهده پرونده پروژه ←")
        self.btn_action_view.setFixedHeight(34)
        self.btn_action_view.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action_view.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600; color: #94A3B8;
                background-color: #161F30; border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px; padding: 0 12px;
            }
            QPushButton:hover { color: #F8FAFC; border-color: #6366F1; background-color: #1E283D; }
        """)
        self.btn_action_view.clicked.connect(self._on_view_project)
        btn_bar.addWidget(self.btn_action_view)

        btn_bar.addStretch()
        layout.addLayout(btn_bar)

    def _toggle_why(self):
        self.is_explanation_open = not self.is_explanation_open
        self.why_panel.setVisible(self.is_explanation_open)
        self.btn_why.setText("بستن توضیح ▴" if self.is_explanation_open else "چرا این پیشنهاد؟ ▾")

    def set_content(self, project_id: Optional[int], insight_text: str, why_points: List[str]):
        self.current_project_id = project_id
        self.lbl_main_insight.setText(insight_text)
        points_fmt = "<br>".join([f"• {p}" for p in why_points])
        self.lbl_why_details.setText(f"<b>مبنای محاسباتی هوش مصنوعی:</b><br>{points_fmt}")
        has_proj = project_id is not None
        self.btn_action_start.setEnabled(has_proj)
        self.btn_action_nle.setEnabled(has_proj)
        self.btn_action_view.setEnabled(has_proj)

    def _on_start_work(self):
        if self.current_project_id:
            global_signals.navigate_to_page.emit(6)

    def _on_launch_nle(self):
        if self.current_project_id:
            proj = ProjectController.get_project_by_id(self.current_project_id)
            if proj and proj.nle_project_path:
                ok, msg = NleLauncherHelper.launch_project(proj.nle_project_path)
                global_signals.show_toast.emit(msg, "success" if ok else "error")
            else:
                global_signals.show_toast.emit("فایل پروژه تدوین برای این آیتم ثبت نشده است.", "warning")

    def _on_view_project(self):
        if self.current_project_id:
            global_signals.navigate_and_focus_project.emit(self.current_project_id)


class SmartPriorityItemRow(QFrame):
    """سطر هر اولویت با بج‌های شیشه‌ای و دکمه‌های اکشن استاندارد استودیو"""
    def __init__(self, rank: str, tag: str, title: str, reason: str, action_label: str, tag_color: str, on_action_cb, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QFrame#PriorityRow {
                background-color: #141B2A;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 7px;
            }
            QFrame#PriorityRow:hover {
                background-color: #182236;
                border-color: rgba(99, 102, 241, 0.35);
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.setObjectName("PriorityRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 10, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # شماره ردیف
        lbl_rank = QLabel(to_persian_numbers(rank))
        lbl_rank.setStyleSheet("font-family: 'Segoe UI'; font-size: 11px; font-weight: 800; color: #64748B; min-width: 18px;")
        layout.addWidget(lbl_rank)

        # بج شیشه‌ای ملایم (Glass Pill Badge)
        lbl_tag = QLabel(tag)
        lbl_tag.setStyleSheet(f"""
            font-size: 9.5px;
            font-weight: 800;
            color: {tag_color};
            background-color: {tag_color}18;
            border: 1px solid {tag_color}35;
            border-radius: 4px;
            padding: 2px 8px;
        """)
        layout.addWidget(lbl_tag)

        # عنوان پروژه یا تسک
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #F8FAFC;")
        layout.addWidget(lbl_title)

        # توضیحات و دلیل اولویت
        lbl_reason = QLabel(f"({reason})")
        lbl_reason.setStyleSheet("font-size: 11px; color: #94A3B8;")
        layout.addWidget(lbl_reason, stretch=1)

        # دکمه اکشن استاندارد استودیویی CutterLog Pro
        btn_act = QPushButton(f"{action_label} ←")
        btn_act.setFixedHeight(28)
        btn_act.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_act.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                font-size: 11px;
                font-weight: 700;
                color: #F8FAFC;
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #6366F1;
                border-color: #6366F1;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #4F46E5;
            }
        """)
        btn_act.clicked.connect(on_action_cb)
        layout.addWidget(btn_act)


class SmartPrioritiesCard(QFrame):
    """کارت اولویت‌های رتبه‌بندی شده روزانه"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet("""
            QFrame#PrioritiesCardFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.setObjectName("PrioritiesCardFrame")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        lbl_t = QLabel("🎯 اولویت‌های رتبه‌بندی‌شده امروز (Smart Action Queue)")
        lbl_t.setStyleSheet("font-size: 12px; font-weight: 800; color: #F8FAFC;")
        top_row.addWidget(lbl_t)
        top_row.addStretch()

        self.lbl_count_tag = QLabel("۰ اقدام")
        self.lbl_count_tag.setStyleSheet("font-size: 10px; color: #64748B;")
        top_row.addWidget(self.lbl_count_tag)
        layout.addLayout(top_row)

        self.items_container = QVBoxLayout()
        self.items_container.setSpacing(5)
        layout.addLayout(self.items_container)

    def set_priorities(self, items: List[dict]):
        while self.items_container.count():
            w = self.items_container.takeAt(0).widget()
            if w:
                w.deleteLater()

        self.lbl_count_tag.setText(f"{to_persian_numbers(len(items))} اقدام فعال")

        if not items:
            lbl_empty = QLabel("هیچ اقدام معوق یا بحرانی برای امروز وجود ندارد؛ همه پروژه‌ها در وضعیت مطلوب هستند ✓")
            lbl_empty.setStyleSheet("font-size: 11px; color: #10B981; padding: 8px 0;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.items_container.addWidget(lbl_empty)
            return

        for p in items[:3]:
            row = SmartPriorityItemRow(
                rank=p["rank"], tag=p["tag"], title=p["title"],
                reason=p["reason"], action_label=p["action_label"],
                tag_color=p["color"], on_action_cb=p["callback"], parent=self
            )
            self.items_container.addWidget(row)


class ActiveProjectCockpitCard(QFrame):
    """کارت پروژه در دست انجام با اطلاعات فنی و پیشرفت"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet("""
            QFrame#CockpitCard {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.setObjectName("CockpitCard")
        self.project_id: Optional[int] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        head = QHBoxLayout()
        lbl_head = QLabel("🎬 پروژه فعال و در جریان تدوین")
        lbl_head.setStyleSheet("font-size: 12px; font-weight: 800; color: #818CF8;")
        head.addWidget(lbl_head)
        head.addStretch()

        self.lbl_status = QLabel("● آماده تدوین")
        self.lbl_status.setStyleSheet("font-size: 10px; font-weight: 700; color: #10B981; background: rgba(16,185,129,0.12); padding: 1px 6px; border-radius: 4px;")
        head.addWidget(self.lbl_status)
        layout.addLayout(head)

        title_row = QHBoxLayout()
        self.lbl_proj_title = QLabel("پروژه‌ای انتخاب نشده")
        self.lbl_proj_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #F8FAFC;")
        title_row.addWidget(self.lbl_proj_title)

        self.lbl_studio_name = QLabel("—")
        self.lbl_studio_name.setStyleSheet("font-size: 11px; color: #94A3B8;")
        title_row.addWidget(self.lbl_studio_name)
        title_row.addStretch()
        layout.addLayout(title_row)

        meta_grid = QGridLayout()
        meta_grid.setContentsMargins(0, 0, 0, 0)
        meta_grid.setHorizontalSpacing(14)
        meta_grid.setVerticalSpacing(4)

        self.lbl_deadline = QLabel("موعد تحویل: —")
        self.lbl_deadline.setStyleSheet("font-size: 10.5px; color: #F59E0B;")
        meta_grid.addWidget(self.lbl_deadline, 0, 0)

        self.lbl_clips_cnt = QLabel("کلیپ‌ها: ۰ از ۰")
        self.lbl_clips_cnt.setStyleSheet("font-size: 10.5px; color: #94A3B8;")
        meta_grid.addWidget(self.lbl_clips_cnt, 0, 1)

        self.lbl_total_fee = QLabel("قرارداد: ۰ تومان")
        self.lbl_total_fee.setStyleSheet("font-size: 10.5px; color: #94A3B8;")
        meta_grid.addWidget(self.lbl_total_fee, 1, 0)

        self.lbl_last_log = QLabel("آخرین رویداد: —")
        self.lbl_last_log.setStyleSheet("font-size: 10.5px; color: #64748B;")
        meta_grid.addWidget(self.lbl_last_log, 1, 1)

        layout.addLayout(meta_grid)

        pb_row = QHBoxLayout()
        pb_row.setSpacing(6)
        self.pb_proj = QProgressBar()
        self.pb_proj.setRange(0, 100)
        self.pb_proj.setValue(0)
        self.pb_proj.setTextVisible(False)
        self.pb_proj.setFixedHeight(4)
        self.pb_proj.setStyleSheet("QProgressBar { background: #161F30; border: none; border-radius: 2px; } QProgressBar::chunk { background: #6366F1; border-radius: 2px; }")
        pb_row.addWidget(self.pb_proj, stretch=1)

        self.lbl_pct = QLabel("۰٪")
        self.lbl_pct.setStyleSheet("font-size: 10.5px; font-weight: bold; color: #818CF8;")
        pb_row.addWidget(self.lbl_pct)
        layout.addLayout(pb_row)

        act_row = QHBoxLayout()
        act_row.setSpacing(6)

        btn_open_folder = QPushButton("پوشه راش‌ها 📁")
        btn_open_folder.setFixedHeight(28)
        btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_folder.setStyleSheet("background: #161F30; color: #F8FAFC; border: 1px solid rgba(255,255,255,0.08); border-radius: 5px; font-size: 10.5px; padding: 0 8px;")
        btn_open_folder.clicked.connect(self._open_folder)
        act_row.addWidget(btn_open_folder)

        btn_view_proj = QPushButton("پرونده پروژه ←")
        btn_view_proj.setFixedHeight(28)
        btn_view_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view_proj.setStyleSheet("background: #161F30; color: #818CF8; border: 1px solid rgba(99,102,241,0.3); border-radius: 5px; font-size: 10.5px; padding: 0 10px; font-weight: bold;")
        btn_view_proj.clicked.connect(self._open_project)
        act_row.addWidget(btn_view_proj)

        act_row.addStretch()
        layout.addLayout(act_row)

    def set_project_data(self, p: Optional[Project]):
        if not p:
            self.project_id = None
            self.lbl_proj_title.setText("پروژه فعالی تعریف نشده است")
            self.lbl_studio_name.setText("—")
            self.pb_proj.setValue(0)
            self.lbl_pct.setText("۰٪")
            return

        self.project_id = p.id
        self.lbl_proj_title.setText(p.couple_names or p.title)
        s_name = p.client.company if (p.client and p.client.company) else (p.client.full_name if p.client else "استودیوی عمومی")
        self.lbl_studio_name.setText(f"({s_name})")

        c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p)
        self.pb_proj.setValue(pct)
        self.lbl_pct.setText(f"{to_persian_numbers(pct)}٪")
        self.lbl_clips_cnt.setText(f"کلیپ‌ها: {to_persian_numbers(c_cnt)} از {to_persian_numbers(t_cnt)}")

        dead_str = gregorian_to_jalali(p.deadline) if p.deadline else "ثبت‌نشده"
        self.lbl_deadline.setText(f"موعد تحویل: {to_persian_numbers(dead_str)}")
        self.lbl_total_fee.setText(f"قرارداد: {format_toman(p.total_fee)}")

        s_info = ProjectController.get_status_info(p)
        self.lbl_status.setText(s_info.get("label", "در حال تدوین"))

        try:
            with db.get_session() as session:
                last_log = session.scalars(
                    select(ProjectEventLog)
                    .where(ProjectEventLog.project_id == p.id)
                    .order_by(ProjectEventLog.created_at.desc())
                    .limit(1)
                ).first()
                if last_log:
                    self.lbl_last_log.setText(f"آخرین رویداد: {last_log.title}")
                else:
                    self.lbl_last_log.setText("آخرین رویداد: ایجاد پرونده")
        except Exception:
            self.lbl_last_log.setText("آخرین رویداد: در حال تدوین")

    def _open_folder(self):
        if self.project_id:
            p = ProjectController.get_project_by_id(self.project_id)
            if p and p.drive_locations and Path(p.drive_locations[0].absolute_path).exists():
                from config import open_path_in_os
                open_path_in_os(p.drive_locations[0].absolute_path)
            else:
                global_signals.show_toast.emit("مسیر پوشه راش‌ها متصل نیست.", "error")

    def _open_project(self):
        if self.project_id:
            global_signals.navigate_and_focus_project.emit(self.project_id)


class TodayInsightsCompactGrid(QFrame):
    """کارت‌های بینش مدیریتی امروز و یادداشت سریع"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
        self.setStyleSheet("""
            QFrame#InsightsFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.setObjectName("InsightsFrame")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        lbl_t = QLabel("💡 بینش‌های مدیریتی امروز")
        lbl_t.setStyleSheet("font-size: 12px; font-weight: 800; color: #10B981;")
        top_row.addWidget(lbl_t)
        top_row.addStretch()

        btn_quick_note = QPushButton("+ یادداشت سریع")
        btn_quick_note.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_quick_note.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: bold; color: #A5B4FC;
                background-color: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 5px; padding: 3px 8px;
            }
            QPushButton:hover { background-color: #6366F1; color: #FFFFFF; }
        """)
        btn_quick_note.clicked.connect(self._open_quick_note_modal)
        top_row.addWidget(btn_quick_note)
        layout.addLayout(top_row)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(6)

        self.cell_time = self._create_tile("زمان خالص تدوین", "۰:۰۰", "#10B981")
        self.cell_peak = self._create_tile("ساعات اوج سرعت", "۱۶ تا ۱۹", "#818CF8")
        self.cell_debts = self._create_tile("مطالبات وصول‌نشده", "۰ تومان", "#F59E0B")
        self.cell_pace = self._create_tile("پایپ‌لاین هفتگی", "تارگت ۳۶ ساعت", "#38BDF8")

        self.grid.addWidget(self.cell_time["frame"], 0, 0)
        self.grid.addWidget(self.cell_peak["frame"], 0, 1)
        self.grid.addWidget(self.cell_debts["frame"], 1, 0)
        self.grid.addWidget(self.cell_pace["frame"], 1, 1)

        layout.addLayout(self.grid)

    def _create_tile(self, title: str, val: str, col: str) -> dict:
        frame = QFrame()
        frame.setStyleSheet("background-color: #161F30; border-radius: 6px; border: 1px solid rgba(255,255,255,0.04);")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_k = QLabel(title)
        lbl_k.setStyleSheet("font-size: 10px; color: #94A3B8;")
        lay.addWidget(lbl_k)

        lbl_v = QLabel(val)
        lbl_v.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {col};")
        lay.addWidget(lbl_v)

        return {"frame": frame, "val_lbl": lbl_v, "key_lbl": lbl_k}

    def _open_quick_note_modal(self):
        settings = SettingsManager.load_settings()
        cur_text = settings.get("copilot_scratchpad_text", "")
        text, ok = StudioInputDialog.get_text(
            self.window(), "یادداشت سریع میز کار", "تایم‌کدها یا نکات ضروری تدوین:", initial_text=cur_text, placeholder="تایم‌کدها، نام موزیک و..."
        )
        if ok:
            settings["copilot_scratchpad_text"] = text
            SettingsManager.save_settings(settings)
            global_signals.show_toast.emit("یادداشت با موفقیت ذخیره شد.", "success")

    def update_insights(self, active_hms: str, peak_hours: str, uncollected_toman: str, weekly_summary: str):
        self.cell_time["val_lbl"].setText(to_persian_numbers(active_hms))
        self.cell_peak["val_lbl"].setText(to_persian_numbers(peak_hours))
        self.cell_debts["val_lbl"].setText(uncollected_toman)
        self.cell_pace["val_lbl"].setText(to_persian_numbers(weekly_summary))


class ActivityFeedAndSystemFooter(QFrame):
    """نوار زیرین ترکیبی رویدادها و وضعیت سخت‌افزار"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QFrame#FeedFooter {
                background-color: #0E131F;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.setObjectName("FeedFooter")
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_icon = QLabel("🕒")
        lbl_icon.setStyleSheet("font-size: 11px;")
        layout.addWidget(lbl_icon)

        lbl_t = QLabel("آخرین رویدادهای پایپ‌لاین:")
        lbl_t.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748B;")
        layout.addWidget(lbl_t)

        self.lbl_feed_text = QLabel("در حال دریافت تاریخچه فعالیت‌ها...")
        self.lbl_feed_text.setStyleSheet("font-size: 11px; color: #CBD5E1;")
        layout.addWidget(self.lbl_feed_text, stretch=1)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFixedHeight(20)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.06); border: none;")
        layout.addWidget(div)

        self.lbl_sys_status = QLabel("● سیستم پایدار")
        self.lbl_sys_status.setStyleSheet("font-size: 10px; font-weight: bold; color: #10B981;")
        layout.addWidget(self.lbl_sys_status)

        self.lbl_hw_specs = QLabel("CPU: ۰٪  |  GPU: ۰٪  |  RAM: ۰٪")
        self.lbl_hw_specs.setStyleSheet("font-family: 'Segoe UI', 'Vazirmatn'; font-size: 10px; color: #94A3B8;")
        layout.addWidget(self.lbl_hw_specs)

    def set_feed_items(self, items: List[str]):
        if items:
            self.lbl_feed_text.setText("   •   ".join(items[:2]))
        else:
            self.lbl_feed_text.setText("هنوز رویدادی ثبت نشده است.")

    def update_hardware(self, cpu: int, gpu: int, ram: int, is_rendering: bool):
        if is_rendering:
            self.lbl_sys_status.setText("⚡ رندر فعال")
            self.lbl_sys_status.setStyleSheet("font-size: 10px; font-weight: bold; color: #38BDF8;")
        else:
            self.lbl_sys_status.setText("● سیستم پایدار")
            self.lbl_sys_status.setStyleSheet("font-size: 10px; font-weight: bold; color: #10B981;")

        specs_str = f"CPU: {to_persian_numbers(cpu)}٪  |  GPU: {to_persian_numbers(gpu)}٪  |  RAM: {to_persian_numbers(ram)}٪"
        self.lbl_hw_specs.setText(specs_str)


class CopilotView(QWidget):
    """
    نمای مدرن و بازطراحی‌شده مرکز فرماندهی هوشمند تدوین (Smart Command Center)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()
        self._connect_signals()
        self._setup_auto_refresh_timer()
        self.refresh_data()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(20, 14, 20, 14)
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ۱. Header
        self.header_bar = CommandHeaderBar(self)
        self.layout.addWidget(self.header_bar)

        # ۲. Today Status & KPIs
        self.overview_bar = TodayOverviewBar(self)
        self.layout.addWidget(self.overview_bar)

        # ۳. Main Copilot Command Center
        self.main_copilot = MainCopilotDecisionCard(self)
        self.layout.addWidget(self.main_copilot)

        # ۴. Priorities / Action Queue
        self.priorities_card = SmartPrioritiesCard(self)
        self.layout.addWidget(self.priorities_card)

        # ۵. Dual Section: Active Project + Today Insights
        mid_grid = QHBoxLayout()
        mid_grid.setSpacing(10)

        self.cockpit_card = ActiveProjectCockpitCard(self)
        mid_grid.addWidget(self.cockpit_card, stretch=3)

        self.insights_grid = TodayInsightsCompactGrid(self)
        mid_grid.addWidget(self.insights_grid, stretch=2)

        self.layout.addLayout(mid_grid)

        # ۶. Bottom Activity Feed & System Mini Status
        self.feed_footer = ActivityFeedAndSystemFooter(self)
        self.layout.addWidget(self.feed_footer)

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _setup_auto_refresh_timer(self):
        self.auto_timer = QTimer(self)
        self.auto_timer.setInterval(20000)
        self.auto_timer.timeout.connect(self.refresh_data)
        self.auto_timer.start()

    def _connect_signals(self):
        trigger = lambda *args: QTimer.singleShot(40, self.refresh_data)
        global_signals.project_created.connect(trigger)
        global_signals.project_updated.connect(trigger)
        global_signals.project_deleted.connect(trigger)
        global_signals.project_archived.connect(trigger)
        global_signals.transaction_recorded.connect(trigger)
        global_signals.session_started.connect(trigger)
        global_signals.session_ended.connect(trigger)
        global_signals.system_activity_updated.connect(self._on_hw_metrics)

    def _on_hw_metrics(self, data: dict):
        cpu = int(data.get("cpu_percent", 0))
        gpu = int(data.get("gpu_percent", 0))
        ram = int(data.get("ram_percent", 0))
        is_rend = data.get("is_rendering", False)
        self.feed_footer.update_hardware(cpu, gpu, ram, is_rend)

    def refresh_data(self):
        settings = SettingsManager.load_settings()
        editor_name = settings.get("editor_name") or "تدوین‌گر"

        prod = CopilotEngine.get_productivity_insights(days_back=14)
        radar = CopilotEngine.get_pipeline_radar()
        rec_proj = CopilotEngine.recommend_next_project()
        fin_data = FinanceController.get_financial_dashboard_data()
        scores = CopilotEngine.get_studio_credit_scores()
        active_projects = ProjectController.get_active_projects()

        now = datetime.now()
        self.header_bar.set_last_sync_time(now.strftime("%H:%M"))

        cards = fin_data.get("summary_cards", {})
        total_contracts = cards.get("total_contracts", 0)
        total_received = cards.get("total_received", 0)
        total_remaining = cards.get("total_remaining", 0)
        fin_pct = int((total_received / total_contracts) * 100) if total_contracts > 0 else 100

        total_clips = sum(len(p.clips) for p in active_projects)
        completed_clips = sum(sum(1 for c in p.clips if c.is_completed) for p in active_projects)
        pipeline_pct = int((completed_clips / total_clips) * 100) if total_clips > 0 else 0

        from time_tracking.timer_engine import TimeTrackingEngine
        today_sec = TimeTrackingEngine.instance().get_today_total_active_seconds()
        t_h = today_sec // 3600
        t_m = (today_sec % 3600) // 60
        time_str = f"{t_h:02d}:{t_m:02d}"

        risks_cnt = radar.get("total_risks_count", 0)
        attention_text = f"امروز {to_persian_numbers(risks_cnt)} موضوع نیازمند توجه است." if risks_cnt > 0 else "پایپ‌لاین در سلامت کامل و بدون ریسک قرار دارد ✓"

        # ۱. بروزرسانی نوار بالایی
        self.overview_bar.update_metrics(
            editor_name=editor_name,
            attention_text=attention_text,
            proj_pct=pipeline_pct,
            fin_pct=fin_pct,
            time_hms=time_str,
            tasks_cnt=risks_cnt
        )

        # ۲. تصمیم‌گیری مغز اصلی Copilot
        if rec_proj:
            insight = f"پروژه «{rec_proj['title']}» آماده شروع تدوین است؛ {rec_proj['recommendation_reason']}."
            why_list = [
                f"استودیو: {rec_proj['studio_name']}",
                f"پیشرفت کلیپ‌ها: {to_persian_numbers(rec_proj['progress_pct'])}٪",
                f"موعد تحویل: {to_persian_numbers(rec_proj['deadline_str'])}",
                "ساعت طلایی بازدهی تدوینگر در حال حاضر فعال است"
            ]
            self.main_copilot.set_content(rec_proj["project_id"], insight, why_list)
        else:
            self.main_copilot.set_content(
                None,
                "تمام پروژه‌های فعال تکمیل شده‌اند یا پروژه‌ای در پایپ‌لاین نیست.",
                ["هیچ اصلاحیه بازی ثبت نشده است", "تمامی راش‌های اولیه تدوین شده‌اند"]
            )

        # ۳. ساخت صف اولویت‌های هوشمند با بج‌های ملایم و دکمه‌های تم استودیو
        p_list = []
        rank_idx = 1

        if radar.get("urgent_deadlines"):
            u = radar["urgent_deadlines"][0]
            p_list.append({
                "rank": f"{rank_idx:02d}", "tag": "فوری", "title": f"ددلاین «{u['title']}»",
                "reason": u["warning"], "action_label": "مشاهده پروژه", "color": "#EF4444",
                "callback": lambda pid=u["id"]: global_signals.navigate_and_focus_project.emit(pid)
            })
            rank_idx += 1

        if rec_proj:
            p_list.append({
                "rank": f"{rank_idx:02d}", "tag": "مهم", "title": f"ادامه تدوین «{rec_proj['title']}»",
                "reason": rec_proj["recommendation_reason"], "action_label": "شروع کات", "color": "#F59E0B",
                "callback": lambda pid=rec_proj["project_id"]: global_signals.navigate_and_focus_project.emit(pid)
            })
            rank_idx += 1

        if total_remaining > 0 and scores:
            bad_client = scores[0]
            p_list.append({
                "rank": f"{rank_idx:02d}", "tag": "پیگیری مالی", "title": f"تسویه مطالبات {bad_client['studio_name']}",
                "reason": f"مانده حساب: {format_toman(bad_client['remaining'])}", "action_label": "دفتر مالی", "color": "#10B981",
                "callback": lambda: global_signals.navigate_to_page.emit(3)
            })
            rank_idx += 1

        self.priorities_card.set_priorities(p_list)

        # ۴. پروژه در دست انجام
        if active_projects:
            active_p = active_projects[0]
            self.cockpit_card.set_project_data(active_p)
        else:
            self.cockpit_card.set_project_data(None)

        # ۵. بینش‌های فشرده مدیریتی
        peak = prod.get("golden_hours_label", "۱۶ تا ۱۹")
        debt_str = format_toman(total_remaining) if total_remaining > 0 else "حساب‌ها تسویه ✓"
        self.insights_grid.update_insights(
            active_hms=f"{t_h} ساعت و {t_m} دقیقه",
            peak_hours=peak,
            uncollected_toman=debt_str,
            weekly_summary="۳۶ ساعت هفتگی"
        )

        # ۶. لاگ‌های اخیر فعالیت
        try:
            with db.get_session() as session:
                logs = session.scalars(select(ProjectEventLog).order_by(ProjectEventLog.created_at.desc()).limit(3)).all()
                feed_items = []
                for l in logs:
                    t_str = l.created_at.strftime("%H:%M") if l.created_at else "--:--"
                    feed_items.append(f"{to_persian_numbers(t_str)} {l.title}")
                self.feed_footer.set_feed_items(feed_items)
        except Exception:
            self.feed_footer.set_feed_items([])