# ==================================================
# FILE: time_tracking/widgets/productivity_chart.py
# ==================================================
from typing import List
from datetime import datetime, timedelta
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QFont
from sqlalchemy import select

from database.db_manager import db
from time_tracking.models import WorkSession
from core.persian_utils import to_persian_numbers


class HourlyActivityBarWidget(QWidget):
    """رندر ساعات شبانه‌روز (از ۸ صبح تا ۱۲ شب) و نمایش دوره‌های کاری فعال"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(85)
        self.hourly_active_minutes = [0] * 16  # ساعات 08:00 تا 24:00

    def set_data(self, hourly_minutes: List[int]):
        self.hourly_active_minutes = hourly_minutes
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        margin_b = 24.0
        chart_h = h - margin_b

        slots = 16
        slot_w = w / slots

        for i in range(slots):
            hour = 8 + i
            mins = self.hourly_active_minutes[i] if i < len(self.hourly_active_minutes) else 0
            ratio = min(1.0, mins / 60.0)

            bar_w = slot_w * 0.65
            bar_x = (i * slot_w) + ((slot_w - bar_w) / 2)
            bar_h = max(4.0, chart_h * ratio) if mins > 0 else 4.0
            bar_y = chart_h - bar_h

            color = QColor("#6366F1") if mins > 0 else QColor("#1A2234")
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 3, 3)

            # برچسب ساعت
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QColor("#64748B"))
            painter.drawText(QRectF(i * slot_w, h - 20, slot_w, 18), Qt.AlignmentFlag.AlignCenter, f"{hour:02d}")

        painter.end()


class ProductivityChartCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProductivityChartCard")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("""
            QFrame#ProductivityChartCard {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        lbl_t = QLabel("توزیع زمان فعالیت در طول روز:")
        lbl_t.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        layout.addWidget(lbl_t)

        self.chart = HourlyActivityBarWidget(self)
        layout.addWidget(self.chart)

    def refresh_data(self):
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        hourly_data = [0] * 16

        with db.get_session() as session:
            sessions = session.scalars(
                select(WorkSession).where(WorkSession.start_time >= today_start)
            ).all()

            for s in sessions:
                st = s.start_time
                dur_mins = (s.active_duration or 0) // 60
                if 8 <= st.hour < 24:
                    idx = st.hour - 8
                    hourly_data[idx] = min(60, hourly_data[idx] + dur_mins)

        self.chart.set_data(hourly_data)