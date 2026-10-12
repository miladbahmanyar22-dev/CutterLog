# ==================================================
# FILE: widgets/base_card.py
# ==================================================
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QStyleOption, QStyle
)
from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QMouseEvent


class BaseProjectCard(QFrame):
    clicked = Signal(int)

    def __init__(
        self,
        project_id: int,
        project_number: int,
        parent=None,
        accent_color: str = "#818CF8",
        card_type: str = "project"
    ):
        super().__init__(parent)
        self.project_id = project_id
        self.project_number = project_number
        self.accent_color = QColor(accent_color)
        self.card_type = card_type
        
        self.formatted_number = f"#{self.project_number:03d}" if self.project_number < 1000 else f"#{self.project_number}"
        self.is_hovered = False

        if self.card_type == "dashboard":
            self.card_fixed_height = 148
        elif self.card_type == "archive":
            self.card_fixed_height = 188
        else:
            self.card_fixed_height = 236

        self.setObjectName("BaseCardFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFixedHeight(self.card_fixed_height)

        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(16, 12, 16, 12)
        self.card_layout.setSpacing(6)

        self._setup_base_header()
        self._apply_base_theme()

    def sizeHint(self) -> QSize:
        return QSize(360, self.card_fixed_height)

    def minimumSizeHint(self) -> QSize:
        return QSize(280, self.card_fixed_height)

    def _setup_base_header(self):
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(0, 0, 0, 0)
        self.header_layout.setSpacing(8)
        self.header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # نشانگر شماره اختصاصی پروژه
        self.lbl_number_badge = QLabel(self.formatted_number)
        self.lbl_number_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_number_badge.setFixedHeight(24)
        self.lbl_number_badge.setMinimumWidth(44)
        self.lbl_number_badge.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI', 'Vazirmatn', sans-serif;
                font-size: 11px;
                font-weight: 900;
                color: #A5B4FC;
                background-color: rgba(99, 102, 241, 0.15);
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 6px;
                padding: 0 6px;
            }
        """)
        self.header_layout.addWidget(self.lbl_number_badge)

        self.header_tags_layout = QHBoxLayout()
        self.header_tags_layout.setContentsMargins(0, 0, 0, 0)
        self.header_tags_layout.setSpacing(6)
        self.header_layout.addLayout(self.header_tags_layout, stretch=1)

        self.card_layout.addLayout(self.header_layout)

    def _apply_base_theme(self):
        self.setStyleSheet("""
            QFrame#BaseCardFrame {
                background-color: #0E1322;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
            }
            QFrame#BaseCardFrame:hover {
                background-color: #12182B;
                border: 1px solid rgba(99, 102, 241, 0.45);
            }
        """)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        painter.end()

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.pos())
            if child in (self, self.lbl_number_badge) or isinstance(child, QLabel):
                event.accept()
                self.clicked.emit(self.project_id)
                return
        super().mouseReleaseEvent(event)