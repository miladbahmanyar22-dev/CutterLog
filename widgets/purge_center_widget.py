# ==================================================
# FILE: widgets/purge_center_widget.py
# ==================================================
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QBrush, QPen, QMouseEvent, QFont
)

from core.purge_manager import PurgeManager
from core.persian_utils import to_persian_numbers
from core.icon_provider import IconProvider
from widgets.studio_dialog_base import StudioConfirmDialog
from core.signals import global_signals


# پالت‌های رنگی اختصاصی و جذاب برای هر قلمرو
SCOPE_COLOR_PALETTES = {
    "time_tracking": {
        "text": "#C084FC",
        "dot": "#A855F7",
        "bg_active": "rgba(168, 85, 247, 0.16)",
        "border_active": "rgba(168, 85, 247, 0.45)",
        "bg_idle": "rgba(168, 85, 247, 0.08)",
        "border_idle": "rgba(168, 85, 247, 0.22)"
    },
    "archived_projects": {
        "text": "#FBBF24",
        "dot": "#F59E0B",
        "bg_active": "rgba(245, 158, 11, 0.18)",
        "border_active": "rgba(245, 158, 11, 0.45)",
        "bg_idle": "rgba(245, 158, 11, 0.08)",
        "border_idle": "rgba(245, 158, 11, 0.22)"
    },
    "active_projects": {
        "text": "#FDA4AF",
        "dot": "#F43F5E",
        "bg_active": "rgba(244, 63, 94, 0.20)",
        "border_active": "rgba(244, 63, 94, 0.55)",
        "bg_idle": "rgba(244, 63, 94, 0.09)",
        "border_idle": "rgba(244, 63, 94, 0.25)"
    },
    "financial_ledger": {
        "text": "#34D399",
        "dot": "#10B981",
        "bg_active": "rgba(16, 185, 129, 0.20)",
        "border_active": "rgba(16, 185, 129, 0.50)",
        "bg_idle": "rgba(16, 185, 129, 0.09)",
        "border_idle": "rgba(16, 185, 129, 0.25)"
    },
    "studios_directory": {
        "text": "#22D3EE",
        "dot": "#06B6D4",
        "bg_active": "rgba(6, 182, 212, 0.18)",
        "border_active": "rgba(6, 182, 212, 0.45)",
        "bg_idle": "rgba(6, 182, 212, 0.08)",
        "border_idle": "rgba(6, 182, 212, 0.22)"
    },
    "branding_settings": {
        "text": "#818CF8",
        "dot": "#6366F1",
        "bg_active": "rgba(99, 102, 241, 0.20)",
        "border_active": "rgba(99, 102, 241, 0.50)",
        "bg_idle": "rgba(99, 102, 241, 0.09)",
        "border_idle": "rgba(99, 102, 241, 0.25)"
    },
    "media_vault": {
        "text": "#38BDF8",
        "dot": "#0284C7",
        "bg_active": "rgba(56, 189, 248, 0.18)",
        "border_active": "rgba(56, 189, 248, 0.45)",
        "bg_idle": "rgba(56, 189, 248, 0.08)",
        "border_idle": "rgba(56, 189, 248, 0.22)"
    }
}


