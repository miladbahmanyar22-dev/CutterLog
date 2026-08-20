# ==================================================
# FILE: widgets/revenue_bar_chart.py
# ==================================================
from typing import List, Dict, Any
from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QLinearGradient, QFont, QPen

from core.persian_utils import format_toman, to_persian_numbers


class RevenueBarChartWidget(QWidget):
    """
    نمودار میله‌ای اختصاصی و کاملاً ریسپانسیو برای نمایش درآمد ۱۲ ماه سال
    دارای محاسبه خودکار ضخامت میله‌ها و مقیاس فونت متناسب با عرض متغیر پنجره
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMouseTracking(True)
        self.setMinimumHeight(220)
        self.monthly_data: List[Dict[str, Any]] = []
        self.hovered_idx = -1

    def set_data(self, monthly_data: List[Dict[str, Any]]):
        self.monthly_data = monthly_data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())

        margin_top = 28.0
        margin_bottom = 36.0
        margin_x = 16.0

        chart_w = max(10.0, w - (margin_x * 2.0))
        chart_h = max(10.0, h - margin_top - margin_bottom)

        if not self.monthly_data:
            painter.setPen(QColor("#64748B"))
            painter.setFont(QFont("Vazirmatn", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "داده‌ای برای نمایش درآمد ماهانه ثبت نشده است.")
            painter.end()
            return

        max_amount = max([m.get("amount", 0) for m in self.monthly_data] + [1])
        count = len(self.monthly_data)
        col_slot_w = chart_w / max(1, count)
        
        # محاسبه ریسپانسیو ضخامت میله‌ها متناسب با پهنای صفحه
        bar_w = max(12.0, min(36.0, col_slot_w * 0.52))

        # خطوط راهنمای افقی (Grid Lines)
        painter.setPen(QPen(QColor(255, 255, 255, 12), 1, Qt.PenStyle.DashLine))
        for step in range(1, 4):
            y_grid = margin_top + (chart_h * (step / 3.0))
            painter.drawLine(int(margin_x), int(y_grid), int(w - margin_x), int(y_grid))

        for i, item in enumerate(self.monthly_data):
            amount = item.get("amount", 0)
            month_name = item.get("month", "")

            # محاسبه مختصات از راست به چپ
            x_center = margin_x + (i + 0.5) * col_slot_w
            bar_x = x_center - (bar_w / 2.0)

            ratio = amount / max_amount if max_amount > 0 else 0
            bar_h = max(4.0, chart_h * ratio) if amount > 0 else 4.0
            bar_y = margin_top + chart_h - bar_h

            rect = QRectF(bar_x, bar_y, bar_w, bar_h)

            # گرادینت ستون
            grad = QLinearGradient(bar_x, bar_y, bar_x, bar_y + bar_h)
            if i == self.hovered_idx:
                grad.setColorAt(0.0, QColor("#34D399"))
                grad.setColorAt(1.0, QColor("#059669"))
            elif amount > 0:
                grad.setColorAt(0.0, QColor("#818CF8"))
                grad.setColorAt(1.0, QColor("#4F46E5"))
            else:
                grad.setColorAt(0.0, QColor("#1E283D"))
                grad.setColorAt(1.0, QColor("#161F30"))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(rect, 4, 4)

            # نام ماه
            font_size = 8 if col_slot_w < 45 else 9
            painter.setFont(QFont("Vazirmatn", font_size, QFont.Weight.Bold if i == self.hovered_idx else QFont.Weight.Normal))
            painter.setPen(QColor("#F8FAFC" if i == self.hovered_idx else "#94A3B8"))
            lbl_rect = QRectF(x_center - (col_slot_w / 2.0), h - margin_bottom + 8, col_slot_w, 20)
            painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, month_name)

            # مبلغ بالای ستون
            if amount > 0 and (i == self.hovered_idx or (ratio > 0.35 and col_slot_w >= 45)):
                painter.setFont(QFont("Vazirmatn", 8, QFont.Weight.Bold))
                painter.setPen(QColor("#10B981" if i == self.hovered_idx else "#818CF8"))
                val_str = to_persian_numbers(f"{amount // 1_000_000:,} م") if amount >= 1_000_000 else to_persian_numbers(f"{amount // 1_000:,} هـ")
                val_rect = QRectF(x_center - 30, bar_y - 18, 60, 16)
                painter.drawText(val_rect, Qt.AlignmentFlag.AlignCenter, val_str)

        painter.end()

    def mouseMoveEvent(self, event):
        if not self.monthly_data:
            return

        w = float(self.width())
        margin_x = 16.0
        chart_w = max(10.0, w - (margin_x * 2.0))
        col_slot_w = chart_w / len(self.monthly_data)

        pos_x = event.position().x() if hasattr(event, "position") else event.pos().x()
        global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()

        if margin_x <= pos_x <= (w - margin_x):
            idx = int((pos_x - margin_x) // col_slot_w)
            if 0 <= idx < len(self.monthly_data):
                if self.hovered_idx != idx:
                    self.hovered_idx = idx
                    self.update()

                item = self.monthly_data[idx]
                month = item.get("month", "")
                amount_str = format_toman(item.get("amount", 0))
                count_str = to_persian_numbers(item.get("count", 0))
                tip = f"{month}\nدرآمد وصول‌شده: {amount_str}\nتعداد واریزی: {count_str} تراکنش"
                QToolTip.showText(global_pos, tip, self)
                return

        if self.hovered_idx != -1:
            self.hovered_idx = -1
            self.update()
            QToolTip.hideText()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.hovered_idx != -1:
            self.hovered_idx = -1
            self.update()
            QToolTip.hideText()
        super().leaveEvent(event)