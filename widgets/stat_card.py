# ==================================================
# FILE: widgets/stat_card.py
# ==================================================
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from core.persian_utils import format_toman, to_persian_numbers


class StatCard(QFrame):
    """
    کارت آماری مینیمال، مات و هماهنگ با دیزاین سیستم نرم‌افزار
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
        self.setObjectName("SurfaceStatCard")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.title = title
        self.current_value = initial_value
        self.is_currency = is_currency
        self.color_accent = color_accent

        self.setFixedHeight(88)
        self.setMinimumWidth(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)

        self.init_ui()
        self._apply_style()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # عنوان کارت
        self.lbl_title = QLabel(self.title)
        self.lbl_title.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 11.5px;
                font-weight: 500;
                color: #8F909D;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.lbl_title)

        # مقدار اصلی
        self.lbl_value = QLabel()
        self.lbl_value.setStyleSheet(f"""
            QLabel {{
                font-family: 'Vazirmatn';
                font-size: 18px;
                font-weight: 800;
                color: {self.color_accent};
                background: transparent;
                border: none;
            }}
        """)
        self._render_value(self.current_value)
        layout.addWidget(self.lbl_value)

    def _apply_style(self):
        self.setStyleSheet("""
            QFrame#SurfaceStatCard {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QFrame#SurfaceStatCard:hover {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
        """)

    def _render_value(self, val: int):
        if self.is_currency:
            self.lbl_value.setText(format_toman(val))
        else:
            self.lbl_value.setText(to_persian_numbers(val))

    def animate_to_value(self, target_value: int):
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(350)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(self.current_value)
        self.anim.setEndValue(target_value)
        self.anim.valueChanged.connect(lambda v: self._render_value(int(v)))
        self.anim.start()
        self.current_value = target_value