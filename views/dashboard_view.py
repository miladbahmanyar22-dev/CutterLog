# ==================================================
# FILE: views/dashboard_view.py
# ==================================================
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QScrollArea, QFrame, QGridLayout, QPushButton, QComboBox
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
from core.copilot_engine import CopilotEngine
from core.persian_utils import to_persian_numbers, format_studio_title
from core.icon_provider import IconProvider
from core.signals import global_signals


class DashboardFilterPill(QPushButton):
    """
    دکمه کپسولی فیلتر با کادر مشخص در حالت عادی و تغییر رنگ تمیز در حالت کلیک‌شده
    با ابعاد کاملاً قفل‌شده و بدون کوچک‌ترین لرزش یا پرش سایز (Zero-Jitter)
    """
    def __init__(self, title: str, filter_key: str, count: int = 0, color_hex: str = "#818CF8", parent=None):
        super().__init__(parent)
        self.filter_key = filter_key
        self.base_title = title
        self.color_hex = color_hex
        self.count = count

        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)
        self.update_text_and_style()

    def set_count(self, count: int):
        self.count = count
        self.update_text_and_style()

    def update_text_and_style(self):
        cnt_part = f" ({to_persian_numbers(self.count)})" if self.count > 0 else ""
        self.setText(f"{self.base_title}{cnt_part}")

        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    font-family: 'Vazirmatn';
                    font-size: 11px;
                    font-weight: 700;
                    background-color: {self.color_hex};
                    color: #FFFFFF;
                    border: 1px solid {self.color_hex};
                    border-radius: 6px;
                    padding: 0 12px;
                }}
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    font-size: 11px;
                    font-weight: 700;
                    background-color: #121826;
                    color: #94A3B8;
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-radius: 6px;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    background-color: #1A2438;
                    color: #F8FAFC;
                    border-color: rgba(255, 255, 255, 0.25);
                }
            """)


class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.active_filter_key = "urgent"  # پیش‌فرض: کارهای فوری و نزدیک‌ترین سررسیدها
        self.filter_pills = {}
        self.current_nle_window_title = ""

        self.init_ui()
        self._connect_signals()
        self._load_studios_filter()
        self.refresh_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 18, 28, 16)
        main_layout.setSpacing(12)

        # ۱. سربرگ خوش‌آمدگویی و کارت هوشمند کوپایلوت
        top_bar_row = QHBoxLayout()
        top_bar_row.setSpacing(14)

        self.welcome_header = DashboardWelcomeHeader(self)
        top_bar_row.addWidget(self.welcome_header, stretch=3)

        self.copilot_card = CopilotBriefingCard(self)
        self.copilot_card.open_insights_requested.connect(lambda: global_signals.navigate_to_page.emit(7))
        top_bar_row.addWidget(self.copilot_card, stretch=2)

        main_layout.addLayout(top_bar_row)

        # ۲. دراپ‌زون آنالیز سریع فوتج
        self.media_drop_zone = MediaInspectorDropZone(self)
        main_layout.addWidget(self.media_drop_zone)

        # ۳. کارت‌های شاخص چهارگانه مالی و پروژه‌ای
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

        # ۴. نوار فیلتر و اولویت پیشخوان
        self.filter_bar = self._build_filter_bar()
        main_layout.addWidget(self.filter_bar)

        # ۵. کانتینر اسکرول کارت‌های پروژه
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
        self.content_layout.setSpacing(14)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.content_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

    def _build_filter_bar(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: #0E1322;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            QLabel {
                font-family: 'Vazirmatn';
                color: #8F909D;
                font-size: 11px;
                font-weight: 700;
                background: transparent;
                border: none;
            }
            QComboBox {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 2px 8px;
                color: #F8FAFC;
                font-size: 11px;
                font-weight: 600;
            }
            QComboBox:hover {
                border-color: #6366F1;
            }
        """)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconProvider.get_pixmap("filter", "#818CF8", size=13))
        lay.addWidget(lbl_icon)

        lbl_text = QLabel("اولویت پیشخوان:")
        lay.addWidget(lbl_text)

        pills_spec = [
            ("نزدیک‌ترین ددلاین ", "urgent", "#FFA200"),
            ("اصلاحیه فعال ", "revision", "#FF5900"),
            ("در حال کات ", "cutting", "#5154FA"),
            ("آماده تحویل ", "ready", "#01E79A"),
            ("همه پروژه‌ها", "all", "#16A7E6")
        ]

        for title, key, col in pills_spec:
            pill = DashboardFilterPill(title, key, count=0, color_hex=col, parent=self)
            if key == self.active_filter_key:
                pill.setChecked(True)
                pill.update_text_and_style()
            pill.clicked.connect(lambda _, k=key: self._on_filter_pill_clicked(k))
            lay.addWidget(pill)
            self.filter_pills[key] = pill

        lay.addStretch(1)

        lbl_studio = QLabel("استودیو:")
        lay.addWidget(lbl_studio)

        self.combo_studio = QComboBox()
        self.combo_studio.setFixedHeight(28)
        self.combo_studio.setMinimumWidth(150)
        self.combo_studio.addItem("همه استودیوها", 0)
        self.combo_studio.currentIndexChanged.connect(self.refresh_data)
        lay.addWidget(self.combo_studio)

        return bar

    def _load_studios_filter(self):
        current_id = self.combo_studio.currentData() if hasattr(self, "combo_studio") else 0
        self.combo_studio.blockSignals(True)
        self.combo_studio.clear()
        self.combo_studio.addItem("همه استودیوها", 0)

        projects = ProjectController.get_active_projects()
        studios_map = {}
        for p in projects:
            if p.client_id:
                name = p.client.company if p.client.company else p.client.full_name
                studios_map[p.client_id] = name

        for c_id, name in sorted(studios_map.items(), key=lambda x: str(x[1])):
            self.combo_studio.addItem(format_studio_title(name), c_id)

        idx = self.combo_studio.findData(current_id)
        if idx >= 0:
            self.combo_studio.setCurrentIndex(idx)
        self.combo_studio.blockSignals(False)

    def _on_filter_pill_clicked(self, clicked_key: str):
        self.active_filter_key = clicked_key
        for key, pill in self.filter_pills.items():
            pill.setChecked(key == clicked_key)
            pill.update_text_and_style()
        self.refresh_data()

    def _sort_projects_smart(self, projects: list) -> list:
        """
        مرتب‌سازی پروژه‌ها بر اساس خروجی ماتریس وزنی هوشمند CopilotEngine
        بدون تغییر ساختار ویجت‌ها، اولویت‌دارترین موارد همیشه در صدر قرار می‌گیرند.
        """
        scored_projects = []
        for p in projects:
            matrix = CopilotEngine.calculate_project_priority_matrix(
                p, 
                current_active_title=self.current_nle_window_title
            )
            scored_projects.append((matrix["score"], p))

        # مرتب‌سازی نزولی (بیشترین امتیاز در ابتدای صف)
        scored_projects.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored_projects]

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
        global_signals.system_activity_updated.connect(self._on_system_activity_update)

    def _on_system_activity_update(self, data: dict):
        """دریافت نام پنجره و فوکوس NLE برای ترنزیشن زنده اولویت‌ها"""
        new_title = data.get("window_title", "")
        if data.get("is_core_nle", False) and new_title and new_title != self.current_nle_window_title:
            self.current_nle_window_title = new_title
            # به‌روزرسانی نامحسوس ترتیب بدون لرزش
            QTimer.singleShot(50, self.refresh_data)

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

        raw_projects = ProjectController.get_active_projects()
        if not raw_projects:
            empty_widget = ModernEmptyStateWidget(
                title="هیچ پروژه فعالی در پایپ‌لاین ثبت نشده است",
                description="میز کار شما در حال حاضر خالی است. برای شروع می‌توانید پروژه جدیدی تعریف کنید.",
                button_text="+ تعریف اولین پروژه",
                icon_name="folder"
            )
            empty_widget.action_clicked.connect(lambda: global_signals.navigate_to_page.emit(1))
            self.content_layout.addWidget(empty_widget)
            return

        now_dt = datetime.utcnow().date()
        counts = {"urgent": 0, "revision": 0, "cutting": 0, "ready": 0, "all": len(raw_projects)}

        for p in raw_projects:
            active_rev = ProjectController.get_active_revision(p)
            c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p)
            status_info = ProjectController.get_status_info(p)
            status_key = status_info.get("key", "")

            if active_rev:
                counts["revision"] += 1
            elif pct >= 100 or status_key in ["under_review", "ready_for_delivery"]:
                counts["ready"] += 1
            else:
                counts["cutting"] += 1

            if p.deadline and pct < 100:
                delta = (p.deadline.date() - now_dt).days
                if delta <= 3:
                    counts["urgent"] += 1

        for k, pill in self.filter_pills.items():
            pill.set_count(counts.get(k, 0))

        # فیلتر بر اساس استودیو
        selected_client_id = self.combo_studio.currentData() if hasattr(self, "combo_studio") else 0
        if selected_client_id and selected_client_id > 0:
            filtered_projects = [p for p in raw_projects if p.client_id == selected_client_id]
        else:
            filtered_projects = raw_projects

        # اعمال فیلتر کپسولی انتخابی
        if self.active_filter_key == "urgent":
            urgent_set = []
            for p in filtered_projects:
                c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p)
                if p.deadline and pct < 100:
                    delta = (p.deadline.date() - now_dt).days
                    if delta <= 5:
                        urgent_set.append(p)
            filtered_projects = urgent_set if urgent_set else filtered_projects
        elif self.active_filter_key == "revision":
            filtered_projects = [p for p in filtered_projects if ProjectController.get_active_revision(p)]
        elif self.active_filter_key == "cutting":
            filtered_projects = [
                p for p in filtered_projects 
                if not ProjectController.get_active_revision(p) and ProjectController.calculate_project_progress(p)[2] < 100
            ]
        elif self.active_filter_key == "ready":
            filtered_projects = [
                p for p in filtered_projects 
                if ProjectController.calculate_project_progress(p)[2] >= 100 or ProjectController.get_status_info(p).get("key") in ["ready_for_delivery", "under_review"]
            ]

        # مرتب‌سازی هوشمند اولویت‌ها بر مبنای ماتریس وزنی CopilotEngine
        sorted_projects = self._sort_projects_smart(filtered_projects)

        if not sorted_projects:
            lbl_empty = QLabel("پروژه‌ای مطابق با فیلتر انتخابی یافت نشد.")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #64748B; padding: 40px 0;")
            self.content_layout.addWidget(lbl_empty)
            return

        self._build_section_grid("🎬 پروژه‌های اولویت‌دار پیشخوان", sorted_projects, "#6366F1")

    def _build_section_grid(self, title: str, projects_list: list, accent_color: str):
        sec_widget = QWidget()
        sec_lay = QVBoxLayout(sec_widget)
        sec_lay.setContentsMargins(0, 0, 0, 0)
        sec_lay.setSpacing(8)

        sec_header = QHBoxLayout()
        count_str = f"({to_persian_numbers(len(projects_list))} پروژه اولویت‌دار)"
        lbl_sec = QLabel(f"{title} <span style='font-size: 11px; font-weight: normal; color: #8F909D;'>{count_str}</span>")
        lbl_sec.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: {accent_color}; border: none; background: transparent;")
        sec_header.addWidget(lbl_sec, stretch=1)

        btn_all = QPushButton("مشاهده همه در تب پروژه‌ها ←")
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

            raw_client = p.client.company if (p.client and p.client.company) else (p.client.full_name if p.client else "")
            client_display = format_studio_title(raw_client) if raw_client else "بدون استودیو"

            p_dict = {
                "id": p.id,
                "project_number": p.project_number or p.id,
                "couple_names": p.couple_names,
                "title": p.title,
                "client_name": client_display,
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
                "status_info": status_info,
                "primary_path": p.drive_locations[0].absolute_path if p.drive_locations else None,
                "nle_project_path": p.nle_project_path
            }
            card = ProjectCardMini(p_dict)
            row = index // 3
            col = index % 3
            grid.addWidget(card, row, col, 1, 1)

        sec_lay.addWidget(grid_widget)
        self.content_layout.addWidget(sec_widget)