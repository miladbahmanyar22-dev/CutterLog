# ==================================================
# FILE: views/financials_view.py
# ==================================================
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QFrame,
    QComboBox, QTabWidget, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer
from sqlalchemy import select

from database.db_manager import db
from database.models import Client
from core.persian_utils import format_toman, to_persian_numbers, gregorian_to_jalali
from core.finance_controller import FinanceController
from core.excel_exporter import export_transactions_to_excel
from widgets.new_transaction_dialog import NewTransactionDialog
from widgets.studio_invoice_dialog import StudioInvoiceDialog
from widgets.stat_card import StatCard
from widgets.revenue_bar_chart import RevenueBarChartWidget
from widgets.empty_state import ModernEmptyStateWidget
from widgets.studio_dialog_base import StudioConfirmDialog
from core.icon_provider import IconProvider
from core.signals import global_signals


class StudioLedgerCard(QFrame):
    """کارت حساب و بدهی کل استودیو"""
    def __init__(self, studio_data: Dict[str, Any], on_settle_callback, parent=None):
        super().__init__(parent)
        self.studio_data = studio_data
        self.on_settle_callback = on_settle_callback
        
        self.setObjectName("FinancialCardItem")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(84)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # نام استودیو
        studio_info = QVBoxLayout()
        studio_info.setSpacing(2)
        studio_info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_name = QLabel(self.studio_data.get("studio_name", "استودیو"))
        lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14.5px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        studio_info.addWidget(lbl_name)

        proj_count = self.studio_data.get("projects_count", 0)
        lbl_count = QLabel(f"🏢 {to_persian_numbers(proj_count)} پروژه تحویل‌شده")
        lbl_count.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; border: none; background: transparent;")
        studio_info.addWidget(lbl_count)
        layout.addLayout(studio_info, stretch=2)

        layout.addWidget(self._create_v_divider())

        # قراردادها و دریافتی
        fin_col1 = QVBoxLayout()
        fin_col1.setSpacing(2)
        fin_col1.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        lbl_fee = QLabel(f"مجموع قراردادها: <b style='color:#F8FAFC;'>{format_toman(self.studio_data.get('total_fee', 0))}</b>")
        lbl_fee.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #8F909D; border: none; background: transparent;")
        fin_col1.addWidget(lbl_fee)

        lbl_paid = QLabel(f"کل دریافتی: <b style='color:#10B981;'>{format_toman(self.studio_data.get('total_paid', 0))}</b>")
        lbl_paid.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #8F909D; border: none; background: transparent;")
        fin_col1.addWidget(lbl_paid)
        layout.addLayout(fin_col1, stretch=2)

        layout.addWidget(self._create_v_divider())

        # مانده و درصد وصول
        remaining = self.studio_data.get("remaining", 0)
        total_fee = self.studio_data.get("total_fee", 0)
        total_paid = self.studio_data.get("total_paid", 0)
        pct = int((total_paid / total_fee) * 100) if total_fee > 0 else 100

        fin_col2 = QVBoxLayout()
        fin_col2.setSpacing(2)
        fin_col2.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        rem_color = "#F59E0B" if remaining > 0 else "#10B981"
        rem_text = f"مانده طلب: <b>{format_toman(remaining)}</b>" if remaining > 0 else "حساب کاملاً تسویه شده ✓"

        lbl_rem = QLabel(rem_text)
        lbl_rem.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 700; color: {rem_color}; border: none; background: transparent;")
        fin_col2.addWidget(lbl_rem)

        lbl_pct = QLabel(f"نرخ وصول مطالبات: {to_persian_numbers(pct)}٪")
        lbl_pct.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; border: none; background: transparent;")
        fin_col2.addWidget(lbl_pct)
        layout.addLayout(fin_col2, stretch=2)

        # دکمه‌های اقدام
        btn_box = QHBoxLayout()
        btn_box.setSpacing(6)

        client_id = self.studio_data.get("client_id", 0)

        btn_invoice = QPushButton("فاکتور 📄")
        btn_invoice.setFixedHeight(36)
        btn_invoice.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_invoice.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #1E283D;
                color: #F8FAFC;
                font-weight: 600;
                font-size: 11.5px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                padding: 0 12px;
            }
            QPushButton:hover {
                border-color: #6366F1;
                background-color: #242E42;
            }
        """)
        btn_invoice.clicked.connect(lambda: self._open_invoice(client_id))
        btn_box.addWidget(btn_invoice)

        btn_settle = QPushButton("تسویه حساب 💳")
        btn_settle.setFixedHeight(36)
        btn_settle.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if remaining > 0:
            btn_settle.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: #6366F1;
                    color: #FFFFFF;
                    font-weight: 700;
                    font-size: 12px;
                    border: none;
                    border-radius: 7px;
                    padding: 0 14px;
                }
                QPushButton:hover { background-color: #4F46E5; }
            """)
            btn_settle.setEnabled(True)
        else:
            btn_settle.setText("تسویه شده ✓")
            btn_settle.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: rgba(16, 185, 129, 0.12);
                    color: #10B981;
                    font-weight: 700;
                    font-size: 11.5px;
                    border: 1px solid rgba(16, 185, 129, 0.25);
                    border-radius: 7px;
                    padding: 0 12px;
                }
            """)
            btn_settle.setEnabled(False)

        btn_settle.clicked.connect(lambda: self.on_settle_callback(client_id))
        btn_box.addWidget(btn_settle)

        layout.addLayout(btn_box)
        self._apply_style()

    def _open_invoice(self, client_id: int):
        diag = StudioInvoiceDialog(client_id, parent=self.window())
        diag.exec()

    def _create_v_divider(self) -> QFrame:
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFixedHeight(34)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        return div

    def _apply_style(self):
        self.setStyleSheet("""
            QFrame#FinancialCardItem {
                background-color: #141B2A;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
            QFrame#FinancialCardItem:hover {
                background-color: #182236;
                border: 1px solid rgba(99, 102, 241, 0.35);
            }
        """)


class ReceivableProjectCard(QFrame):
    """کارت مدرن پروژه‌های دارای مانده بدهی با دسترسی به ثبت واریزی و فاکتور مستقل"""
    def __init__(self, item_data: Dict[str, Any], on_pay_callback, on_invoice_callback, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self.on_pay_callback = on_pay_callback
        self.on_invoice_callback = on_invoice_callback
        
        self.setObjectName("FinancialCardItem")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(84)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        p_info = QVBoxLayout()
        p_info.setSpacing(2)
        p_info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        p_num = f"{self.item_data.get('project_number', 1):03d}"
        lbl_title = QLabel(f"<span style='color:#818CF8; font-weight:bold;'>{to_persian_numbers(p_num)}</span> — {self.item_data.get('couple_names', 'پروژه')}")
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        p_info.addWidget(lbl_title)

        status_text = "آرشیو شده" if self.item_data.get("is_archived") else "تحویل شده به آتلیه"
        lbl_sub = QLabel(f"استودیو: {self.item_data.get('client_name', '-')}    |    وضعیت: {status_text}")
        lbl_sub.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; border: none; background: transparent;")
        p_info.addWidget(lbl_sub)
        layout.addLayout(p_info, stretch=2)

        layout.addWidget(self._create_v_divider())

        fin_col1 = QVBoxLayout()
        fin_col1.setSpacing(2)
        fin_col1.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        lbl_fee = QLabel(f"مبلغ کل: <b style='color:#F8FAFC;'>{format_toman(self.item_data.get('total_fee', 0))}</b>")
        lbl_fee.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #8F909D; border: none; background: transparent;")
        fin_col1.addWidget(lbl_fee)

        lbl_paid = QLabel(f"دریافت‌شده: <b style='color:#10B981;'>{format_toman(self.item_data.get('total_paid', 0))}</b>")
        lbl_paid.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #8F909D; border: none; background: transparent;")
        fin_col1.addWidget(lbl_paid)
        layout.addLayout(fin_col1, stretch=2)

        layout.addWidget(self._create_v_divider())

        rem_col = QVBoxLayout()
        rem_col.setSpacing(2)
        rem_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_rem = QLabel(f"مانده بدهی: <b>{format_toman(self.item_data.get('remaining', 0))}</b>")
        lbl_rem.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #F59E0B; border: none; background: transparent;")
        rem_col.addWidget(lbl_rem)

        lbl_hint = QLabel("در انتظار واریزی و تسویه")
        lbl_hint.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; border: none; background: transparent;")
        rem_col.addWidget(lbl_hint)
        layout.addLayout(rem_col, stretch=2)

        # دکمه‌های فاکتور تک‌پروژه و ثبت واریزی
        btn_box = QHBoxLayout()
        btn_box.setSpacing(6)

        proj_id = self.item_data.get("project_id", 0)

        btn_invoice = QPushButton("فاکتور 📄")
        btn_invoice.setFixedHeight(36)
        btn_invoice.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_invoice.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #1E283D;
                color: #F8FAFC;
                font-weight: 600;
                font-size: 11.5px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                padding: 0 12px;
            }
            QPushButton:hover {
                border-color: #6366F1;
                background-color: #242E42;
            }
        """)
        btn_invoice.clicked.connect(lambda: self.on_invoice_callback(proj_id))
        btn_box.addWidget(btn_invoice)

        btn_pay = QPushButton("ثبت واریزی 💵")
        btn_pay.setFixedHeight(36)
        btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pay.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: 700;
                border: none;
                border-radius: 7px;
                padding: 0 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_pay.clicked.connect(lambda: self.on_pay_callback(proj_id))
        btn_box.addWidget(btn_pay)

        layout.addLayout(btn_box)
        self._apply_style()

    def _create_v_divider(self) -> QFrame:
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFixedHeight(34)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        return div

    def _apply_style(self):
        self.setStyleSheet("""
            QFrame#FinancialCardItem {
                background-color: #141B2A;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
            QFrame#FinancialCardItem:hover {
                background-color: #182236;
                border: 1px solid rgba(245, 158, 11, 0.40);
            }
        """)


