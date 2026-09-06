# ==================================================
# FILE: widgets/copilot_briefing_card.py
# ==================================================
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from core.copilot_engine import CopilotEngine
from core.icon_provider import IconProvider
from core.signals import global_signals


class CopilotBriefingCard(QFrame):
    """
    کادر فشرده و خلاصه دستیار هوشمند استودیو برای قرارگیری در کنار ساعت
    """
    open_insights_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CopilotBriefingCompactFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QFrame#CopilotBriefingCompactFrame {
                background-color: rgba(15, 20, 35, 0.65);
                border: 1px solid rgba(99, 102, 241, 0.14);
                border-radius: 14px;
            }
            QFrame#CopilotBriefingCompactFrame:hover {
                border: 1px solid rgba(99, 102, 241, 0.28);
                background-color: rgba(18, 24, 42, 0.75);
            }
            QLabel {
                background: transparent;
                border: none;
                font-family: 'Vazirmatn';
            }
        """)
        self.setMouseTracking(True)
        self.init_ui()
        self.refresh_briefing()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconProvider.get_pixmap("sparkles", "#818CF8", size=15))
        top_row.addWidget(lbl_icon)

        lbl_title = QLabel("دستیار هوشمند")
        lbl_title.setStyleSheet("font-size: 12.5px; font-weight: 800; color: #F1F5F9;")
        top_row.addWidget(lbl_title)

        live_dot = QLabel("● زنده")
        live_dot.setStyleSheet("""
            font-size: 8.5px;
            font-weight: 700;
            color: #38BDF8;
            background-color: rgba(56, 189, 248, 0.08);
            border: 1px solid rgba(56, 189, 248, 0.18);
            border-radius: 10px;
            padding: 2px 7px;
        """)
        top_row.addWidget(live_dot)
        top_row.addStretch()

        btn_more = QPushButton("تحلیل جامع ←")
        btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_more.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(99, 102, 241, 0.10);
                color: #818CF8;
                border: 1px solid rgba(99, 102, 241, 0.22);
                border-radius: 6px;
                padding: 3px 10px;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: rgba(99, 102, 241, 0.22);
                color: #A5B4FC;
                border: 1px solid rgba(99, 102, 241, 0.4);
            }
        """)
        btn_more.clicked.connect(self.open_insights_requested.emit)
        top_row.addWidget(btn_more)

        layout.addLayout(top_row)

        self.points_container = QVBoxLayout()
        self.points_container.setSpacing(4)
        layout.addLayout(self.points_container)

    def refresh_briefing(self):
        while self.points_container.count():
            item = self.points_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        briefing = CopilotEngine.generate_daily_briefing()
        bullets = briefing.get("bullet_points", [])

        # نمایش ۲ الی ۳ مورد از مهم‌ترین پیام‌ها برای حفظ تناسب ارتفاع
        for b in bullets[:2]:
            row = QHBoxLayout()
            row.setContentsMargins(8, 3, 8, 3)
            row.setSpacing(6)
            row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            icon_lbl = QLabel(b.get("icon", "•"))
            icon_lbl.setStyleSheet("font-size: 10px;")
            row.addWidget(icon_lbl)

            txt_lbl = QLabel(b.get("text", ""))
            txt_lbl.setWordWrap(False)
            txt_lbl.setStyleSheet("font-size: 10.5px; color: #9CA3AF; font-weight: 400;")
            row.addWidget(txt_lbl, stretch=1)

            pill_frame = QFrame()
            pill_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.02); border-radius: 6px;")
            pill_frame.setLayout(row)
            self.points_container.addWidget(pill_frame)