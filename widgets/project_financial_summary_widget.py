# ==================================================
# FILE: widgets/project_financial_summary_widget.py
# ==================================================
from typing import Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from core.persian_utils import format_toman, to_persian_numbers


class MetricBlock(QFrame):
    """بلاک مالی ساده، بدون Outline کپسولی و دارای تایپوگرافی خوانا"""
    def __init__(self, title: str, value_text: str, sub_text: str = "", accent_color: str = "#F8FAFC", parent=None):
        super().__init__(parent)
        self.setObjectName("MetricBlockFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(70)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # عنوان شاخص
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("""
            font-family: 'Vazirmatn';
            font-size: 11px;
            font-weight: 500;
            color: #8F909D;
            background: transparent;
            border: none;
        """)
        layout.addWidget(lbl_title)

        # ردیف مقدار و توضیحات
        val_row = QHBoxLayout()
        val_row.setContentsMargins(0, 0, 0, 0)
        val_row.setSpacing(8)
        val_row.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        lbl_val = QLabel(value_text)
        lbl_val.setStyleSheet(f"""
            font-family: 'Vazirmatn';
            font-size: 14.5px;
            font-weight: 800;
            color: {accent_color};
            background: transparent;
            border: none;
        """)
        val_row.addWidget(lbl_val)

        if sub_text:
            lbl_sub = QLabel(sub_text)
            lbl_sub.setStyleSheet("""
                font-family: 'Vazirmatn';
                font-size: 10.5px;
                font-weight: 600;
                color: #10B981;
                background: transparent;
                border: none;
            """)
            val_row.addWidget(lbl_sub)

        val_row.addStretch()
        layout.addLayout(val_row)

        self.setStyleSheet("""
            QFrame#MetricBlockFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            QFrame#MetricBlockFrame:hover {
                background-color: #161F30;
            }
        """)


class ProjectFinancialSummaryWidget(QWidget):
    """ویجت ۳ ستونه خلاصه مالی پروژه بدون کادرهای اضافی"""
    def __init__(self, financial_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.financial_data = financial_data
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(8)

        self._render_metrics()

    def set_data(self, financial_data: Dict[str, Any]):
        self.financial_data = financial_data
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._render_metrics()

    def _render_metrics(self):
        fin = self.financial_data or {}
        total_fee = int(fin.get("total_fee", 0))
        total_paid = int(fin.get("total_paid", 0))
        remaining = int(fin.get("remaining", 0))
        raw_balance = int(fin.get("raw_balance", 0))

        paid_pct = int((total_paid / total_fee) * 100) if total_fee > 0 else 0
        pct_str = f"({to_persian_numbers(paid_pct)}٪ وصول)" if total_fee > 0 else ""

        if total_fee == 0:
            status_text = "بدون مبلغ قرارداد"
            status_color = "#94A3B8"
        elif remaining == 0 and total_paid >= total_fee:
            if raw_balance < 0:
                status_text = f"اضافه پرداخت ({format_toman(abs(raw_balance))})"
                status_color = "#38BDF8"
            else:
                status_text = "تسویه کامل شده ✓"
                status_color = "#10B981"
        elif total_paid == 0:
            status_text = f"در انتظار پرداخت ({format_toman(remaining)})"
            status_color = "#EF4444"
        else:
            status_text = f"پرداخت جزئی (مانده: {format_toman(remaining)})"
            status_color = "#F59E0B"

        card_fee = MetricBlock(
            title="مبلغ کل قرارداد",
            value_text=format_toman(total_fee),
            accent_color="#F8FAFC"
        )

        card_paid = MetricBlock(
            title="مجموع دریافتی‌ها",
            value_text=format_toman(total_paid),
            sub_text=pct_str,
            accent_color="#10B981" if total_paid > 0 else "#94A3B8"
        )

        card_status = MetricBlock(
            title="وضعیت حساب و مانده",
            value_text=status_text,
            accent_color=status_color
        )

        self.cards = [card_fee, card_paid, card_status]
        for i, card in enumerate(self.cards):
            self.grid.addWidget(card, 0, i)
            self.grid.setColumnStretch(i, 1)