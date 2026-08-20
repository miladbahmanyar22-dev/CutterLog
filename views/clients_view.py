# views/clients_view.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QLineEdit
)
from PySide6.QtCore import Qt, QSize
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database.db_manager import db
from database.models import Client
from core.persian_utils import format_toman, to_persian_numbers, gregorian_to_jalali
from widgets.new_client_dialog import NewClientDialog
from core.icon_provider import IconProvider
from core.signals import global_signals


class ClientsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()
        self._connect_signals()
        self.refresh_clients()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # Header Section
        header_layout = QHBoxLayout()
        info_col = QVBoxLayout()

        title = QLabel("دایرکتوری کارفرماها و همکاران")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #F4F4F6;")
        subtitle = QLabel("مدیریت اطلاعات تماس، تاریخچه پروژه‌ها و سوابق مالی هر مشتری")
        subtitle.setStyleSheet("font-size: 12px; color: #8F909D;")
        info_col.addWidget(title)
        info_col.addWidget(subtitle)
        header_layout.addLayout(info_col, stretch=1)

        # New Client Button with SVG Vector Icon
        btn_new = QPushButton("کارفرمای جدید")
        btn_new.setIcon(IconProvider.get_icon("plus", "#FFFFFF", size=15))
        btn_new.setIconSize(QSize(15, 15))
        btn_new.setProperty("class", "PrimaryButton")
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.clicked.connect(self._open_new_client_dialog)
        header_layout.addWidget(btn_new)

        main_layout.addLayout(header_layout)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("جستجوی کارفرما بر اساس نام، برند، استودیو یا شماره تماس...")
        self.search_input.textChanged.connect(self.refresh_clients)
        main_layout.addWidget(self.search_input)

        # Clients Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "نام کارفرما", "برند / شرکت", "شماره تماس", "تعداد پروژه‌ها", "ارزش کل سفارش‌ها", "تاریخ عضویت"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1A1E;
                border: 1px solid #2E2E36;
                border-radius: 8px;
                gridline-color: #24242A;
                color: #F4F4F6;
            }
            QHeaderView::section {
                background-color: #16161A;
                color: #8F909D;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #2E2E36;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #24242A;
                color: #6366F1;
            }
        """)
        main_layout.addWidget(self.table, stretch=1)

    def _connect_signals(self):
        global_signals.client_balance_updated.connect(lambda _: self.refresh_clients())
        global_signals.project_created.connect(lambda _: self.refresh_clients())
        global_signals.project_updated.connect(lambda _: self.refresh_clients())
        global_signals.project_deleted.connect(lambda _: self.refresh_clients())

    def _open_new_client_dialog(self):
        dialog = NewClientDialog(self)
        dialog.exec()

    def refresh_clients(self):
        self.table.setRowCount(0)
        search_query = self.search_input.text().strip().lower()

        with db.get_session() as session:
            stmt = select(Client).options(joinedload(Client.projects)).order_by(Client.created_at.desc())
            clients = session.scalars(stmt).unique().all()

            row_idx = 0
            for c in clients:
                full_name = c.full_name or ""
                company = c.company or "-"
                phone_raw = c.phone or "-"
                phone_display = to_persian_numbers(phone_raw)
                
                # فیلتر جستجو
                if search_query and (
                    search_query not in full_name.lower() 
                    and search_query not in company.lower() 
                    and search_query not in phone_raw.lower()
                ):
                    continue

                self.table.insertRow(row_idx)

                projects_count = len(c.projects)
                total_spent = sum(p.total_fee for p in c.projects)
                created_date = gregorian_to_jalali(c.created_at)

                items = [
                    full_name,
                    company,
                    phone_display,
                    to_persian_numbers(projects_count),
                    format_toman(total_spent),
                    created_date
                ]

                for col_idx, val in enumerate(items):
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row_idx, col_idx, item)

                row_idx += 1