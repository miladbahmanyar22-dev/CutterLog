# ==================================================
# FILE: widgets/copilot_briefing_card.py
# ==================================================
import re
from typing import List, Tuple
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QWidget
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QMouseEvent, QPainter, QColor, QLinearGradient, QRadialGradient, QBrush, QPen
)

from core.copilot_engine import CopilotEngine


class CopilotBriefingCard(QFrame):
    """
    کارت بریف هوشمند میز کار با چیدمان خطی یکپارچه و استاندارد راست‌به‌چپ (RTL)
    بدون فاصله ناخواسته بین عنوان و متن
    """
    open_insights_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CopilotBriefingCard")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_hovered = False

        self.init_ui()
        self.refresh_briefing()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ردیف بالای کارت
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_header = QLabel("میزکار هوشمند")
        lbl_header.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 11px;
                font-weight: 700;
                color: #8F909D;
                letter-spacing: 0.3px;
                background: transparent;
                border: none;
            }
        """)
        top_row.addWidget(lbl_header)
        top_row.addStretch()

        lbl_live_badge = QLabel("● زنده")
        lbl_live_badge.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 9px;
                font-weight: 700;
                color: #818CF8;
                background-color: rgba(99, 102, 241, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 8px;
                padding: 1px 7px;
            }
        """)
        top_row.addWidget(lbl_live_badge)
        layout.addLayout(top_row)

        # کانتینر ردیف‌های پیام
        self.rows_container = QVBoxLayout()
        self.rows_container.setContentsMargins(0, 2, 0, 0)
        self.rows_container.setSpacing(4)
        layout.addLayout(self.rows_container)

    def refresh_briefing(self):
        while self.rows_container.count():
            item = self.rows_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                # حذف زیرطرح‌ها در صورت وجود
                sub_layout = item.layout()
                while sub_layout.count():
                    sub_item = sub_layout.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

        # دریافت داده‌ها از موتور کوپایلوت
        briefing = CopilotEngine.generate_daily_briefing()

        rows_spec: List[Tuple[str, str, str]] = [
            ("اولویت اقدام", "#818CF8", briefing["line_action"]),
            ("زمان‌‌بندی", briefing.get("timeline_color", "#38BDF8"), briefing["line_timeline"]),
            ("وضعیت مالی", briefing.get("finance_color", "#34D399"), briefing["line_finance"])
        ]

        for label_text, color_hex, text_content in rows_spec:
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(5)
            row_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # برچسب عنوان ثابت
            lbl_tag = QLabel(f"{label_text}:")
            lbl_tag.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            lbl_tag.setStyleSheet(f"""
                QLabel {{
                    font-family: 'Vazirmatn';
                    font-size: 11px;
                    font-weight: 800;
                    color: {color_hex};
                    background: transparent;
                    border: none;
                }}
            """)
            row_layout.addWidget(lbl_tag)

            # متن اصلی پیام که بلافاصله بعد از دونقطه قرار می‌گیرد
            formatted_text = self._apply_inline_accents(text_content)
            lbl_msg = QLabel()
            lbl_msg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            lbl_msg.setTextFormat(Qt.TextFormat.RichText)
            lbl_msg.setStyleSheet("""
                QLabel {
                    font-family: 'Vazirmatn';
                    font-size: 11px;
                    color: #CBD5E1;
                    background: transparent;
                    border: none;
                }
            """)
            lbl_msg.setText(formatted_text)
            row_layout.addWidget(lbl_msg)

            # فاصله خالی به سمت چپ فرستاده می‌شود تا کل ردیف به راست فشرده و مرتب باشد
            row_layout.addStretch(1)

            self.rows_container.addLayout(row_layout)

    def _apply_inline_accents(self, text_str: str) -> str:
        text_str = re.sub(
            r"«(.*?)»",
            r'<b style="color: #F8FAFC;">«\1»</b>',
            text_str
        )
        text_str = re.sub(
            r"\((.*?)\)",
            r'<span style="color: #A5B4FC;">(\1)</span>',
            text_str
        )
        return text_str

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

        # گرادیانت پس‌زمینه
        grad = QLinearGradient(0, 0, 0, h)
        if self._is_hovered:
            grad.setColorAt(0.0, QColor("#161F30"))
            grad.setColorAt(1.0, QColor("#111726"))
        else:
            grad.setColorAt(0.0, QColor("#121826"))
            grad.setColorAt(1.0, QColor("#0D121D"))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(rect, 12, 12)

        # هاله بنفش مات در گوشه بالای کارت
        radial = QRadialGradient(QPointF(w * 0.82, 0.0), w * 0.55)
        alpha = 34 if self._is_hovered else 18
        radial.setColorAt(0.0, QColor(99, 102, 241, alpha))
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(radial))
        painter.drawRoundedRect(rect, 12, 12)

        # خط باریک رنگی هماهنگ در پایین کارت
        line_rect = QRectF(16.0, h - 2.5, w - 32.0, 1.5)
        line_color = QColor(99, 102, 241, 160 if self._is_hovered else 75)
        painter.setBrush(QBrush(line_color))
        painter.drawRoundedRect(line_rect, 1, 1)

        # بردر کادر
        border_color = QColor(99, 102, 241, 95 if self._is_hovered else 22)
        painter.setPen(QPen(border_color, 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 12, 12)

        painter.end()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.open_insights_requested.emit()
            return
        super().mouseReleaseEvent(event)