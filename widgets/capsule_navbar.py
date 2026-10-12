# ==================================================
# FILE: widgets/capsule_navbar.py
# ==================================================
from typing import List, Optional
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QPushButton, QSizePolicy, QWidget
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, QTimer, QSize, QRectF
)
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QPen, QBrush
)

from core.icon_provider import IconProvider


@dataclass
class DeckNavItem:
    title: str
    icon_name: str
    page_index: int
    group: int = 1


class MatteDeckTabButton(QPushButton):
    """دکمه شیشه‌ای کپسول با آیکون‌های وکتور رسمی و بدون لرزش"""
    def __init__(self, item: DeckNavItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.is_active = False
        self.mode = "full"

        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedHeight(32)
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
        else:
            self.setText(f"  {self.item.title}")
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)

        self._update_style()

    def _update_style(self):
        icon_color = "#818CF8" if self.is_active else "#64748B"
        icon = IconProvider.get_icon(self.item.icon_name, icon_color, size=15)
        self.setIcon(icon)
        self.setIconSize(QSize(15, 15))

        pad_x = 0 if self.mode == "icon_only" else (8 if self.mode == "compact" else 12)
        font_sz = 11 if self.mode == "compact" else 11.5

        if self.is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    font-family: 'Vazirmatn';
                    font-size: {font_sz}px;
                    font-weight: 700;
                    color: #F8FAFC;
                    background-color: transparent;
                    border: none;
                    border-radius: 16px;
                    padding: 0 {pad_x}px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    font-family: 'Vazirmatn';
                    font-size: {font_sz}px;
                    font-weight: 700;
                    color: #8F909D;
                    background-color: transparent;
                    border: none;
                    border-radius: 16px;
                    padding: 0 {pad_x}px;
                }}
                QPushButton:hover {{
                    color: #F8FAFC;
                }}
            """)


class CapsuleNavBar(QFrame):
    page_selected = Signal(int)

    ITEMS = [
        DeckNavItem("پیشخوان", "dashboard", 0, group=1),
        DeckNavItem("پروژه‌ها", "projects", 1, group=1),
        DeckNavItem("آرشیو", "archive", 2, group=1),
        DeckNavItem("موزیک", "music", 4, group=1),
        DeckNavItem("دستیار هوشمند", "sparkles", 7, group=2),
        DeckNavItem("زمان و راندمان", "timer", 6, group=2),
        DeckNavItem("مالی", "dollar", 3, group=2),
        DeckNavItem("تنظیمات", "settings", 5, group=2),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_index = 0
        self.buttons: List[MatteDeckTabButton] = []
        self.dividers: List[QWidget] = []

        self.setObjectName("EditorialGlassDeck")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        # پیل کپسولی با استایل گرادیان درخشان و ظریف
        self.active_pill = QFrame(self)
        self.active_pill.setFixedHeight(30)
        self.active_pill.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(99, 102, 241, 0.28), stop:1 rgba(56, 189, 248, 0.16));
                border: 1px solid rgba(129, 140, 248, 0.40);
                border-radius: 15px;
            }
        """)
        self.active_pill.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # ترانزیشن مغناطیسی فنری (Magnetic Elastic Spring)
        self.anim = QPropertyAnimation(self.active_pill, b"geometry")
        self.anim.setDuration(260)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)

        self.init_ui()

    def paintEvent(self, event):
        """رسم بدنه شیار فرورفته متالیک (Frosted Inset Track)"""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            w = float(self.width())
            h = float(self.height())
            rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

            # شیار تراش‌خورده تیتانیومی
            bg_grad = QLinearGradient(0, 0, 0, h)
            bg_grad.setColorAt(0.0, QColor("#080B12"))
            bg_grad.setColorAt(0.5, QColor("#0A0E17"))
            bg_grad.setColorAt(1.0, QColor("#0D1322"))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_grad))
            painter.drawRoundedRect(rect, 20, 20)

            # هایلایت شیار بیرونی با کنتراست ظریف
            border_pen = QPen(QColor(99, 102, 241, 45), 1.0)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 20, 20)

            # خط هایلایت میکرونی لبه بالایی برای حس عمق (Inner Inset Shadow)
            top_inset_rect = QRectF(12.0, 1.2, w - 24.0, 1.0)
            painter.setPen(QPen(QColor(255, 255, 255, 12), 1.0))
            painter.drawLine(int(top_inset_rect.left()), int(top_inset_rect.top()),
                             int(top_inset_rect.right()), int(top_inset_rect.top()))
        finally:
            painter.end()

    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 4, 5, 4)
        self.main_layout.setSpacing(2)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        current_grp = 1
        for item in self.ITEMS:
            if item.group != current_grp:
                current_grp = item.group
                # نقطه نورانی تفکیک گروه ابزارها
                dot_sep = QWidget()
                dot_sep.setFixedSize(12, 32)
                sep_lay = QHBoxLayout(dot_sep)
                sep_lay.setContentsMargins(0, 0, 0, 0)
                sep_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

                dot = QFrame()
                dot.setFixedSize(3, 3)
                dot.setStyleSheet("background-color: rgba(255, 255, 255, 0.18); border-radius: 1.5px;")
                sep_lay.addWidget(dot)

                self.main_layout.addWidget(dot_sep)
                self.dividers.append(dot_sep)

            btn = MatteDeckTabButton(item, self)
            btn.clicked.connect(lambda _, idx=item.page_index: self.select_index(idx, emit_signal=True))
            self.main_layout.addWidget(btn)
            self.buttons.append(btn)

        self.active_pill.lower()
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
            self._reposition_pill(target_btn, animate=animate)

        if emit_signal:
            self.page_selected.emit(index)

    def _reposition_pill(self, btn: QPushButton, animate: bool = True):
        geo = btn.geometry()
        if geo.width() <= 0:
            return

        target_rect = QRect(geo.x(), 5, geo.width(), 30)
        self.active_pill.raise_()
        btn.raise_()

        if animate:
            self.anim.stop()
            self.anim.setStartValue(self.active_pill.geometry())
            self.anim.setEndValue(target_rect)
            self.anim.start()
        else:
            self.active_pill.setGeometry(target_rect)

    def update_responsive_layout(self, window_width: int):
        if window_width < 1040:
            mode = "icon_only"
            spacing = 2
            margins = (4, 4, 4, 4)
        elif window_width < 1280:
            mode = "compact"
            spacing = 2
            margins = (5, 4, 5, 4)
        else:
            mode = "full"
            spacing = 3
            margins = (6, 4, 6, 4)

        for btn in self.buttons:
            btn.set_responsive_mode(mode)

        self.main_layout.setSpacing(spacing)
        self.main_layout.setContentsMargins(*margins)

        self.adjustSize()
        self.updateGeometry()

        QTimer.singleShot(25, lambda: self.select_index(self.current_index, emit_signal=False, animate=False))

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(35, lambda: self.select_index(self.current_index, emit_signal=False, animate=False))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(25, lambda: self.select_index(self.current_index, emit_signal=False, animate=False))