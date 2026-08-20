# ==================================================
# FILE: widgets/status_badge.py
# ==================================================
from enum import Enum
from typing import Optional
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class StatusType(str, Enum):
    ACTIVE = "active"          # سبز نیترو/ملایم (در حال تدوین، فعال)
    COMPLETED = "completed"    # زمردی (تکمیل شده، تحویل موفق)
    PENDING = "pending"        # زرد/کهربایی ملایم (منتظر بازبینی، در انتظار)
    WARNING = "warning"        # نارنجی ملایم (نزدیک به ددلاین، اصلاحیه)
    DANGER = "danger"          # قرمز ملایم (تأخیر، ددلاین گذشته)
    NEUTRAL = "neutral"        # خاکستری ملایم/خنثی (آرشیو شده، بدون فعالیت)


STATUS_THEMES = {
    StatusType.ACTIVE: {
        "bg": "rgba(52, 211, 153, 0.10)",
        "border": "rgba(52, 211, 153, 0.25)",
        "text": "#34D399",
        "dot": "#10B981",
        "symbol": "●"
    },
    StatusType.COMPLETED: {
        "bg": "rgba(16, 185, 129, 0.12)",
        "border": "rgba(16, 185, 129, 0.28)",
        "text": "#10B981",
        "dot": "#10B981",
        "symbol": "✓"
    },
    StatusType.PENDING: {
        "bg": "rgba(245, 158, 11, 0.10)",
        "border": "rgba(245, 158, 11, 0.25)",
        "text": "#FBBF24",
        "dot": "#F59E0B",
        "symbol": "●"
    },
    StatusType.WARNING: {
        "bg": "rgba(249, 115, 22, 0.10)",
        "border": "rgba(249, 115, 22, 0.25)",
        "text": "#FB923C",
        "dot": "#EA580C",
        "symbol": "!"
    },
    StatusType.DANGER: {
        "bg": "rgba(239, 68, 68, 0.10)",
        "border": "rgba(239, 68, 68, 0.28)",
        "text": "#F87171",
        "dot": "#EF4444",
        "symbol": "!"
    },
    StatusType.NEUTRAL: {
        "bg": "rgba(148, 163, 184, 0.08)",
        "border": "rgba(148, 163, 184, 0.18)",
        "text": "#94A3B8",
        "dot": "#64748B",
        "symbol": "●"
    },
}


class StatusPillBadge(QFrame):
    """بج کپسولی استاندارد، بدون وابستگی مخرب و دارای ابعاد پایدار"""
    def __init__(
        self,
        label: str,
        status_type: StatusType = StatusType.ACTIVE,
        custom_symbol: Optional[str] = None,
        parent=None
    ):
        super().__init__(parent)
        self.label_text = label
        self.status_type = status_type
        self.custom_symbol = custom_symbol

        self.setObjectName("StatusPillBadgeFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(24)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.init_ui()

    def init_ui(self):
        theme = STATUS_THEMES.get(self.status_type, STATUS_THEMES[StatusType.NEUTRAL])
        symbol = self.custom_symbol or theme["symbol"]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_indicator = QLabel(symbol)
        self.lbl_indicator.setStyleSheet(f"""
            font-family: 'Vazirmatn', sans-serif;
            font-size: 9.5px;
            font-weight: 900;
            color: {theme['dot']};
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.lbl_indicator)

        self.lbl_text = QLabel(self.label_text)
        self.lbl_text.setStyleSheet(f"""
            font-family: 'Vazirmatn';
            font-size: 11px;
            font-weight: 600;
            color: {theme['text']};
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.lbl_text)

        self.setStyleSheet(f"""
            QFrame#StatusPillBadgeFrame {{
                background-color: {theme['bg']};
                border: 1px solid {theme['border']};
                border-radius: 12px;
            }}
        """)

    def update_status(self, label: str, status_type: StatusType, custom_symbol: Optional[str] = None):
        self.label_text = label
        self.status_type = status_type
        self.custom_symbol = custom_symbol

        theme = STATUS_THEMES.get(self.status_type, STATUS_THEMES[StatusType.NEUTRAL])
        symbol = self.custom_symbol or theme["symbol"]

        self.lbl_indicator.setText(symbol)
        self.lbl_indicator.setStyleSheet(f"color: {theme['dot']}; background: transparent; border: none; font-size: 9.5px; font-weight: 900;")
        self.lbl_text.setText(self.label_text)
        self.lbl_text.setStyleSheet(f"color: {theme['text']}; background: transparent; border: none; font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600;")
        
        self.setStyleSheet(f"""
            QFrame#StatusPillBadgeFrame {{
                background-color: {theme['bg']};
                border: 1px solid {theme['border']};
                border-radius: 12px;
            }}
        """)