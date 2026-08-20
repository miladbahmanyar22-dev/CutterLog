# ==================================================
# FILE: widgets/base_card.py
# ==================================================
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QStyleOption, QStyle
)
from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QMouseEvent


class BaseProjectCard(QFrame):
    clicked = Signal(int)

    def __init__(
        self,
        project_id: int,
        project_number: int,
        parent=None,
        accent_color: str = "#6366F1",
        card_type: str = "project"
    ):
        super().__init__(parent)
        self.project_id = project_id
        self.project_number = project_number
        self.accent_color = accent_color
        self.card_type = card_type
        
        self.formatted_number = f"{self.project_number:03d}" if self.project_number < 1000 else str(self.project_number)
        self.is_hovered = False
        
        if self.card_type == "dashboard":
            self.base_wm_opacity = 0.040
            self.hover_wm_opacity = 0.080
            self.card_fixed_height = 145
        elif self.card_type == "archive":
            self.base_wm_opacity = 0.035
            self.hover_wm_opacity = 0.070
            self.card_fixed_height = 188
        else:
            self.base_wm_opacity = 0.040
            self.hover_wm_opacity = 0.080
            self.card_fixed_height = 230

        self.current_wm_opacity = self.base_wm_opacity

        self.setObjectName("BaseCardFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFixedHeight(self.card_fixed_height)

        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(18, 14, 18, 14)
        self.card_layout.setSpacing(8)

        self._setup_base_ui()
        self._apply_base_styles()

    def sizeHint(self) -> QSize:
        return QSize(360, self.card_fixed_height)

    def minimumSizeHint(self) -> QSize:
        return QSize(280, self.card_fixed_height)

    def _setup_base_ui(self):
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(8)

        self.lbl_number_badge = QLabel(self.formatted_number)
        self.lbl_number_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_number_badge.setFixedHeight(24)
        self.lbl_number_badge.setMinimumWidth(38)
        self.lbl_number_badge.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI', 'Vazirmatn', sans-serif;
                font-size: 11px;
                font-weight: 800;
                color: #A5B4FC;
                background-color: rgba(99, 102, 241, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 6px;
                padding: 0 6px;
                letter-spacing: 0.5px;
            }
        """)
        self.header_layout.addWidget(self.lbl_number_badge)

        self.header_tags_layout = QHBoxLayout()
        self.header_tags_layout.setContentsMargins(0, 0, 0, 0)
        self.header_tags_layout.setSpacing(6)
        self.header_layout.addLayout(self.header_tags_layout, stretch=1)

        self.card_layout.addLayout(self.header_layout)

    def _apply_base_styles(self):
        self.setStyleSheet("""
            QFrame#BaseCardFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
            }
            QFrame#BaseCardFrame:hover {
                background-color: #161F30;
                border: 1px solid rgba(99, 102, 241, 0.40);
            }
        """)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        wm_color = QColor(self.accent_color)
        wm_color.setAlphaF(self.current_wm_opacity)
        painter.setPen(wm_color)

        target_height = float(self.height())
        font = QFont("Segoe UI", 10, QFont.Weight.Black)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

        fm = QFontMetrics(font)
        if fm.capHeight() > 0:
            scale_factor = (target_height * 0.96) / fm.capHeight()
            font.setPointSizeF(10.0 * scale_factor)

        painter.setFont(font)

        full_fit_rect = QRectF(2.0, 0.0, float(self.width() * 0.70), target_height)
        painter.drawText(
            full_fit_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.formatted_number
        )
        painter.end()

    def enterEvent(self, event):
        self.is_hovered = True
        self.current_wm_opacity = self.hover_wm_opacity
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.current_wm_opacity = self.base_wm_opacity
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # کلیک فقط در صورتی اعمال می‌شود که روی المان‌های تعاملی داخلی نباشد
            child = self.childAt(event.pos())
            if child in (self, self.lbl_number_badge) or isinstance(child, QLabel):
                event.accept()
                self.clicked.emit(self.project_id)
                return
        super().mouseReleaseEvent(event)