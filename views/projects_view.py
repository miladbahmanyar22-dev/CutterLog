# ==================================================
# FILE: views/projects_view.py
# ==================================================
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QScrollArea, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, QSize

from widgets.project_card import ProjectCard
from widgets.new_project_dialog import NewProjectDialog
from widgets.header_summary_pill import HeaderSummaryPill
from widgets.empty_state import ModernEmptyStateWidget
from core.project_controller import ProjectController
from core.settings_manager import SettingsManager
from core.persian_utils import to_persian_numbers
from core.icon_provider import IconProvider
from core.signals import global_signals


class StudioFilterPillButton(QPushButton):
    def __init__(self, title: str, filter_key: str, icon_name: str, color_hex: str = "#818CF8", parent=None):
        super().__init__(parent)
        self.filter_key = filter_key
        self.icon_name = icon_name
        self.color_hex = color_hex
        self.base_title = title
        self.count = 0

        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self.setIconSize(QSize(13, 13))
        self.update_appearance()

    def set_count(self, count: int):
        self.count = count
        cnt_str = f" ({to_persian_numbers(count)})" if count > 0 else ""
        self.setText(f" {self.base_title}{cnt_str}")
        self.setEnabled(count > 0 or self.isChecked())
        self.update_appearance()

    def update_appearance(self):
        if self.isChecked():
            self.setIcon(IconProvider.get_icon(self.icon_name, "#FFFFFF", size=13))
            self.setStyleSheet(f"""
                QPushButton {{
                    font-family: 'Vazirmatn';
                    font-size: 11.5px;
                    font-weight: 700;
                    background-color: {self.color_hex};
                    color: #FFFFFF;
                    border: 1px solid {self.color_hex};
                    border-radius: 7px;
                    padding: 0 12px;
                }}
            """)
        else:
            icon_color = self.color_hex if self.count > 0 else "#64748B"
            text_color = "#F8FAFC" if self.count > 0 else "#64748B"
            self.setIcon(IconProvider.get_icon(self.icon_name, icon_color, size=13))
            self.setStyleSheet(f"""
                QPushButton {{
                    font-family: 'Vazirmatn';
                    font-size: 11.5px;
                    font-weight: 600;
                    background-color: #161F30;
                    color: {text_color};
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 7px;
                    padding: 0 12px;
                }}
                QPushButton:hover {{
                    background-color: #1E283D;
                    border-color: {self.color_hex}88;
                    color: #FFFFFF;
                }}
            """)


class ProjectsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.card_widgets = {}
        self.quick_pills = {}
        self._current_grid_cols = 2
        
        self.init_ui()
        self._connect_signals()
        self.refresh_projects()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 20, 28, 20)
        main_layout.setSpacing(14)

        # ۱. سربرگ صفحه
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        lbl_title = QLabel("مدیریت پروژه‌های فعال")
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 22px; font-weight: 800; color: #F8FAFC;")
        lbl_desc = QLabel("پایپ‌لاین پروژه‌های در حال تدوین، کلیپ‌ها، تحویل اولیه و دوره‌های اصلاحیه")
        lbl_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; color: #94A3B8;")
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_desc)
        header_layout.addLayout(title_col, stretch=1)

        self.summary_pill = HeaderSummaryPill(
            title="پروژه‌های فعال",
            count=0,
            sub_text="در حال انجام",
            accent_color="#818CF8"
        )
        header_layout.addWidget(self.summary_pill)

        btn_new_proj = QPushButton("تعریف پروژه جدید")
        btn_new_proj.setFixedHeight(38)
        btn_new_proj.setIcon(IconProvider.get_icon("plus", "#FFFFFF", size=14))
        btn_new_proj.setIconSize(QSize(14, 14))
        btn_new_proj.setProperty("class", "PrimaryButton")
        btn_new_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_proj.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12.5px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        btn_new_proj.clicked.connect(self._open_new_project_dialog)
        header_layout.addWidget(btn_new_proj)

        main_layout.addLayout(header_layout)

        # ۲. پنل یکپارچه جستجو و فیلترهای سریع
        filter_panel = QFrame()
        filter_panel.setObjectName("ProjectsFilterPanel")
        filter_panel.setStyleSheet("""
            QFrame#ProjectsFilterPanel {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
            QLineEdit {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                padding: 0 12px;
                color: #F8FAFC;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2234;
            }
        """)

        panel_layout = QHBoxLayout(filter_panel)
        panel_layout.setContentsMargins(10, 8, 10, 8)
        panel_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setFixedHeight(34)
        self.search_input.setPlaceholderText("🔍 جستجوی هوشمند (نام زوجین، شماره پروژه مانند 05، استودیو...)")
        self.search_input.textChanged.connect(self.refresh_projects)
        panel_layout.addWidget(self.search_input, stretch=3)

        self.pill_overdue = StudioFilterPillButton("تأخیر خورده", "overdue", "filter_alert", "#EF4444")
        self.pill_overdue.clicked.connect(lambda: self._on_quick_pill_clicked("overdue"))
        panel_layout.addWidget(self.pill_overdue)
        self.quick_pills["overdue"] = self.pill_overdue

        self.pill_revision = StudioFilterPillButton("اصلاحیه فعال", "revision", "filter_bolt", "#F97316")
        self.pill_revision.clicked.connect(lambda: self._on_quick_pill_clicked("revision"))
        panel_layout.addWidget(self.pill_revision)
        self.quick_pills["revision"] = self.pill_revision

        self.pill_ready = StudioFilterPillButton("آماده تحویل", "ready", "filter_check_all", "#10B981")
        self.pill_ready.clicked.connect(lambda: self._on_quick_pill_clicked("ready"))
        panel_layout.addWidget(self.pill_ready)
        self.quick_pills["ready"] = self.pill_ready

        self.pill_unsettled = StudioFilterPillButton("تسویه‌نشده", "unsettled", "filter_finance", "#F59E0B")
        self.pill_unsettled.clicked.connect(lambda: self._on_quick_pill_clicked("unsettled"))
        panel_layout.addWidget(self.pill_unsettled)
        self.quick_pills["unsettled"] = self.pill_unsettled

        self.btn_reset = QPushButton(" بازنشانی")
        self.btn_reset.setIcon(IconProvider.get_icon("refresh", "#818CF8", size=12))
        self.btn_reset.setIconSize(QSize(12, 12))
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setFixedHeight(34)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                color: #818CF8;
                background-color: #161F30;
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 7px;
                font-size: 11.5px;
                font-weight: bold;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.15);
                color: #A5B4FC;
            }
        """)
        self.btn_reset.clicked.connect(self._reset_all_filters)
        panel_layout.addWidget(self.btn_reset)

        main_layout.addWidget(filter_panel)

        # ۳. کانتینر اسکرول و گرید داینامیک
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(0, 4, 0, 10)
        self.cards_grid.setHorizontalSpacing(14)
        self.cards_grid.setVerticalSpacing(14)
        self.cards_grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll.setWidget(self.cards_container)
        main_layout.addWidget(self.scroll, stretch=1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.scroll.width()
        target_cols = 1 if w < 840 else 2
        if hasattr(self, "_current_grid_cols") and self._current_grid_cols == target_cols:
            return
        self._current_grid_cols = target_cols
        self.refresh_projects()

    def _connect_signals(self):
        trigger = lambda *args: QTimer.singleShot(0, self.refresh_projects)
        global_signals.project_created.connect(trigger)
        global_signals.project_deleted.connect(trigger)
        global_signals.project_archived.connect(trigger)
        global_signals.project_unarchived.connect(trigger)
        global_signals.stage_changed.connect(trigger)
        global_signals.revision_added.connect(trigger)
        global_signals.revision_deleted.connect(trigger)
        global_signals.transaction_recorded.connect(trigger)
        global_signals.settings_updated.connect(trigger)
        
        # هندل نرم‌تر آپدیت پروژه برای جلوگیری از بازسازی پرشی
        global_signals.project_updated.connect(self._on_project_updated_soft)
        global_signals.navigate_and_focus_project.connect(self.focus_and_highlight_project)

    def _on_project_updated_soft(self, project_id: int):
        # بازخوانی مستقیم بدون ایجاد لرزش
        QTimer.singleShot(50, self.refresh_projects)

    def _on_quick_pill_clicked(self, clicked_key: str):
        target_pill = self.quick_pills.get(clicked_key)
        if not target_pill:
            return

        is_now_checked = target_pill.isChecked()
        for key, pill in self.quick_pills.items():
            if key != clicked_key:
                pill.setChecked(False)
                pill.update_appearance()

        target_pill.setChecked(is_now_checked)
        target_pill.update_appearance()
        self.refresh_projects()

    def _reset_all_filters(self):
        self.search_input.clear()
        for pill in self.quick_pills.values():
            pill.setChecked(False)
            pill.update_appearance()
        self.refresh_projects()

    def refresh_projects(self):
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.card_widgets.clear()
        raw_projects = ProjectController.get_active_projects()

        search_query = self.search_input.text().strip().lower()
        active_filter = None
        for key, pill in self.quick_pills.items():
            if pill.isChecked():
                active_filter = key
                break

        now_dt = datetime.utcnow()
        counts = {"overdue": 0, "revision": 0, "ready": 0, "unsettled": 0}

        for p in raw_projects:
            fin = ProjectController.get_project_financial_summary(p)
            active_rev = ProjectController.get_active_revision(p)
            s_info = ProjectController.get_status_info(p)

            if p.deadline:
                delta = (p.deadline.date() - now_dt.date()).days
                if delta < 0:
                    counts["overdue"] += 1

            if active_rev:
                counts["revision"] += 1
            elif s_info.get("key") == "ready_for_delivery":
                counts["ready"] += 1

            if fin["remaining"] > 0:
                counts["unsettled"] += 1

        self.pill_overdue.set_count(counts["overdue"])
        self.pill_revision.set_count(counts["revision"])
        self.pill_ready.set_count(counts["ready"])
        self.pill_unsettled.set_count(counts["unsettled"])

        filtered_items = []
        for p in raw_projects:
            fin = ProjectController.get_project_financial_summary(p)
            active_rev = ProjectController.get_active_revision(p)
            completed_cnt, total_cnt, pct = ProjectController.calculate_project_progress(p)
            status_info = ProjectController.get_status_info(p)

            if active_filter == "overdue":
                if not p.deadline or (p.deadline.date() - now_dt.date()).days >= 0:
                    continue
            elif active_filter == "revision":
                if not active_rev:
                    continue
            elif active_filter == "ready":
                if status_info.get("key") != "ready_for_delivery":
                    continue
            elif active_filter == "unsettled":
                if fin["remaining"] <= 0:
                    continue

            if search_query:
                c_name = (p.couple_names or "").lower()
                p_title = (p.title or "").lower()
                s_name = (p.client.company if p.client and p.client.company else (p.client.full_name if p.client else "")).lower()
                p_num_str = f"{p.project_number:02d}" if p.project_number else str(p.id)
                fee_str = str(fin["total_fee"])
                rem_str = str(fin["remaining"])

                match = (
                    (search_query in c_name) or 
                    (search_query in s_name) or 
                    (search_query in p_title) or 
                    (search_query in p_num_str) or 
                    (search_query in fee_str) or 
                    (search_query in rem_str)
                )
                if not match:
                    continue

            filtered_items.append((p, fin, active_rev, completed_cnt, total_cnt, pct, status_info))

        filtered_items.sort(key=lambda x: x[0].deadline or datetime.max)
        self.summary_pill.set_count(len(filtered_items))

        is_any_active = bool(search_query or active_filter)
        self._update_reset_button_state(is_any_active)

        # تنظیم ستون‌های گرید
        cols = getattr(self, "_current_grid_cols", 2)
        for i in range(self.cards_grid.columnCount()):
            self.cards_grid.setColumnStretch(i, 0)
        for c in range(cols):
            self.cards_grid.setColumnStretch(c, 1)

        if not filtered_items:
            empty_state = ModernEmptyStateWidget(
                title="هیچ پروژه‌ای با این مشخصات یافت نشد",
                description="می‌توانید فیلتر را غیرفعال کرده یا پروژه جدیدی تعریف کنید.",
                button_text="+ تعریف پروژه جدید"
            )
            empty_state.action_clicked.connect(self._open_new_project_dialog)
            self.cards_grid.addWidget(empty_state, 0, 0, 1, cols)
            return

        for index, (p, fin, active_rev, completed_cnt, total_cnt, pct, status_info) in enumerate(filtered_items):
            rev_c, rev_t, rev_pct = ProjectController.calculate_revision_progress(active_rev) if active_rev else (0, 0, 0)

            clips_data = [
                {
                    "id": c.id,
                    "name": c.clip_name,
                    "is_completed": c.is_completed,
                    "completed_at": c.completed_at
                }
                for c in p.clips
            ]

            p_data = {
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
                "financial_status": fin["status_label"],
                "financial_color": fin["status_color"],
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
            card = ProjectCard(p_data)
            row = index // cols
            col = index % cols
            self.cards_grid.addWidget(card, row, col, 1, 1)
            self.card_widgets[p.id] = card

    def _update_reset_button_state(self, is_active: bool):
        if is_active:
            self.btn_reset.setIcon(IconProvider.get_icon("refresh", "#F59E0B", size=12))
            self.btn_reset.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    color: #F59E0B;
                    background-color: rgba(245, 158, 11, 0.12);
                    border: 1px solid rgba(245, 158, 11, 0.35);
                    border-radius: 7px;
                    font-size: 11.5px;
                    font-weight: 700;
                    padding: 0 10px;
                }
                QPushButton:hover {
                    background-color: #F59E0B;
                    color: #000000;
                }
            """)
        else:
            self.btn_reset.setIcon(IconProvider.get_icon("refresh", "#818CF8", size=12))
            self.btn_reset.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    color: #818CF8;
                    background-color: #161F30;
                    border: 1px solid rgba(99, 102, 241, 0.25);
                    border-radius: 7px;
                    font-size: 11.5px;
                    font-weight: bold;
                    padding: 0 10px;
                }
                QPushButton:hover {
                    background-color: rgba(99, 102, 241, 0.15);
                    color: #A5B4FC;
                }
            """)

    def focus_and_highlight_project(self, project_id: int):
        if self.search_input.text():
            self.search_input.clear()

        def _do_highlight():
            card = self.card_widgets.get(project_id)
            if card:
                self.scroll.ensureWidgetVisible(card, 50, 50)
                card.setStyleSheet("""
                    QFrame#BaseCardFrame {
                        background-color: #1A243D;
                        border: 2px solid #6366F1;
                        border-radius: 12px;
                    }
                """)
                QTimer.singleShot(2200, lambda: card._apply_base_styles() if card else None)

        QTimer.singleShot(100, _do_highlight)

    def _open_new_project_dialog(self):
        diag = NewProjectDialog(self.window())
        diag.exec()