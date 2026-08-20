# ==================================================
# FILE: C:\Users\Milad\OneDrive\Desktop\CutterLog\widgets\custom_inputs.py
# ==================================================
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from core.persian_utils import to_persian_numbers


class ModernNumberStepper(QWidget):
    """کنترلر عددی مدرن با دکمه‌های تفکیک‌شده مثبت و منفی و نمایش واضح عدد"""
    valueChanged = Signal(int)

    def __init__(self, min_val: int = 0, max_val: int = 100, initial_val: int = 0, unit: str = "روز", zero_text: str = None, parent=None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.current_val = initial_val
        self.unit = unit
        self.zero_text = zero_text
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # دکمه افزایش (+)
        self.btn_plus = QPushButton("+")
        self.btn_plus.setFixedSize(36, 36)
        self.btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_plus.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #242E42;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #6366F1;
                border-color: #6366F1;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #4F46E5;
            }
        """)
        self.btn_plus.clicked.connect(self._increment)
        layout.addWidget(self.btn_plus)

        # کادر نمایش عدد
        self.lbl_display = QLabel()
        self.lbl_display.setFixedHeight(36)
        self.lbl_display.setMinimumWidth(110)
        self.lbl_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_display.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 10px;
            }
        """)
        layout.addWidget(self.lbl_display)

        # دکمه کاهش (−)
        self.btn_minus = QPushButton("−")
        self.btn_minus.setFixedSize(36, 36)
        self.btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minus.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #242E42;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                font-size: 16px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #242E42;
                border-color: #EF4444;
                color: #EF4444;
            }
            QPushButton:pressed {
                background-color: #1A2234;
            }
        """)
        self.btn_minus.clicked.connect(self._decrement)
        layout.addWidget(self.btn_minus)

        self._update_display()

    def _update_display(self):
        if self.current_val == 0 and self.zero_text:
            self.lbl_display.setText(self.zero_text)
            self.lbl_display.setStyleSheet("""
                QLabel {
                    font-family: 'Vazirmatn';
                    background-color: #161F30;
                    color: #94A3B8;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 0 10px;
                }
            """)
        else:
            self.lbl_display.setText(f"{to_persian_numbers(self.current_val)} {self.unit}")
            self.lbl_display.setStyleSheet("""
                QLabel {
                    font-family: 'Vazirmatn';
                    background-color: #161F30;
                    color: #F8FAFC;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 700;
                    padding: 0 10px;
                }
            """)

    def _increment(self):
        if self.current_val < self.max_val:
            self.current_val += 1
            self._update_display()
            self.valueChanged.emit(self.current_val)

    def _decrement(self):
        if self.current_val > self.min_val:
            self.current_val -= 1
            self._update_display()
            self.valueChanged.emit(self.current_val)

    def value(self) -> int:
        return self.current_val

    def setValue(self, val: int):
        self.current_val = max(self.min_val, min(self.max_val, val))
        self._update_display()