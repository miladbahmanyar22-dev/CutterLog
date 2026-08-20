# ==================================================
# FILE: widgets/capsule_navbar.py
# ==================================================
from typing import List, Optional
from dataclasses import dataclass
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame, QSizePolicy
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, QTimer, QSize

from core.icon_provider import IconProvider


@dataclass
class DeckNavItem:
    title: str
    icon_name: str
    page_index: int
    group: int = 1


class MatteDeckTabButton(QPushButton):
    """تب کنسولی واکنش‌گرا با پشتیبانی از ۳ مود: فول، فشرده و مینی‌مال (فقط آیکون)"""
    def __init__(self, item: DeckNavItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.is_active = False
        self.mode = "full"  # "full", "compact", "icon_only"

        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(34)
        self.setToolTip(item.title)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._update_display()

    def set_active_state(self, active: bool):
        self.is_active = active
        self.setChecked(active)
        self._update_style()

    def set_responsive_mode(self, mode: str):
        if self.mode != mode:
            self.mode = mode
            self._update_display()

    def _update_display(self):
        if self.mode == "icon_only":
            self.setText("")
            self.setFixedWidth(36)
        elif self.mode == "compact":
            self.setText(f" {self.item.title}")
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
        else:  # full
            self.setText(f"  {self.item.title}")
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)

        self._update_style()

    def _update_style(self):
        icon_color = "#818CF8" if self.is_active else "#64748B"
        self.setIcon(IconProvider.get_icon(self.item.icon_name, icon_color, size=15))
        self.setIconSize(QSize(15, 15))

        pad_x = 0 if self.mode == "icon_only" else (7 if self.mode == "compact" else 12)
        font_sz = 11.5 if self.mode == "compact" else 12

        if self.is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    font-family: 'Vazirmatn';
                    font-size: {font_sz}px;
                    font-weight: 800;
                    color: #F8FAFC;
                    background-color: #161F30;
                    border: none;
                    border-radius: 6px;
                    padding: 0 {pad_x}px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    font-family: 'Vazirmatn';
                    font-size: {font_sz}px;
                    font-weight: 500;
                    color: #8F909D;
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 0 {pad_x}px;
                }}
                QPushButton:hover {{
                    color: #F8FAFC;
                    background-color: rgba(255, 255, 255, 0.04);
                }}
            """)


class CapsuleNavBar(QFrame):
    page_selected = Signal(int)

    # فهرست کامل تب‌های نوار ناوبری بالا
    ITEMS = [
        DeckNavItem("پیشخوان", "dashboard", 0, group=1),
        DeckNavItem("پروژه‌ها", "projects", 1, group=1),
        DeckNavItem("آرشیو", "archive", 2, group=1),
        DeckNavItem("موزیک", "music", 4, group=1),
        DeckNavItem("دستیار هوشمند", "sparkles", 7, group=2),
        DeckNavItem("زمان و راندمان", "play", 6, group=2),
        DeckNavItem("مالی", "dollar", 3, group=2),
        DeckNavItem("تنظیمات", "settings", 5, group=2),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_index = 0
        self.buttons: List[MatteDeckTabButton] = []
        self.dividers: List[QFrame] = []

        self.setObjectName("MatteDeckContainer")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QFrame#MatteDeckContainer {
                background-color: #0B0F17;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)

        # خط شاخص متحرک نوری
        self.indicator_line = QFrame(self)
        self.indicator_line.setFixedHeight(2)
        self.indicator_line.setStyleSheet("background-color: #6366F1; border-radius: 1px;")
        self.indicator_line.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.anim = QPropertyAnimation(self.indicator_line, b"geometry")
        self.anim.setDuration(160)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.init_ui()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(4, 3, 4, 3)
        self.main_layout.setSpacing(3)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        current_grp = 1
        for item in self.ITEMS:
            if item.group != current_grp:
                current_grp = item.group
                div = QFrame()
                div.setFrameShape(QFrame.Shape.VLine)
                div.setFixedHeight(18)
                div.setStyleSheet("background-color: rgba(255, 255, 255, 0.06); border: none;")
                self.main_layout.addWidget(div)
                self.dividers.append(div)

            btn = MatteDeckTabButton(item, self)
            btn.clicked.connect(lambda _, idx=item.page_index: self.select_index(idx, emit_signal=True))
            self.main_layout.addWidget(btn)
            self.buttons.append(btn)

        self.select_index(0, emit_signal=False, animate=False)

    def select_index(self, index: int, emit_signal: bool = True, animate: bool = True):
        self.current_index = index
        target_btn: Optional[MatteDeckTabButton] = None

        for btn in self.buttons:
            is_active = (btn.item.page_index == index)
            btn.set_active_state(is_active)
            if is_active:
                target_btn = btn

        if target_btn:
            self._reposition_indicator(target_btn, animate=animate)

        if emit_signal:
            self.page_selected.emit(index)

    def _reposition_indicator(self, btn: QPushButton, animate: bool = True):
        geo = btn.geometry()
        if geo.width() <= 0:
            return

        w = max(16, int(geo.width() * 0.65))
        x = geo.x() + int((geo.width() - w) / 2)
        y = self.height() - 3
        target_rect = QRect(x, y, w, 2)

        if animate:
            self.anim.stop()
            self.anim.setStartValue(self.indicator_line.geometry())
            self.anim.setEndValue(target_rect)
            self.anim.start()
        else:
            self.indicator_line.setGeometry(target_rect)

    def update_responsive_layout(self, window_width: int):
        if window_width < 1020:
            mode = "icon_only"
            spacing = 2
            margins = (3, 3, 3, 3)
        elif window_width < 1280:
            mode = "compact"
            spacing = 3
            margins = (4, 3, 4, 3)
        else:
            mode = "full"
            spacing = 4
            margins = (6, 3, 6, 3)

        for btn in self.buttons:
            btn.set_responsive_mode(mode)

        self.main_layout.setSpacing(spacing)
        self.main_layout.setContentsMargins(*margins)

        self.adjustSize()
        self.updateGeometry()

        QTimer.singleShot(20, lambda: self.select_index(self.current_index, emit_signal=False, animate=False))

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(40, lambda: self.select_index(self.current_index, emit_signal=False, animate=False))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(20, lambda: self.select_index(self.current_index, emit_signal=False, animate=False))