# ==================================================
# FILE: views/archive_view.py
# ==================================================
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QScrollArea, QFrame, QGridLayout,
    QPushButton, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QSize
from sqlalchemy import select

from database.db_manager import db
from database.models import Client
from widgets.archive_project_card import ArchiveProjectCard
from widgets.header_summary_pill import HeaderSummaryPill
from widgets.empty_state import ModernEmptyStateWidget
from core.project_controller import ProjectController
from core.persian_utils import to_persian_numbers
from core.icon_provider import IconProvider
from core.signals import global_signals


class ArchiveFilterPillButton(QPushButton):
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
                    padding: 0 10px;
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
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background-color: #1E283D;
                    border-color: {self.color_hex}88;
                    color: #FFFFFF;
                }}
            """)


class ArchiveView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.quick_pills = {}
        self._current_grid_cols = 4
        
        self.init_ui()
        self._connect_signals()
        self._load_studios_filter()
        self.refresh_archive()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 20, 28, 20)
        main_layout.setSpacing(14)

        # ۱. سربرگ صفحه
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        lbl_title = QLabel("آرشیو پروژه‌های تکمیل‌شده")
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 22px; font-weight: 800; color: #F8FAFC;")
        lbl_desc = QLabel("سوابق تحویل اولیه، شناسنامه رسمی، تسویه‌حساب‌ها و تاریخچه چرخه‌های اصلاحیه")
        lbl_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; color: #94A3B8;")
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_desc)
        header_layout.addLayout(title_col, stretch=1)

        self.summary_pill = HeaderSummaryPill(
            title="پرونده‌های آرشیو",
            count=0,
            sub_text="مختومه و تحویل‌شده",
            accent_color="#10B981"
        )
        header_layout.addWidget(self.summary_pill)
        main_layout.addLayout(header_layout)

        # ۲. پنل یکپارچه فیلترها
        filter_panel = QFrame()
        filter_panel.setObjectName("ArchiveFilterPanel")
        filter_panel.setStyleSheet("""
            QFrame#ArchiveFilterPanel {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
            QLabel {
                font-family: 'Vazirmatn';
                color: #94A3B8;
                font-size: 11.5px;
                font-weight: 600;
                background: transparent;
                border: none;
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
            QComboBox {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                padding: 4px 8px;
                color: #F8FAFC;
                font-size: 11.5px;
                min-height: 32px;
            }
            QComboBox:focus {
                border-color: #6366F1;
            }
            QComboBox QAbstractItemView {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: #F8FAFC;
                selection-background-color: #6366F1;
                padding: 4px;
            }
        """)

        panel_layout = QVBoxLayout(filter_panel)
        panel_layout.setContentsMargins(12, 8, 12, 8)
        panel_layout.setSpacing(8)

        # ردیف بالا: سرچ و چیپ‌های سریع
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setFixedHeight(34)
        self.search_input.setPlaceholderText("🔍 جستجو در آرشیو (نام زوجین، استودیو، شماره پرونده...)")
        self.search_input.textChanged.connect(self.refresh_archive)
        top_row.addWidget(self.search_input, stretch=3)

        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(6)

        self.pill_unsettled = ArchiveFilterPillButton("تسویه‌نشده", "unsettled", "filter_finance", "#F59E0B")
        self.pill_unsettled.clicked.connect(lambda: self._on_quick_pill_clicked("unsettled"))
        pills_layout.addWidget(self.pill_unsettled)
        self.quick_pills["unsettled"] = self.pill_unsettled

        self.pill_settled = ArchiveFilterPillButton("تسویه کامل", "settled", "filter_check_all", "#10B981")
        self.pill_settled.clicked.connect(lambda: self._on_quick_pill_clicked("settled"))
        pills_layout.addWidget(self.pill_settled)
        self.quick_pills["settled"] = self.pill_settled

        self.pill_has_rev = ArchiveFilterPillButton("دارای اصلاحیه", "has_rev", "filter_bolt", "#F97316")
        self.pill_has_rev.clicked.connect(lambda: self._on_quick_pill_clicked("has_rev"))
        pills_layout.addWidget(self.pill_has_rev)
        self.quick_pills["has_rev"] = self.pill_has_rev

        self.pill_no_rev = ArchiveFilterPillButton("تحویل یکباره", "no_rev", "check", "#38BDF8")
        self.pill_no_rev.clicked.connect(lambda: self._on_quick_pill_clicked("no_rev"))
        pills_layout.addWidget(self.pill_no_rev)
        self.quick_pills["no_rev"] = self.pill_no_rev

        top_row.addLayout(pills_layout, stretch=4)
        panel_layout.addLayout(top_row)

        # ردیف پایین: فیلترها و مرتب‌سازی
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)

        controls_row.addWidget(QLabel("استودیو:"))
        self.combo_studio = QComboBox()
        self.combo_studio.addItem("همه استودیوها", 0)
        self.combo_studio.currentIndexChanged.connect(self.refresh_archive)
        controls_row.addWidget(self.combo_studio, stretch=3)

        controls_row.addWidget(QLabel("مرتب‌سازی:"))
        self.combo_sort = QComboBox()
        self.combo_sort.addItem("جدیدترین تاریخ تحویل", "delivery_desc")
        self.combo_sort.addItem("قدیمی‌ترین تاریخ تحویل", "delivery_asc")
        self.combo_sort.addItem("تاریخ مراسم (جدید به قدیم)", "event_desc")
        self.combo_sort.addItem("شماره پرونده (صعودی)", "pnum_asc")
        self.combo_sort.addItem("شماره پرونده (نزولی)", "pnum_desc")
        self.combo_sort.addItem("بیشترین مانده بدهی", "debt_desc")
        self.combo_sort.addItem("بالاترین مبلغ کل", "fee_desc")
        self.combo_sort.currentIndexChanged.connect(self.refresh_archive)
        controls_row.addWidget(self.combo_sort, stretch=3)

        self.btn_reset = QPushButton(" بازنشانی")
        self.btn_reset.setIcon(IconProvider.get_icon("refresh", "#10B981", size=12))
        self.btn_reset.setIconSize(QSize(12, 12))
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setFixedHeight(32)
        self.btn_reset.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                color: #10B981;
                background-color: #161F30;
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 7px;
                font-size: 11.5px;
                font-weight: bold;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.15);
                color: #34D399;
            }
        """)
        self.btn_reset.clicked.connect(self._reset_all_filters)
        controls_row.addWidget(self.btn_reset)

        panel_layout.addLayout(controls_row)
        main_layout.addWidget(filter_panel)

        # ۳. کانتینر اسکرول و گرید
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setContentsMargins(0, 4, 0, 10)
        self.cards_grid.setHorizontalSpacing(10)
        self.cards_grid.setVerticalSpacing(10)
        self.cards_grid.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.cards_container)
        main_layout.addWidget(scroll, stretch=1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        if w < 860:
            target_cols = 2
        elif w < 1180:
            target_cols = 3
        else:
            target_cols = 4

        if hasattr(self, "_current_grid_cols") and self._current_grid_cols == target_cols:
            return
        self._current_grid_cols = target_cols
        self.refresh_archive()

    def _connect_signals(self):
        trigger = lambda *args: QTimer.singleShot(0, self.refresh_archive)
        global_signals.project_archived.connect(trigger)
        global_signals.project_unarchived.connect(trigger)
        global_signals.project_updated.connect(trigger)
        global_signals.project_deleted.connect(trigger)
        global_signals.transaction_recorded.connect(trigger)
        global_signals.client_balance_updated.connect(lambda *_: self._load_studios_filter())

    def _load_studios_filter(self):
        current_id = self.combo_studio.currentData()
        self.combo_studio.blockSignals(True)
        self.combo_studio.clear()
        self.combo_studio.addItem("همه استودیوها", 0)

        with db.get_session() as session:
            clients = session.scalars(select(Client).order_by(Client.company, Client.full_name)).all()
            for c in clients:
                display = c.company or c.full_name
                self.combo_studio.addItem(display, c.id)

        idx = self.combo_studio.findData(current_id)
        if idx >= 0:
            self.combo_studio.setCurrentIndex(idx)
        self.combo_studio.blockSignals(False)

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
        self.refresh_archive()

    def _reset_all_filters(self):
        self.search_input.clear()
        self.combo_studio.setCurrentIndex(0)
        self.combo_sort.setCurrentIndex(0)
        for pill in self.quick_pills.values():
            pill.setChecked(False)
            pill.update_appearance()
        self.refresh_archive()

    def refresh_archive(self):
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        raw_projects = ProjectController.get_archived_projects()

        search_query = self.search_input.text().strip().lower()
        selected_client_id = self.combo_studio.currentData() or 0
        sort_mode = self.combo_sort.currentData() or "delivery_desc"

        active_filter = None
        for key, pill in self.quick_pills.items():
            if pill.isChecked():
                active_filter = key
                break

        counts = {"unsettled": 0, "settled": 0, "has_rev": 0, "no_rev": 0}

        for p in raw_projects:
            fin = ProjectController.get_project_financial_summary(p)
            rev_cnt = len(p.revisions) if p.revisions else 0

            if fin["remaining"] > 0:
                counts["unsettled"] += 1
            else:
                counts["settled"] += 1

            if rev_cnt > 0:
                counts["has_rev"] += 1
            else:
                counts["no_rev"] += 1

        self.pill_unsettled.set_count(counts["unsettled"])
        self.pill_settled.set_count(counts["settled"])
        self.pill_has_rev.set_count(counts["has_rev"])
        self.pill_no_rev.set_count(counts["no_rev"])

        filtered_items = []
        for p in raw_projects:
            fin = ProjectController.get_project_financial_summary(p)
            rev_cnt = len(p.revisions) if p.revisions else 0

            if selected_client_id > 0 and p.client_id != selected_client_id:
                continue

            if active_filter == "unsettled" and fin["remaining"] <= 0:
                continue
            elif active_filter == "settled" and not fin["is_settled"]:
                continue
            elif active_filter == "has_rev" and rev_cnt == 0:
                continue
            elif active_filter == "no_rev" and rev_cnt > 0:
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

            filtered_items.append((p, fin))

        if sort_mode == "delivery_desc":
            filtered_items.sort(key=lambda x: x[0].delivered_at or x[0].completed_at or x[0].created_at or datetime.min, reverse=True)
        elif sort_mode == "delivery_asc":
            filtered_items.sort(key=lambda x: x[0].delivered_at or x[0].completed_at or x[0].created_at or datetime.min, reverse=False)
        elif sort_mode == "event_desc":
            filtered_items.sort(key=lambda x: x[0].event_date or datetime.min, reverse=True)
        elif sort_mode == "pnum_asc":
            filtered_items.sort(key=lambda x: x[0].project_number or x[0].id)
        elif sort_mode == "pnum_desc":
            filtered_items.sort(key=lambda x: x[0].project_number or x[0].id, reverse=True)
        elif sort_mode == "debt_desc":
            filtered_items.sort(key=lambda x: x[1]["remaining"], reverse=True)
        elif sort_mode == "fee_desc":
            filtered_items.sort(key=lambda x: x[1]["total_fee"], reverse=True)

        self.summary_pill.set_count(len(filtered_items))

        is_any_active = bool(search_query or selected_client_id > 0 or active_filter)
        self._update_reset_button_state(is_any_active)

        cols = getattr(self, "_current_grid_cols", 4)
        for i in range(self.cards_grid.columnCount()):
            self.cards_grid.setColumnStretch(i, 0)
        for c in range(cols):
            self.cards_grid.setColumnStretch(c, 1)

        if not filtered_items:
            empty_state = ModernEmptyStateWidget(
                title="هیچ پرونده‌ای با این مشخصات یافت نشد",
                description="می‌توانید عبارت جستجو را تغییر دهید یا فیلترها را بازنشانی کنید.",
                button_text=""
            )
            self.cards_grid.addWidget(empty_state, 0, 0, 1, cols)
            return

        for index, (p, fin) in enumerate(filtered_items):
            p_data = {
                "id": p.id,
                "project_number": p.project_number or p.id,
                "couple_names": p.couple_names,
                "title": p.title,
                "client_name": p.client.company if (p.client and p.client.company) else (p.client.full_name if p.client else "بدون استودیو"),
                "total_fee": fin["total_fee"],
                "remaining_amount": fin["remaining"],
                "is_settled": fin["is_settled"],
                "event_date": p.event_date,
                "completed_at": p.delivered_at or p.completed_at,
                "revisions_count": len(p.revisions) if p.revisions else 0,
                "primary_path": p.drive_locations[0].absolute_path if p.drive_locations else None
            }
            card = ArchiveProjectCard(p_data)
            row = index // cols
            col = index % cols
            self.cards_grid.addWidget(card, row, col, 1, 1)

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
            self.btn_reset.setIcon(IconProvider.get_icon("refresh", "#10B981", size=12))
            self.btn_reset.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    color: #10B981;
                    background-color: #161F30;
                    border: 1px solid rgba(16, 185, 129, 0.25);
                    border-radius: 7px;
                    font-size: 11.5px;
                    font-weight: bold;
                    padding: 0 10px;
                }
                QPushButton:hover {
                    background-color: rgba(16, 185, 129, 0.15);
                    color: #34D399;
                }
            """)