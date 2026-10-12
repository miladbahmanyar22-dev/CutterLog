# ==================================================
# FILE: widgets/stat_card.py
# ==================================================
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QBrush, QPen

from core.persian_utils import format_toman, to_persian_numbers


class StatCard(QFrame):
    """
    کارت آماری بازطراحی‌شده با طراحی مدرن استودیویی،
    هاله نوری ملایم، نشانگر خطی موضوعی و انیمیشن ارقام
    """
    def __init__(
        self, 
        title: str, 
        initial_value: int = 0, 
        is_currency: bool = False, 
        color_accent: str = "#818CF8", 
        parent=None
    ):
        super().__init__(parent)
        self.setObjectName("ModernStatCard")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.title = title
        self.current_value = initial_value
        self.is_currency = is_currency
        self.color_accent = QColor(color_accent)
        self._is_hovered = False

        self.setFixedHeight(94)
        self.setMinimumWidth(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)

        self.init_ui()
        self._render_value(self.current_value)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # ردیف بالا: عنوان و میکرو-نشانگر رنگی
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_title = QLabel(self.title)
        self.lbl_title.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 11px;
                font-weight: 600;
                color: #8F909D;
                background: transparent;
                border: none;
            }
        """)
        top_row.addWidget(self.lbl_title)
        top_row.addStretch()

        # نشانگر نوری کوچک گوشه کارت
        self.micro_dot = QLabel("●")
        self.micro_dot.setStyleSheet(f"""
            QLabel {{
                font-size: 8px;
                color: {self.color_accent.name()};
                background: transparent;
                border: none;
            }}
        """)
        top_row.addWidget(self.micro_dot)
        layout.addLayout(top_row)

        # ردیف مقدار عددی و واحد
        val_row = QHBoxLayout()
        val_row.setContentsMargins(0, 0, 0, 0)
        val_row.setSpacing(6)
        val_row.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)

        self.lbl_value = QLabel()
        self.lbl_value.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 19px;
                font-weight: 800;
                color: #F8FAFC;
                background: transparent;
                border: none;
            }
        """)
        val_row.addWidget(self.lbl_value)

        self.lbl_unit = QLabel("تومان" if self.is_currency else "مورد")
        self.lbl_unit.setStyleSheet(f"""
            QLabel {{
                font-family: 'Vazirmatn';
                font-size: 10.5px;
                font-weight: 700;
                color: {self.color_accent.name()};
                background: transparent;
                border: none;
                padding-top: 4px;
            }}
        """)
        val_row.addWidget(self.lbl_unit)
        val_row.addStretch()

        layout.addLayout(val_row)

    def _render_value(self, val: int):
        val_int = int(val)
        if self.is_currency:
            formatted = f"{val_int:,}"
            self.lbl_value.setText(to_persian_numbers(formatted))
        else:
            self.lbl_value.setText(to_persian_numbers(val_int))

    def animate_to_value(self, target_value: int):
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(self.current_value)
        self.anim.setEndValue(target_value)
        self.anim.valueChanged.connect(lambda v: self._render_value(int(v)))
        self.anim.start()
        self.current_value = target_value

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

        # پس‌زمینه گرادیانتی تیره
        grad = QLinearGradient(0, 0, 0, h)
        if self._is_hovered:
            grad.setColorAt(0.0, QColor("#161F30"))
            grad.setColorAt(1.0, QColor("#111726"))
        else:
            grad.setColorAt(0.0, QColor("#121826"))
            grad.setColorAt(1.0, QColor("#0D121D"))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(rect, 10, 10)

        # هاله نوری ملایم در گوشه بالایی
        radial = QRadialGradient(QPointF(w * 0.85, 0.0), w * 0.65)
        accent = self.color_accent
        alpha = 32 if self._is_hovered else 16
        radial.setColorAt(0.0, QColor(accent.red(), accent.green(), accent.blue(), alpha))
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(radial))
        painter.drawRoundedRect(rect, 10, 10)

        # نوار باریک رنگی در لبه پایینی برای ریتم بصری
        line_rect = QRectF(14.0, h - 2.5, w - 28.0, 1.5)
        line_color = QColor(accent.red(), accent.green(), accent.blue(), 180 if self._is_hovered else 80)
        painter.setBrush(QBrush(line_color))
        painter.drawRoundedRect(line_rect, 1, 1)

        # بردر کادر
        border_alpha = 110 if self._is_hovered else 25
        border_color = QColor(accent.red(), accent.green(), accent.blue(), border_alpha) if self._is_hovered else QColor(255, 255, 255, 16)
        painter.setPen(QPen(border_color, 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 10, 10)

        painter.end()