# ==================================================
# FILE: widgets/copilot_briefing_card.py
# ==================================================
import re
from typing import List, Tuple
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QGridLayout, QWidget
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QMouseEvent, QPainter, QColor, QLinearGradient, QRadialGradient, QBrush, QPen
)

from core.copilot_engine import CopilotEngine
from core.project_controller import ProjectController
from core.finance_controller import FinanceController
from core.persian_utils import format_toman, to_persian_numbers


class CopilotBriefingCard(QFrame):
    """
    کارت بریف هوشمند میز کار با چیدمان گرید و متن‌های چپ‌چین
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

        # گرید ستونی برای چیدمان اطلاعات
        self.grid_container = QGridLayout()
        self.grid_container.setContentsMargins(0, 2, 0, 0)
        self.grid_container.setHorizontalSpacing(4)
        self.grid_container.setVerticalSpacing(4)
        
        self.grid_container.setColumnStretch(0, 0)
        self.grid_container.setColumnStretch(1, 0)
        self.grid_container.setColumnStretch(2, 1)

        layout.addLayout(self.grid_container)

    def refresh_briefing(self):
        # پاکسازی خانه‌های گرید قبلی
        while self.grid_container.count():
            item = self.grid_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        # استخراج داده‌های زنده و واقعی
        radar = CopilotEngine.get_pipeline_radar()
        rec_proj = CopilotEngine.recommend_next_project()
        fin_data = FinanceController.get_financial_dashboard_data(date_range_key="all")
        active_projects = ProjectController.get_active_projects()

        rows_spec: List[Tuple[str, str, str]] = []

        # ۱. خط اول: تدوین و اقدام
        if rec_proj:
            line_1 = f"پیشنهاد تدوین «{rec_proj['title']}» ({rec_proj['recommendation_reason']})"
        elif active_projects:
            p_top = active_projects[0]
            c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p_top)
            line_1 = f"پروژه فعال «{p_top.couple_names or p_top.title}» ({to_persian_numbers(pct)}٪ پیشرفت)"
        else:
            line_1 = "تمامی پروژه‌های فعال تکمیل شده‌اند و پایپ‌لاین آزاد است."
        rows_spec.append(("اولویت اقدام", "#818CF8", self._apply_inline_accents(line_1)))

        # ۲. خط دوم: رادار زمان و ددلاین
        if radar.get("urgent_deadlines"):
            risk = radar["urgent_deadlines"][0]
            line_2 = f"ددلاین فوری «{risk['title']}» ({risk['warning']})"
            tag_color = "#38BDF8"
        elif radar.get("pending_review_alerts"):
            alert = radar["pending_review_alerts"][0]
            line_2 = f"یادآوری بازبینی «{alert['title']}» ({alert['notice']})"
            tag_color = "#38BDF8"
        elif radar.get("heavy_revisions"):
            rev = radar["heavy_revisions"][0]
            line_2 = f"اصلاحیه فعال «{rev['title']}» ({rev['notice']})"
            tag_color = "#38BDF8"
        else:
            line_2 = "زمان‌بندی پایدار است و هیچ سررسید بحرانی ثبت نشده است."
            tag_color = "#38BDF8"
        rows_spec.append(("زمان‌‌بندی", tag_color, self._apply_inline_accents(line_2)))

        # ۳. خط سوم: مطالبات مالی
        cards = fin_data.get("summary_cards", {})
        total_remaining = cards.get("total_remaining", 0)
        unsettled_count = cards.get("unsettled_count", 0)

        if total_remaining > 0:
            line_3 = f"مطالبات وصول‌نشده {format_toman(total_remaining)} ({to_persian_numbers(unsettled_count)} پروژه)"
            fin_tag_color = "#34D399"
        else:
            line_3 = "حساب تمامی پروژه‌های تحویل‌شده تسویه است."
            fin_tag_color = "#34D399"
        rows_spec.append(("وضعیت مالی", fin_tag_color, self._apply_inline_accents(line_3)))

        # قرار دادن ردیف‌ها در گرید با متن‌های چپ‌چین
        for row_idx, (label_text, color_hex, text_html) in enumerate(rows_spec):
            # ستون ۰: برچسب عنوان با عرض ثابت
            lbl_tag = QLabel(label_text)
            lbl_tag.setFixedWidth(66)
            lbl_tag.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignAbsolute)
            lbl_tag.setStyleSheet(f"""
                QLabel {{
                    font-family: 'Vazirmatn';
                    font-size: 11px;
                    font-weight: 700;
                    color: {color_hex};
                    background: transparent;
                    border: none;
                }}
            """)
            self.grid_container.addWidget(lbl_tag, row_idx, 0)

            # ستون ۱: دونقطه
            lbl_colon = QLabel(":")
            lbl_colon.setFixedWidth(8)
            lbl_colon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_colon.setStyleSheet("""
                QLabel {
                    font-family: 'Vazirmatn';
                    font-size: 11.5px;
                    font-weight: 700;
                    color: #64748B;
                    background: transparent;
                    border: none;
                }
            """)
            self.grid_container.addWidget(lbl_colon, row_idx, 1)

            # ستون ۲: متن اطلاعات با چپ‌چین‌سازی کامل (direction: ltr و text-align: left)
            lbl_msg = QLabel()
            lbl_msg.setTextFormat(Qt.TextFormat.RichText)
            lbl_msg.setWordWrap(False)
            lbl_msg.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignAbsolute)
            lbl_msg.setStyleSheet("""
                QLabel {
                    font-family: 'Vazirmatn';
                    font-size: 11px;
                    color: #94A3B8;
                    background: transparent;
                    border: none;
                }
            """)
            # اعمال جهت LTR و چپ‌چین برای متن‌ها
            lbl_msg.setText(f"<div style='direction: ltr; text-align: left;'>{text_html}</div>")
            self.grid_container.addWidget(lbl_msg, row_idx, 2)

    def _apply_inline_accents(self, text_str: str) -> str:
        text_str = re.sub(
            r"«(.*?)»",
            r"<b style='color: #F8FAFC;'>«\1»</b>",
            text_str
        )
        text_str = re.sub(
            r"\((.*?)\)",
            r"<span style='color: #A5B4FC;'>(\1)</span>",
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