class UltraMetricBadge(QWidget):
    """کپسول آماری اختصاصی با نور نئونی، دات چشم‌نواز و ترکیب رنگی جذاب"""
    def __init__(self, palette: dict, parent=None):
        super().__init__(parent)
        self.palette = palette
        self.text_value = "—"
        self.is_active = False
        self.setFixedHeight(24)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

    def set_value(self, text: str, is_active: bool = False):
        self.text_value = text
        self.is_active = is_active
        self.updateGeometry()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

        p = self.palette
        bg_col = QColor(p["bg_active"] if self.is_active else p["bg_idle"])
        border_col = QColor(p["border_active"] if self.is_active else p["border_idle"])
        text_col = QColor(p["text"])
        dot_col = QColor(p["dot"])

        radius = h / 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_col))
        painter.drawRoundedRect(rect, radius, radius)

        painter.setPen(QPen(border_col, 1.2 if self.is_active else 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        dot_radius = 2.5
        dot_x = w - 11.0
        dot_y = h / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        glow_c = QColor(dot_col.red(), dot_col.green(), dot_col.blue(), 55 if self.is_active else 25)
        painter.setBrush(QBrush(glow_c))
        painter.drawEllipse(QPointF(dot_x, dot_y), dot_radius + 2.0, dot_radius + 2.0)

        painter.setBrush(QBrush(dot_col))
        painter.drawEllipse(QPointF(dot_x, dot_y), dot_radius, dot_radius)

        font = QFont("Vazirmatn", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(text_col)

        text_rect = QRectF(8.0, 0.0, w - 21.0, h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, self.text_value)
        painter.end()


class ScenarioProfileCard(QFrame):
    """کارت مدرن و استودیویی برای هر یک از پروفایل‌های پاک‌سازی سریع"""
    clicked = Signal()

    def __init__(self, key: str, title: str, subtitle: str, tag: str, 
                 accent_hex: str, icon_key: str, parent=None):
        super().__init__(parent)
        self.profile_key = key
        self.title_text = title
        self.subtitle_text = subtitle
        self.tag_text = tag
        self.accent_color = QColor(accent_hex)
        self.icon_key = icon_key

        self._is_active = False
        self._is_hovered = False

        self.setObjectName("ScenarioProfileCard")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # آیکون کوچک با کادر نئونی
        self.icon_plate = QFrame()
        self.icon_plate.setFixedSize(32, 32)
        ip_lay = QVBoxLayout(self.icon_plate)
        ip_lay.setContentsMargins(0, 0, 0, 0)
        ip_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_icon = QLabel()
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        ip_lay.addWidget(self.lbl_icon)
        layout.addWidget(self.icon_plate)

        # عنوان و زیرعنوان سناریو
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; background: transparent; border: none;")
        text_col.addWidget(self.lbl_title)

        self.lbl_sub = QLabel(self.subtitle_text)
        self.lbl_sub.setStyleSheet("font-family: 'Vazirmatn'; font-size: 9px; color: #8F98A8; background: transparent; border: none;")
        text_col.addWidget(self.lbl_sub)

        layout.addLayout(text_col, stretch=1)

        # بج متنی وضعیت سناریو
        self.lbl_tag = QLabel(self.tag_text)
        self.lbl_tag.setFixedHeight(20)
        self.lbl_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_tag)

        self._update_appearance()

    def set_active_state(self, active: bool):
        if self._is_active != active:
            self._is_active = active
            self._update_appearance()
            self.update()

    def _update_appearance(self):
        c = self.accent_color
        r, g, b = c.red(), c.green(), c.blue()

        self.lbl_icon.setPixmap(IconProvider.get_pixmap(self.icon_key, c.name(), size=15))

        self.icon_plate.setStyleSheet(f"""
            QFrame {{
                background-color: rgba({r}, {g}, {b}, {0.20 if self._is_active else 0.10});
                border: 1px solid rgba({r}, {g}, {b}, {0.45 if self._is_active else 0.20});
                border-radius: 6px;
            }}
        """)

        title_color = "#FFFFFF" if self._is_active else "#F1F5F9"
        self.lbl_title.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; color: {title_color}; background: transparent; border: none;")

        self.lbl_tag.setStyleSheet(f"""
            QLabel {{
                font-family: 'Vazirmatn';
                font-size: 8.5px;
                font-weight: 800;
                color: {c.name()};
                background-color: rgba({r}, {g}, {b}, {0.20 if self._is_active else 0.10});
                border: 1px solid rgba({r}, {g}, {b}, {0.45 if self._is_active else 0.22});
                border-radius: 4px;
                padding: 1px 6px;
            }}
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        c = self.accent_color

        bg_grad = QLinearGradient(0, 0, w, h)
        if self._is_active:
            bg_grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 38))
            bg_grad.setColorAt(1.0, QColor("#0D1322"))
            border_color = QColor(c.red(), c.green(), c.blue(), 180)
        else:
            if self._is_hovered:
                bg_grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 18))
                bg_grad.setColorAt(1.0, QColor("#111726"))
                border_color = QColor(c.red(), c.green(), c.blue(), 90)
            else:
                bg_grad.setColorAt(0.0, QColor("#121828"))
                bg_grad.setColorAt(1.0, QColor("#0E1320"))
                border_color = QColor(255, 255, 255, 12)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_grad))
        painter.drawRoundedRect(rect, 8, 8)

        painter.setPen(QPen(border_color, 1.2 if (self._is_active or self._is_hovered) else 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 8, 8)
        painter.end()

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class UltraStudioPurgeCard(QFrame):
    """کارت مدرن و شیشه‌ای انتخاب قلمرو پاک‌سازی متناسب با گرید ۲ ستونه"""
    toggled = Signal()

    def __init__(self, scope_key: str, title: str, description: str, 
                 icon_key: str, badge_text: str, is_danger: bool = False, parent=None):
        super().__init__(parent)
        self.scope_key = scope_key
        self.title_text = title
        self.desc_text = description
        self.icon_key = icon_key
        self.is_danger = is_danger
        self._is_checked = False
        self._is_hovered = False

        self.palette = SCOPE_COLOR_PALETTES.get(scope_key, SCOPE_COLOR_PALETTES["branding_settings"])

        self.setObjectName("UltraStudioPurgeCardFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.init_ui(badge_text)

    def init_ui(self, badge_text: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # ۱. دکمه چک‌باکس کپسولی سفارشی
        self.chk_indicator = QLabel(self)
        self.chk_indicator.setFixedSize(20, 20)
        self.chk_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.chk_indicator)

        # ۲. آیکون موضوعی کارت
        self.icon_box = QFrame()
        self.icon_box.setFixedSize(36, 36)
        icon_box_layout = QVBoxLayout(self.icon_box)
        icon_box_layout.setContentsMargins(0, 0, 0, 0)
        icon_box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_icon = QLabel()
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        icon_box_layout.addWidget(self.lbl_icon)
        layout.addWidget(self.icon_box)

        # ۳. عنوان و متن توضیحات با سایز بهینه‌سازی‌شده
        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_title = QLabel(self.title_text)
        self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; background: transparent; border: none;")
        info_col.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(self.desc_text)
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 9.5px; color: #8F98A8; background: transparent; border: none; line-height: 1.25;")
        info_col.addWidget(self.lbl_desc)

        layout.addLayout(info_col, stretch=1)

        # ۴. کپسول آماری
        self.metric_badge = UltraMetricBadge(self.palette, self)
        self.metric_badge.set_value(badge_text, is_active=False)
        layout.addWidget(self.metric_badge)

        self._update_state()

    def set_badge(self, text: str):
        self.metric_badge.set_value(text, is_active=self._is_checked)

    def is_checked(self) -> bool:
        return self._is_checked

    def set_checked(self, checked: bool):
        if self._is_checked != checked:
            self._is_checked = checked
            self._update_state()
            self.update()

    def _update_state(self):
        accent_hex = self.palette["dot"]

        if self._is_checked:
            chk_bg = accent_hex
            chk_border = self.palette["text"]
            chk_mark = "✓"
            chk_text_color = "#FFFFFF"
        else:
            chk_bg = "rgba(18, 24, 38, 0.75)"
            chk_border = "rgba(255, 255, 255, 0.16)"
            chk_mark = ""
            chk_text_color = "transparent"

        self.chk_indicator.setText(chk_mark)
        self.chk_indicator.setStyleSheet(f"""
            QLabel {{
                font-family: 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: 900;
                color: {chk_text_color};
                background-color: {chk_bg};
                border: 1.5px solid {chk_border};
                border-radius: 5px;
            }}
        """)

        self.icon_box.setStyleSheet(f"""
            QFrame {{
                background-color: {self.palette["bg_active"] if self._is_checked else self.palette["bg_idle"]};
                border: 1px solid {self.palette["border_active"] if self._is_checked else self.palette["border_idle"]};
                border-radius: 8px;
            }}
        """)
        self.lbl_icon.setPixmap(IconProvider.get_pixmap(self.icon_key, self.palette["text"], size=16))

        title_color = "#FDA4AF" if self.is_danger else "#F8FAFC"
        self.lbl_title.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: {title_color}; background: transparent; border: none;")

        self.metric_badge.set_value(self.metric_badge.text_value, is_active=self._is_checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

        bg_grad = QLinearGradient(0, 0, w, h)
        if self._is_checked:
            if self.is_danger:
                bg_grad.setColorAt(0.0, QColor("#1F0F14"))
                bg_grad.setColorAt(1.0, QColor("#120A0E"))
                border_color = QColor("#F43F5E")
            else:
                bg_grad.setColorAt(0.0, QColor("#161F36"))
                bg_grad.setColorAt(1.0, QColor("#0D1322"))
                border_color = QColor(self.palette["dot"])
        else:
            if self._is_hovered:
                bg_grad.setColorAt(0.0, QColor("#151D2E"))
                bg_grad.setColorAt(1.0, QColor("#0F1424"))
                border_color = QColor(self.palette["dot"])
            else:
                bg_grad.setColorAt(0.0, QColor("#111726"))
                bg_grad.setColorAt(1.0, QColor("#0B0F1A"))
                border_color = QColor(255, 255, 255, 14)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_grad))
        painter.drawRoundedRect(rect, 9, 9)

        if self._is_checked or self._is_hovered:
            dot_c = QColor(self.palette["dot"])
            glow_c = QColor(dot_c.red(), dot_c.green(), dot_c.blue(), 25)
            radial = QRadialGradient(QPointF(20, h * 0.5), 90)
            radial.setColorAt(0.0, glow_c)
            radial.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(radial))
            painter.drawRoundedRect(rect, 9, 9)

        painter.setPen(QPen(border_color, 1.2 if (self._is_checked or self._is_hovered) else 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 9, 9)
        painter.end()

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_checked = not self._is_checked
            self._update_state()
            self.update()
            self.toggled.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class PurgeCenterWidget(QWidget):
    """پنل یکپارچه مرکز پاکسازی با کپسول‌های آماری و سناریوهای مینی‌کارت لوکس"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.scope_cards: Dict[str, UltraStudioPurgeCard] = {}
        self.scenario_cards: Dict[str, ScenarioProfileCard] = {}
        self.init_ui()
        self.refresh_metrics()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # ۱. بنر نقطه بازگشت اضطراری (Zero-Risk Protection Slate)
        self.snapshot_banner = QFrame()
        self.snapshot_banner.setFixedHeight(68)
        self.snapshot_banner.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0B171A, stop:0.5 #0F1F24, stop:1 #0B171A);
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 9px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        snap_layout = QHBoxLayout(self.snapshot_banner)
        snap_layout.setContentsMargins(16, 0, 14, 0)
        snap_layout.setSpacing(12)
        snap_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_frame = QFrame()
        icon_frame.setFixedSize(36, 36)
        icon_frame.setStyleSheet("background-color: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 7px;")
        if_lay = QVBoxLayout(icon_frame)
        if_lay.setContentsMargins(0, 0, 0, 0)
        if_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        snap_icon = QLabel()
        snap_icon.setPixmap(IconProvider.get_pixmap("save", "#34D399", size=16))
        if_lay.addWidget(snap_icon)
        snap_layout.addWidget(icon_frame)

        snap_info = QVBoxLayout()
        snap_info.setSpacing(1)
        snap_info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_snap_title = QLabel("پوشش ایمنی و بازگشت خودکار (Safety Snapshot)")
        lbl_snap_title.setStyleSheet("font-size: 12px; font-weight: 800; color: #F8FAFC;")
        snap_info.addWidget(lbl_snap_title)

        self.lbl_snap_desc = QLabel("قبل از هر پاک‌سازی، بکاپ اضطراری دیتابیس ساخته می‌شود تا بدون استرس در هر لحظه بتوانید به آن بازگردید.")
        self.lbl_snap_desc.setStyleSheet("font-size: 10px; color: #94A3B8;")
        snap_info.addWidget(self.lbl_snap_desc)
        snap_layout.addLayout(snap_info, stretch=1)

        self.btn_rollback = QPushButton("بازگردانی آخرین وضعیت قبل از پاک‌سازی ↺")
        self.btn_rollback.setFixedHeight(32)
        self.btn_rollback.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rollback.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(16, 185, 129, 0.16);
                color: #34D399;
                border: 1px solid rgba(16, 185, 129, 0.45);
                border-radius: 6px;
                font-size: 10.5px;
                font-weight: 800;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #10B981;
                color: #FFFFFF;
                border-color: #10B981;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.03);
                color: #475569;
                border-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.btn_rollback.clicked.connect(self._handle_rollback)
        snap_layout.addWidget(self.btn_rollback)

        main_layout.addWidget(self.snapshot_banner)

        # ۲. بخش کاملاً بازطراحی‌شده سناریوهای مینی‌کارت لوکس
        scenarios_wrap = QFrame()
        scenarios_wrap.setStyleSheet("""
            QFrame#ScenariosWrapFrame {
                background-color: #101625;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }
        """)
        scenarios_wrap.setObjectName("ScenariosWrapFrame")
        scenarios_vlay = QVBoxLayout(scenarios_wrap)
        scenarios_vlay.setContentsMargins(12, 10, 12, 10)
        scenarios_vlay.setSpacing(8)

        sc_top_bar = QHBoxLayout()
        lbl_sc_title = QLabel("سناریوهای آماده پاک‌سازی استودیو:")
        lbl_sc_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #8F98A8; background: transparent; border: none;")
        sc_top_bar.addWidget(lbl_sc_title)
        sc_top_bar.addStretch()

        btn_reset_all = QPushButton("حالت انتخاب دستی / لغو سناریو")
        btn_reset_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset_all.setStyleSheet("background: transparent; color: #64748B; border: none; font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 700;")
        btn_reset_all.clicked.connect(self._deselect_all)
        sc_top_bar.addWidget(btn_reset_all)
        scenarios_vlay.addLayout(sc_top_bar)

        scenarios_grid = QHBoxLayout()
        scenarios_grid.setSpacing(8)

        # کارت سناریوی ۱: پاکسازی سبک و دوره‌ای
        self.sc_clean = ScenarioProfileCard(
            key="clean",
            title="پاک‌سازی سبک دوره‌ای",
            subtitle="حذف کش موقت، لاگ‌ها و تایمر بدون تغییر پروژه‌ها",
            tag="سبک و امن",
            accent_hex="#A855F7",
            icon_key="timer",
            parent=self
        )
        self.sc_clean.clicked.connect(self._preset_clean)
        scenarios_grid.addWidget(self.sc_clean)
        self.scenario_cards["clean"] = self.sc_clean

        # کارت سناریوی ۲: پایان فصل تدوین
        self.sc_season = ScenarioProfileCard(
            key="season",
            title="پایان فصل کاری",
            subtitle="پاک‌سازی پرونده‌های آرشیوشده و تسویه‌شده",
            tag="مختومه‌سازی",
            accent_hex="#F59E0B",
            icon_key="archive",
            parent=self
        )
        self.sc_season.clicked.connect(self._preset_season)
        scenarios_grid.addWidget(self.sc_season)
        self.scenario_cards["season"] = self.sc_season

        # کارت سناریوی ۳: بازنشانی کارخانه
        self.sc_factory = ScenarioProfileCard(
            key="factory",
            title="بازنشانی کامل کارخانه",
            subtitle="صفر کردن تمام پایگاه داده و برگرداندن تنظیمات",
            tag="ریست عمیق",
            accent_hex="#F43F5E",
            icon_key="trash",
            parent=self
        )
        self.sc_factory.clicked.connect(self._preset_factory)
        scenarios_grid.addWidget(self.sc_factory)
        self.scenario_cards["factory"] = self.sc_factory

        scenarios_vlay.addLayout(scenarios_grid)
        main_layout.addWidget(scenarios_wrap)

        # ۳. گرید کارت‌ها به صورت ۲ ستونه
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(8)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        self.scopes_data = [
            ("time_tracking", "سوابق جلسات و کش", "حذف رکوردهای تایم‌ترکینگ، فعالیت سیستم و کش موقت تصاویر", "timer", False),
            ("archived_projects", "پرونده‌های مختومه (آرشیو)", "حذف پروژه‌های آرشیو شده؛ پروژه‌های فعال حفظ می‌شوند", "archive", False),
            ("active_projects", "پروژه‌های فعال پایپ‌لاین", "پاک‌سازی پروژه‌های در حال تدوین، کلیپ‌ها و اصلاحیه‌ها", "projects", True),
            ("financial_ledger", "دفتر کل و تراکنش‌های مالی", "حذف واریزی‌ها و لاگ‌های مالی بدون حذف پروژه‌ها یا مخاطبین", "dollar", True),
            ("studios_directory", "دایرکتوری استودیوها", "حذف اطلاعات تماس آتلیه‌ها (پروژه‌ها بدون استودیو می‌مانند)", "target", False),
            ("branding_settings", "هویت برندینگ و قالب‌ها", "حذف لوگو، مهر/امضا و بازگردانی قالب‌های پیام‌رسانی", "settings", False),
            ("media_vault", "ایندکس آرشیو موزیک", "پاک‌سازی متادیتای دسته‌بندی‌ها بدون حذف فایل‌های هارد", "music", False)
        ]

        for idx, (key, title, desc, icon_key, danger) in enumerate(self.scopes_data):
            card = UltraStudioPurgeCard(key, title, desc, icon_key, "—", is_danger=danger, parent=self)
            card.toggled.connect(self._on_card_toggled)
            self.scope_cards[key] = card
            row = idx // 2
            col = idx % 2
            if idx == len(self.scopes_data) - 1 and col == 0:
                grid_layout.addWidget(card, row, 0, 1, 2)
            else:
                grid_layout.addWidget(card, row, col)

        main_layout.addWidget(grid_widget)

        # ۴. نوار وضعیت و دکمه اجرای نهایی
        action_plate = QFrame()
        action_plate.setFixedHeight(50)
        action_plate.setStyleSheet("""
            QFrame {
                background-color: #0E1322;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)
        action_layout = QHBoxLayout(action_plate)
        action_layout.setContentsMargins(14, 0, 14, 0)
        action_layout.setSpacing(12)
        action_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_selected_summary = QLabel("هیچ بخشی برای پاک‌سازی انتخاب نشده است.")
        self.lbl_selected_summary.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8; background: transparent; border: none;")
        action_layout.addWidget(self.lbl_selected_summary, stretch=1)

        self.btn_execute = QPushButton("اجرای پاک‌سازی بخش‌های انتخابی")
        self.btn_execute.setFixedHeight(34)
        self.btn_execute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_execute.setEnabled(False)
        self.btn_execute.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #1A2234;
                color: #475569;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 0 18px;
                font-size: 11.5px;
                font-weight: 800;
            }
            QPushButton:enabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #E11D48, stop:1 #BE123C);
                color: #FFFFFF;
                border: 1px solid #FB7185;
            }
            QPushButton:enabled:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F43F5E, stop:1 #E11D48);
            }
        """)
        self.btn_execute.clicked.connect(self._execute_purge)
        action_layout.addWidget(self.btn_execute)

        main_layout.addWidget(action_plate)

    def refresh_metrics(self):
        metrics = PurgeManager.get_live_metrics()

        if "time_tracking" in self.scope_cards:
            total_logs = metrics["time_tracking_sessions"] + metrics["activity_logs_count"]
            self.scope_cards["time_tracking"].set_badge(f"{to_persian_numbers(total_logs)} رکورد")

        if "archived_projects" in self.scope_cards:
            self.scope_cards["archived_projects"].set_badge(f"{to_persian_numbers(metrics['archived_projects_count'])} پرونده")

        if "active_projects" in self.scope_cards:
            self.scope_cards["active_projects"].set_badge(f"{to_persian_numbers(metrics['active_projects_count'])} پروژه")

        if "financial_ledger" in self.scope_cards:
            self.scope_cards["financial_ledger"].set_badge(f"{to_persian_numbers(metrics['transactions_count'])} تراکنش")

        if "studios_directory" in self.scope_cards:
            self.scope_cards["studios_directory"].set_badge(f"{to_persian_numbers(metrics['studios_count'])} استودیو")

        if "branding_settings" in self.scope_cards:
            self.scope_cards["branding_settings"].set_badge("سفارشی" if metrics["has_branding"] else "خام")

        if "media_vault" in self.scope_cards:
            self.scope_cards["media_vault"].set_badge(f"{to_persian_numbers(metrics['media_vault_refs_count'])} قطعه")

        snap_info = metrics.get("last_snapshot_date")
        if snap_info:
            self.lbl_snap_desc.setText(f"آخرین نقطه بازگشت اضطراری ذخیره‌شده: <b style='color:#34D399;'>{snap_info['display_time']}</b>")
            self.btn_rollback.setEnabled(True)
        else:
            self.lbl_snap_desc.setText("هنوز نقطه بازگشتی ایجاد نشده است (با اولین پاک‌سازی، بکاپ به‌صورت خودکار ساخته می‌شود).")
            self.btn_rollback.setEnabled(False)

        self._update_action_state()

    def _on_card_toggled(self):
        # بررسی تطابق با سناریوهای فعال
        self._sync_scenarios_state()
        self._update_action_state()

    def _sync_scenarios_state(self):
        checked_keys = set(k for k, card in self.scope_cards.items() if card.is_checked())
        
        self.sc_clean.set_active_state(checked_keys == {"time_tracking"})
        self.sc_season.set_active_state(checked_keys == {"time_tracking", "archived_projects"})
        self.sc_factory.set_active_state(len(checked_keys) == len(self.scope_cards) and len(checked_keys) > 0)

    def _update_action_state(self):
        chosen = [k for k, card in self.scope_cards.items() if card.is_checked()]
        count = len(chosen)
        self.btn_execute.setEnabled(count > 0)

        if count == 0:
            self.lbl_selected_summary.setText("هیچ بخشی برای پاک‌سازی انتخاب نشده است.")
        else:
            has_danger = any(self.scope_cards[k].is_danger for k in chosen)
            tag_color = "#FB7185" if has_danger else "#818CF8"
            self.lbl_selected_summary.setText(f"<b style='color:{tag_color};'>{to_persian_numbers(count)} بخش</b> از پایگاه داده و تنظیمات برای پاک‌سازی مشخص شد.")

    def _preset_clean(self):
        for k, card in self.scope_cards.items():
            card.set_checked(k == "time_tracking")
        self._sync_scenarios_state()
        self._update_action_state()

    def _preset_season(self):
        for k, card in self.scope_cards.items():
            card.set_checked(k in ["time_tracking", "archived_projects"])
        self._sync_scenarios_state()
        self._update_action_state()

    def _preset_factory(self):
        for card in self.scope_cards.values():
            card.set_checked(True)
        self._sync_scenarios_state()
        self._update_action_state()

    def _deselect_all(self):
        for card in self.scope_cards.values():
            card.set_checked(False)
        self._sync_scenarios_state()
        self._update_action_state()

    def _execute_purge(self):
        chosen = [k for k, card in self.scope_cards.items() if card.is_checked()]
        if not chosen:
            return

        has_danger = any(self.scope_cards[k].is_danger for k in chosen)

        confirm_msg = f"آیا از پاک‌سازی {to_persian_numbers(len(chosen))} بخش انتخاب‌شده اطمینان دارید؟"
        details_msg = "یک نسخه پشتیبان خودکار (Safety Snapshot) به صورت کامل ذخیره می‌شود و در صورت تمایل می‌توانید بلافاصله به آن بازگردید."

        if StudioConfirmDialog.ask(
            self.window(),
            title="تأیید پاک‌سازی داده‌ها",
            message=confirm_msg,
            details=details_msg,
            confirm_text="اجرای پاک‌سازی",
            is_danger=has_danger,
            icon_name="alert" if has_danger else "trash"
        ):
            success = PurgeManager.execute_granular_purge(chosen)
            if success:
                global_signals.show_toast.emit("پاک‌سازی بخش‌های انتخابی با موفقیت انجام شد.", "success")
                self._deselect_all()
                self.refresh_metrics()
            else:
                StudioConfirmDialog.ask(
                    self.window(),
                    title="خطا",
                    message="خطایی در اجرای عملیات پاک‌سازی رخ داد.",
                    is_danger=True,
                    icon_name="alert"
                )

    def _handle_rollback(self):
        if StudioConfirmDialog.ask(
            self.window(),
            title="بازگردانی به آخرین اسنپ‌شات",
            message="آیا مایلید تمام داده‌ها و تنظیمات به قبل از آخرین پاک‌سازی بازگردند؟",
            details="تمامی اطلاعات موجود در فایل اسنپ‌شات مجدداً روی دیتابیس فعلی اعمال خواهند شد.",
            confirm_text="بازگردانی اضطراری",
            is_danger=False,
            icon_name="revision"
        ):
            if PurgeManager.restore_last_snapshot():
                global_signals.show_toast.emit("داده‌ها با موفقیت از آخرین اسنپ‌شات بازگردانی شدند.", "success")
                self.refresh_metrics()
            else:
                StudioConfirmDialog.ask(
                    self.window(),
                    title="خطا",
                    message="خطا در بازیابی اسنپ‌شات اضطراری.",
                    is_danger=True,
                    icon_name="alert"
                )