class TransactionLedgerCard(QFrame):
    """کارت ثبت تراکنش مالی در دفتر کل همراه با کد رهگیری و دکمه حذف"""
    def __init__(self, tx_data: Dict[str, Any], on_delete_cb, parent=None):
        super().__init__(parent)
        self.tx_data = tx_data
        self.on_delete_cb = on_delete_cb
        
        self.setObjectName("FinancialCardItem")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(76)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        col_tx = QVBoxLayout()
        col_tx.setSpacing(2)
        col_tx.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_code = QLabel(f"TX-{self.tx_data.get('id', 0):04d}")
        lbl_code.setStyleSheet("font-family: 'Segoe UI', 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #818CF8; border: none; background: transparent;")
        col_tx.addWidget(lbl_code)

        date_str = gregorian_to_jalali(self.tx_data.get("paid_at"))
        lbl_date = QLabel(f"📅 {date_str}")
        lbl_date.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; border: none; background: transparent;")
        col_tx.addWidget(lbl_date)
        layout.addLayout(col_tx, stretch=1)

        layout.addWidget(self._create_v_divider())

        col_target = QVBoxLayout()
        col_target.setSpacing(2)
        col_target.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_proj = QLabel(f"<b>{self.tx_data.get('project_title', 'پروژه')}</b> {self.tx_data.get('target_name', '')}")
        lbl_proj.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; color: #F8FAFC; border: none; background: transparent;")
        col_target.addWidget(lbl_proj)

        lbl_client = QLabel(f"استودیو: {self.tx_data.get('client_name', '-')}")
        lbl_client.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; border: none; background: transparent;")
        col_target.addWidget(lbl_client)
        layout.addLayout(col_target, stretch=2)

        layout.addWidget(self._create_v_divider())

        col_desc = QVBoxLayout()
        col_desc.setSpacing(2)
        col_desc.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        pt = self.tx_data.get("payment_type", "")
        pt_label = "واریزی مرحله‌ای"
        if pt == "prepayment": pt_label = "پیش‌پرداخت اولیه"
        elif pt == "final_settlement": pt_label = "تسویه نهایی حساب"

        tracking_val = self.tx_data.get("tracking_code")
        tracking_info = f" • پیگیری: {to_persian_numbers(tracking_val)}" if tracking_val else ""

        lbl_pt = QLabel(f"نوع: <span style='color:#A5B4FC; font-weight:600;'>{pt_label}</span>{tracking_info}")
        lbl_pt.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; border: none; background: transparent;")
        col_desc.addWidget(lbl_pt)

        lbl_note = QLabel(f"شرح: {self.tx_data.get('notes', '-')}")
        lbl_note.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; border: none; background: transparent;")
        col_desc.addWidget(lbl_note)
        layout.addLayout(col_desc, stretch=2)

        layout.addWidget(self._create_v_divider())

        amount = self.tx_data.get("amount", 0)
        lbl_amt = QLabel(f"+ {format_toman(amount)}")
        lbl_amt.setStyleSheet("font-family: 'Vazirmatn'; font-size: 15px; font-weight: 800; color: #10B981; border: none; background: transparent;")
        layout.addWidget(lbl_amt)

        btn_del = QPushButton()
        btn_del.setIcon(IconProvider.get_icon("trash", "#EF4444", size=13))
        btn_del.setFixedSize(28, 28)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setToolTip("حذف این تراکنش مالی")
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.12);
                border: 1px solid rgba(239, 68, 68, 0.25);
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #EF4444;
            }
        """)
        btn_del.clicked.connect(lambda: self.on_delete_cb(self.tx_data["id"], amount))
        layout.addWidget(btn_del)

        self._apply_style()

    def _create_v_divider(self) -> QFrame:
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFixedHeight(30)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        return div

    def _apply_style(self):
        self.setStyleSheet("""
            QFrame#FinancialCardItem {
                background-color: #141B2A;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
            QFrame#FinancialCardItem:hover {
                background-color: #182236;
                border: 1px solid rgba(16, 185, 129, 0.35);
            }
        """)


class MonthlyPerformanceCard(QFrame):
    """کارت ماهانه عملکرد مالی سال جاری"""
    def __init__(self, month_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.month_data = month_data
        
        self.setObjectName("FinancialCardItem")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_month = QLabel(f"📅 <b>{self.month_data.get('month', '')}</b>")
        lbl_month.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14px; color: #F8FAFC; border: none; background: transparent;")
        layout.addWidget(lbl_month, stretch=1)

        layout.addWidget(self._create_v_divider())

        cnt = self.month_data.get("count", 0)
        cnt_text = f"{to_persian_numbers(cnt)} واریزی ثبت‌شده" if cnt > 0 else "بدون تراکنش"
        lbl_cnt = QLabel(cnt_text)
        lbl_cnt.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8; border: none; background: transparent;")
        layout.addWidget(lbl_cnt, stretch=1)

        layout.addWidget(self._create_v_divider())

        amount = self.month_data.get("amount", 0)
        amt_color = "#10B981" if amount > 0 else "#64748B"
        lbl_amt = QLabel(format_toman(amount))
        lbl_amt.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 14.5px; font-weight: 800; color: {amt_color}; border: none; background: transparent;")
        layout.addWidget(lbl_amt)

        self._apply_style()

    def _create_v_divider(self) -> QFrame:
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFixedHeight(28)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        return div

    def _apply_style(self):
        self.setStyleSheet("""
            QFrame#FinancialCardItem {
                background-color: #141B2A;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
            QFrame#FinancialCardItem:hover {
                background-color: #182236;
                border: 1px solid rgba(99, 102, 241, 0.35);
            }
        """)


class FinancialsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()
        self._connect_signals()
        self.refresh_all_financial_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(16)

        # ۱. سربرگ
        header_layout = QHBoxLayout()
        info_col = QVBoxLayout()
        info_col.setSpacing(3)

        title = QLabel("مرکز مدیریت مالی و تسویه حساب‌ها")
        title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 22px; font-weight: 800; color: #F8FAFC;")
        subtitle = QLabel("مدیریت کل بدهی استودیوها، تسویه خودکار فاکتورها، وصول مطالبات و دفتر کل")
        subtitle.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; color: #94A3B8;")
        info_col.addWidget(title)
        info_col.addWidget(subtitle)
        header_layout.addLayout(info_col, stretch=1)

        btn_new_pay = QPushButton("ثبت دریافت وجه / تسویه")
        btn_new_pay.setIcon(IconProvider.get_icon("dollar", "#FFFFFF", size=15))
        btn_new_pay.setIconSize(QSize(15, 15))
        btn_new_pay.setProperty("class", "PrimaryButton")
        btn_new_pay.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_pay.setFixedHeight(38)
        btn_new_pay.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 12.5px;
                font-weight: 700;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        btn_new_pay.clicked.connect(lambda: self._open_new_transaction_dialog())
        header_layout.addWidget(btn_new_pay)

        btn_export = QPushButton("خروجی اکسل")
        btn_export.setIcon(IconProvider.get_icon("excel", "#10B981", size=15))
        btn_export.setIconSize(QSize(15, 15))
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setFixedHeight(38)
        btn_export.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 8px;
                padding: 0 14px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { background-color: rgba(16, 185, 129, 0.15); }
        """)
        btn_export.clicked.connect(self._export_excel)
        header_layout.addWidget(btn_export)

        main_layout.addLayout(header_layout)

        # ۲. نوار فیلترها
        filter_frame = QFrame()
        filter_frame.setObjectName("SurfaceCard")
        filter_frame.setStyleSheet("""
            QFrame#SurfaceCard {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
            QLabel {
                font-family: 'Vazirmatn';
                color: #94A3B8;
                font-size: 12px;
                font-weight: 600;
            }
            QComboBox {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                padding: 6px 12px;
                color: #F8FAFC;
                font-size: 12px;
                min-height: 34px;
            }
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(16, 10, 16, 10)
        filter_layout.setSpacing(14)

        filter_layout.addWidget(QLabel("استودیو:"))
        self.combo_filter_client = QComboBox()
        self.combo_filter_client.addItem("همه استودیوها", 0)
        self.combo_filter_client.currentIndexChanged.connect(self.refresh_all_financial_data)
        filter_layout.addWidget(self.combo_filter_client, stretch=2)

        filter_layout.addWidget(QLabel("بازه زمانی:"))
        self.combo_filter_date = QComboBox()
        self.combo_filter_date.addItem("همه زمان‌ها", "all")
        self.combo_filter_date.addItem("امروز", "today")
        self.combo_filter_date.addItem("این هفته", "this_week")
        self.combo_filter_date.addItem("این ماه (شمسی)", "this_month")
        self.combo_filter_date.addItem("ماه قبل", "last_month")
        self.combo_filter_date.addItem("امسال (سال جاری)", "this_year")
        self.combo_filter_date.currentIndexChanged.connect(self.refresh_all_financial_data)
        filter_layout.addWidget(self.combo_filter_date, stretch=2)

        filter_layout.addWidget(QLabel("وضعیت مالی:"))
        self.combo_filter_status = QComboBox()
        self.combo_filter_status.addItem("همه وضعیت‌ها", "all")
        self.combo_filter_status.addItem("دارای مانده طلب (تسویه‌نشده)", "unsettled")
        self.combo_filter_status.addItem("تسویه کامل شده", "settled")
        self.combo_filter_status.currentIndexChanged.connect(self.refresh_all_financial_data)
        filter_layout.addWidget(self.combo_filter_status, stretch=2)

        btn_reset_filters = QPushButton("بازنشانی")
        btn_reset_filters.setStyleSheet("font-family: 'Vazirmatn'; color: #818CF8; background: transparent; border: none; font-size: 11.5px; font-weight: 600;")
        btn_reset_filters.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_filters.clicked.connect(self._reset_filters)
        filter_layout.addWidget(btn_reset_filters)

        main_layout.addWidget(filter_frame)

        # ۳. کارت‌های شاخص مالی
        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(12)

        self.card_total_contracts = StatCard(title="کل ارزش قراردادها", initial_value=0, is_currency=True, color_accent="#6366F1")
        self.card_total_received = StatCard(title="مجموع دریافتی وصول‌شده", initial_value=0, is_currency=True, color_accent="#10B981")
        self.card_total_remaining = StatCard(title="کل طلب وصول‌نشده", initial_value=0, is_currency=True, color_accent="#F59E0B")
        self.card_unsettled_count = StatCard(title="پروژه‌های دارای مانده", initial_value=0, is_currency=False, color_accent="#EF4444")
        self.card_projects_count = StatCard(title="پروژه‌های تحویل‌شده", initial_value=0, is_currency=False, color_accent="#38BDF8")

        self.stats_layout.addWidget(self.card_total_contracts)
        self.stats_layout.addWidget(self.card_total_received)
        self.stats_layout.addWidget(self.card_total_remaining)
        self.stats_layout.addWidget(self.card_unsettled_count)
        self.stats_layout.addWidget(self.card_projects_count)
        main_layout.addLayout(self.stats_layout)

        # ۴. تب‌های اختصاصی مالی
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.06);
                background-color: #121826;
                border-radius: 10px;
                padding: 14px;
            }
            QTabBar::tab {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 9px 20px;
                margin-left: 6px;
                font-weight: 600;
                font-size: 12.5px;
            }
            QTabBar::tab:selected {
                background-color: #6366F1;
                color: #FFFFFF;
                font-weight: 700;
            }
        """)

        # تب ۱: حساب و بدهی کل استودیوها
        self.tab_studio_overview = self._create_card_tab_container("studios")
        self.tab_widget.addTab(self.tab_studio_overview, "حساب و بدهی کل استودیوها")

        # تب ۲: پروژه‌های دارای مانده
        self.tab_receivables = self._create_card_tab_container("receivables")
        self.tab_widget.addTab(self.tab_receivables, "پروژه‌های دارای مانده")

        # تب ۳: دفتر کل تراکنش‌ها
        self.tab_transactions = self._create_card_tab_container("transactions")
        self.tab_widget.addTab(self.tab_transactions, "دفتر کل تراکنش‌ها")

        # تب ۴: گزارش ماهانه درآمد
        self.tab_monthly = self._build_monthly_income_tab()
        self.tab_widget.addTab(self.tab_monthly, "درآمد ماهانه سال جاری")

        main_layout.addWidget(self.tab_widget, stretch=1)
        self._load_clients_filter_options()

    def _connect_signals(self):
        trigger = lambda *args: QTimer.singleShot(0, self.refresh_all_financial_data)
        global_signals.transaction_recorded.connect(trigger)
        global_signals.project_created.connect(trigger)
        global_signals.project_updated.connect(trigger)
        global_signals.project_deleted.connect(trigger)
        global_signals.project_archived.connect(trigger)
        global_signals.project_unarchived.connect(trigger)
        global_signals.revision_added.connect(trigger)
        global_signals.client_balance_updated.connect(lambda *_: self._load_clients_filter_options())

    def _load_clients_filter_options(self):
        current_id = self.combo_filter_client.currentData()
        self.combo_filter_client.blockSignals(True)
        self.combo_filter_client.clear()
        self.combo_filter_client.addItem("همه استودیوها", 0)
        
        with db.get_session() as session:
            clients = session.scalars(select(Client).order_by(Client.company, Client.full_name)).all()
            for c in clients:
                display = c.company or c.full_name
                self.combo_filter_client.addItem(display, c.id)

        idx = self.combo_filter_client.findData(current_id)
        if idx >= 0:
            self.combo_filter_client.setCurrentIndex(idx)
        self.combo_filter_client.blockSignals(False)

    def _reset_filters(self):
        self.combo_filter_client.setCurrentIndex(0)
        self.combo_filter_date.setCurrentIndex(0)
        self.combo_filter_status.setCurrentIndex(0)

    def _create_card_tab_container(self, category_key: str) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(0, 2, 0, 8)
        c_lay.setSpacing(8)
        c_lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        lay.addWidget(scroll)

        if category_key == "studios":
            self.studios_layout = c_lay
        elif category_key == "receivables":
            self.receivables_layout = c_lay
        elif category_key == "transactions":
            self.transactions_layout = c_lay

        return widget

    def _build_monthly_income_tab(self) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(14)

        self.revenue_chart = RevenueBarChartWidget()
        lay.addWidget(self.revenue_chart)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.monthly_cards_layout = QVBoxLayout(container)
        self.monthly_cards_layout.setContentsMargins(0, 2, 0, 8)
        self.monthly_cards_layout.setSpacing(8)
        self.monthly_cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(container)
        lay.addWidget(scroll, stretch=1)
        return widget

    def refresh_all_financial_data(self):
        client_id = self.combo_filter_client.currentData()
        client_id_val = client_id if (client_id and client_id > 0) else None
        date_key = self.combo_filter_date.currentData() or "all"
        status_filter = self.combo_filter_status.currentData() or "all"

        data = FinanceController.get_financial_dashboard_data(
            client_id=client_id_val,
            date_range_key=date_key,
            status_filter=status_filter
        )

        cards = data["summary_cards"]
        self.card_total_contracts.animate_to_value(cards["total_contracts"])
        self.card_total_received.animate_to_value(cards["total_received"])
        self.card_total_remaining.animate_to_value(cards["total_remaining"])
        self.card_unsettled_count.animate_to_value(cards["unsettled_count"])
        self.card_projects_count.animate_to_value(cards["total_projects"])

        self._render_studios_matrix_cards(data["studio_matrix"])
        self._render_receivables_cards(data["receivables"])
        self._render_transactions_cards(data["transactions"])
        self._render_monthly_cards(data["monthly_income"])

    def _render_studios_matrix_cards(self, studio_matrix: List[dict]):
        while self.studios_layout.count():
            item = self.studios_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not studio_matrix:
            empty = ModernEmptyStateWidget(
                title="هیچ استودیوی واجد شرایط مالی یافت نشد",
                description="تنها استودیوهایی که پروژه‌های تکمیل‌شده و تحویل‌شده به آتلیه دارند در این بخش محاسبه می‌شوند.",
                button_text=""
            )
            self.studios_layout.addWidget(empty)
            return

        for s in studio_matrix:
            card = StudioLedgerCard(s, on_settle_callback=self._open_payment_for_studio)
            self.studios_layout.addWidget(card)

    def _render_receivables_cards(self, receivables: List[dict]):
        while self.receivables_layout.count():
            item = self.receivables_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not receivables:
            empty = ModernEmptyStateWidget(
                title="هیچ پروژه دارای مانده بدهی یافت نشد",
                description="تمامی پروژه‌های تحویل‌شده به آتلیه کاملاً تسویه شده‌اند و طلبی باقی نمانده است.",
                button_text=""
            )
            self.receivables_layout.addWidget(empty)
            return

        for r in receivables:
            card = ReceivableProjectCard(
                r, 
                on_pay_callback=self._open_payment_for_project,
                on_invoice_callback=self._open_invoice_for_project
            )
            self.receivables_layout.addWidget(card)

    def _render_transactions_cards(self, transactions: List[dict]):
        while self.transactions_layout.count():
            item = self.transactions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not transactions:
            empty = ModernEmptyStateWidget(
                title="هیچ تراکنش مالی ثبت نشده است",
                description="واریزی‌ها و تسویه‌حساب‌های ثبت‌شده در این بخش به عنوان دفتر کل نگهداری می‌شوند.",
                button_text=""
            )
            self.transactions_layout.addWidget(empty)
            return

        for t in transactions:
            card = TransactionLedgerCard(t, on_delete_cb=self._handle_delete_transaction)
            self.transactions_layout.addWidget(card)

    def _render_monthly_cards(self, monthly_data: List[dict]):
        if hasattr(self, "revenue_chart"):
            self.revenue_chart.set_data(monthly_data)

        while self.monthly_cards_layout.count():
            item = self.monthly_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for m in monthly_data:
            card = MonthlyPerformanceCard(m)
            self.monthly_cards_layout.addWidget(card)

    def _handle_delete_transaction(self, transaction_id: int, amount: int):
        if StudioConfirmDialog.ask(
            self.window(),
            title="حذف تراکنش مالی",
            message=f"آیا از حذف تراکنش دریافتی به مبلغ {format_toman(amount)} اطمینان دارید؟",
            details="پس از حذف، این مبلغ مجدداً به عنوان مانده بدهی پروژه و استودیو لحاظ خواهد شد.",
            confirm_text="حذف تراکنش",
            is_danger=True,
            icon_name="trash"
        ):
            if FinanceController.delete_transaction(transaction_id):
                global_signals.transaction_recorded.emit(0)
                global_signals.show_toast.emit("تراکنش مالی با موفقیت حذف شد.", "info")
                self.refresh_all_financial_data()

    def _open_new_transaction_dialog(self):
        diag = NewTransactionDialog(None, None, self.window())
        diag.exec()

    def _open_payment_for_studio(self, client_id: int):
        diag = NewTransactionDialog(target_project_id=None, target_client_id=client_id, parent=self.window())
        diag.exec()

    def _open_payment_for_project(self, project_id: int):
        diag = NewTransactionDialog(target_project_id=project_id, target_client_id=None, parent=self.window())
        diag.exec()

    def _open_invoice_for_project(self, project_id: int):
        project = ProjectController.get_project_by_id(project_id)
        if project and project.client_id:
            diag = StudioInvoiceDialog(project.client_id, initial_project_id=project_id, parent=self.window())
            diag.exec()

    def _export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "ذخیره گزارش مالی اکسل", "CutterLog_Financial_Report.xlsx", "Excel Files (*.xlsx)"
        )
        if file_path:
            client_id = self.combo_filter_client.currentData()
            client_id_val = client_id if (client_id and client_id > 0) else None
            date_key = self.combo_filter_date.currentData() or "all"
            status_filter = self.combo_filter_status.currentData() or "all"

            data = FinanceController.get_financial_dashboard_data(
                client_id=client_id_val,
                date_range_key=date_key,
                status_filter=status_filter
            )

            txs = [{
                "id": t["id"],
                "project": t["project_title"],
                "client": t["client_name"],
                "amount": t["amount"],
                "date": t["paid_at"].strftime("%Y-%m-%d") if t["paid_at"] else ""
            } for t in data["transactions"]]

            if export_transactions_to_excel(txs, file_path):
                StudioConfirmDialog.ask(
                    self, 
                    title="موفقیت", 
                    message="فایل اکسل گزارش مالی با موفقیت صادر شد.", 
                    details=f"مسیر ذخیره:\n{file_path}",
                    confirm_text="متوجه شدم",
                    icon_name="check"
                )
            else:
                StudioConfirmDialog.ask(
                    self, 
                    title="خطا", 
                    message="خطا در تولید فایل اکسل.", 
                    is_danger=True,
                    icon_name="alert"
                )