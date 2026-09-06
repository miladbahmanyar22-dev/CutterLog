# ==================================================
# FILE: views/dashboard_view.py
# ==================================================
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QGridLayout, QPushButton
)
from PySide6.QtCore import Qt, QTimer

from widgets.stat_card import StatCard
from widgets.project_card_mini import ProjectCardMini
from widgets.empty_state import ModernEmptyStateWidget
from widgets.dashboard_welcome_header import DashboardWelcomeHeader
from widgets.media_inspector_widget import MediaInspectorDropZone
from widgets.copilot_briefing_card import CopilotBriefingCard

from core.finance_controller import FinanceController
from core.project_controller import ProjectController
from core.persian_utils import to_persian_numbers
from core.signals import global_signals


class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()
        self._connect_signals()
        self.refresh_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 18, 28, 16)
        main_layout.setSpacing(14)

        # ۱. سطر ترکیبی اول: خوش‌آمدگویی/ساعت (راست) + دستیار هوشمند خلاصه (چپ)
        top_bar_row = QHBoxLayout()
        top_bar_row.setSpacing(14)

        self.welcome_header = DashboardWelcomeHeader(self)
        top_bar_row.addWidget(self.welcome_header, stretch=3)

        self.copilot_card = CopilotBriefingCard(self)
        # هدایت مستقیم به صفحه کامل دستیار هوشمند (ایندکس ۷)
        self.copilot_card.open_insights_requested.connect(lambda: global_signals.navigate_to_page.emit(7))
        top_bar_row.addWidget(self.copilot_card, stretch=2)

        main_layout.addLayout(top_bar_row)

        # ۲. کارت آنالیزور سریع فوتج (Media Inspector)
        self.media_drop_zone = MediaInspectorDropZone(self)
        main_layout.addWidget(self.media_drop_zone)

        # ۳. کارت‌های شاخص آماری (KPIs)
        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(10)

        self.card_revenue = StatCard(title="کل درآمد وصول‌شده", initial_value=0, is_currency=True, color_accent="#10B981")
        self.card_pipeline = StatCard(title="ارزش پروژه‌های فعال", initial_value=0, is_currency=True, color_accent="#6366F1")
        self.card_active = StatCard(title="پروژه‌های در حال تدوین", initial_value=0, is_currency=False, color_accent="#38BDF8")
        self.card_reviews = StatCard(title="منتظر تایید / بازبینی", initial_value=0, is_currency=False, color_accent="#F59E0B")

        self.stats_layout.addWidget(self.card_revenue)
        self.stats_layout.addWidget(self.card_pipeline)
        self.stats_layout.addWidget(self.card_active)
        self.stats_layout.addWidget(self.card_reviews)
        main_layout.addLayout(self.stats_layout)

        # ۴. کانتینر اسکرول محتوای پروژه‌ها
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.content_container = QWidget()
        self.content_container.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 4, 0, 10)
        self.content_layout.setSpacing(18)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.content_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

    def _connect_signals(self):
        trigger = lambda *args: QTimer.singleShot(0, self.refresh_data)
        global_signals.project_created.connect(trigger)
        global_signals.project_updated.connect(trigger)
        global_signals.stage_changed.connect(trigger)
        global_signals.clip_status_toggled.connect(trigger)
        global_signals.revision_added.connect(trigger)
        global_signals.revision_updated.connect(trigger)
        global_signals.revision_task_toggled.connect(trigger)
        global_signals.project_deleted.connect(trigger)
        global_signals.project_archived.connect(trigger)
        global_signals.project_unarchived.connect(trigger)
        global_signals.transaction_recorded.connect(trigger)
        global_signals.session_started.connect(trigger)
        global_signals.session_ended.connect(trigger)
        global_signals.settings_updated.connect(lambda: self.welcome_header.update_all())

    def refresh_data(self):
        self.welcome_header.update_all()
        if hasattr(self, "copilot_card"):
            self.copilot_card.refresh_briefing()

        metrics = FinanceController.get_dashboard_metrics()
        self.card_revenue.animate_to_value(metrics["total_revenue"])
        self.card_pipeline.animate_to_value(metrics["active_pipeline_value"])
        self.card_active.animate_to_value(metrics["active_projects_count"])
        self.card_reviews.animate_to_value(metrics["review_count"])

        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        projects = ProjectController.get_active_projects()
        if not projects:
            empty_widget = ModernEmptyStateWidget(
                title="هیچ پروژه فعالی در پایپ‌لاین ثبت نشده است",
                description="میز کار شما در حال حاضر خالی است. برای شروع می‌توانید پروژه جدیدی تعریف کنید.",
                button_text="+ تعریف اولین پروژه",
                icon_name="folder"
            )
            empty_widget.action_clicked.connect(lambda: global_signals.navigate_to_page.emit(1))
            self.content_layout.addWidget(empty_widget)
            return

        urgent_projects = []
        review_projects = []
        active_projects = []

        for p in projects:
            active_rev = ProjectController.get_active_revision(p)
            c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p)
            
            if active_rev:
                urgent_projects.append(p)
            elif t_cnt > 0 and c_cnt == t_cnt:
                review_projects.append(p)
            else:
                active_projects.append(p)

        if urgent_projects:
            self._build_section("⚡ اقدامات فوری و اصلاحیه‌های فعال", urgent_projects, "#EA580C")
        if active_projects:
            self._build_section("🎬 پایپ‌لاین پروژه‌های در حال تدوین", active_projects, "#6366F1")
        if review_projects:
            self._build_section("⏳ منتظر بازبینی استودیو / آماده تحویل نهایی", review_projects, "#F59E0B")

    def _build_section(self, title: str, projects_list: list, accent_color: str):
        sec_widget = QWidget()
        sec_lay = QVBoxLayout(sec_widget)
        sec_lay.setContentsMargins(0, 0, 0, 0)
        sec_lay.setSpacing(8)

        sec_header = QHBoxLayout()
        count_str = f"({to_persian_numbers(len(projects_list))} پروژه)"
        lbl_sec = QLabel(f"{title} <span style='font-size: 11px; font-weight: normal; color: #8F909D;'>{count_str}</span>")
        lbl_sec.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: {accent_color}; border: none; background: transparent;")
        sec_header.addWidget(lbl_sec, stretch=1)

        btn_all = QPushButton("مشاهده در پروژه‌ها ←")
        btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_all.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background: transparent;
                color: #818CF8;
                border: none;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { color: #A5B4FC; }
        """)
        btn_all.clicked.connect(lambda: global_signals.navigate_to_page.emit(1))
        sec_header.addWidget(btn_all)
        sec_lay.addLayout(sec_header)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        for index, p in enumerate(projects_list):
            completed_cnt, total_cnt, pct = ProjectController.calculate_project_progress(p)
            fin = ProjectController.get_project_financial_summary(p)
            active_rev = ProjectController.get_active_revision(p)
            rev_c, rev_t, rev_pct = ProjectController.calculate_revision_progress(active_rev) if active_rev else (0, 0, 0)
            status_info = ProjectController.get_status_info(p)

            clips_data = [
                {
                    "id": c.id,
                    "name": c.clip_name,
                    "is_completed": c.is_completed,
                    "completed_at": c.completed_at
                }
                for c in p.clips
            ]

            p_dict = {
                "id": p.id,
                "project_number": p.project_number or p.id,
                "couple_names": p.couple_names,
                "title": p.title,
                "client_name": p.client.company if (p.client and p.client.company) else (p.client.full_name if p.client else "بدون استودیو"),
                "current_stage": p.current_stage.value if hasattr(p.current_stage, "value") else str(p.current_stage),
                "deadline": p.deadline,
                "event_date": p.event_date,
                "total_fee": fin["total_fee"],
                "remaining_amount": fin["remaining"],
                "is_settled": fin["is_settled"],
                "progress_pct": pct,
                "completed_clips": completed_cnt,
                "total_clips": total_cnt,
                "clips_list": clips_data,
                "active_revision_title": active_rev.title if active_rev else None,
                "rev_progress_pct": rev_pct,
                "rev_completed_tasks": rev_c,
                "rev_total_tasks": rev_t,
                "status_info": status_info
            }
            card = ProjectCardMini(p_dict)
            row = index // 3
            col = index % 3
            grid.addWidget(card, row, col, 1, 1)

        sec_lay.addWidget(grid_widget)
        self.content_layout.addWidget(sec_widget)