# ==================================================
# FILE: time_tracking/widgets/daily_goal_dialog.py
# ==================================================
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from widgets.studio_dialog_base import StudioBaseDialog
from core.persian_utils import to_persian_numbers


class StudioStepperWidget(QFrame):
    """ویجت کنترل عددی مدرن کپسولی با دکمه‌های مجزا و بزرگ + و -"""
    valueChanged = Signal(int)

    def __init__(self, value: int = 8, min_val: int = 1, max_val: int = 24, step: int = 1, unit_label: str = "ساعت", parent=None):
        super().__init__(parent)
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.unit_label = unit_label

        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            StudioStepperWidget {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            StudioStepperWidget:hover {
                border-color: rgba(99, 102, 241, 0.4);
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        # دکمه افزایش (+)
        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(34, 34)
        btn_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_plus.setStyleSheet("""
            QPushButton {
                font-family: 'Segoe UI', monospace;
                background-color: #1F2A40;
                color: #818CF8;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #6366F1;
                color: #FFFFFF;
                border-color: #818CF8;
            }
        """)
        btn_plus.clicked.connect(self._increase)
        layout.addWidget(btn_plus)

        # نمایشگر عدد و واحد در مرکز
        self.lbl_display = QLabel()
        self.lbl_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_display.setStyleSheet("background: transparent; border: none;")
        self._update_label()
        layout.addWidget(self.lbl_display, stretch=1)

        # دکمه کاهش (-)
        btn_minus = QPushButton("-")
        btn_minus.setFixedSize(34, 34)
        btn_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_minus.setStyleSheet("""
            QPushButton {
                font-family: 'Segoe UI', monospace;
                background-color: #1F2A40;
                color: #818CF8;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #EF4444;
                color: #FFFFFF;
                border-color: #F87171;
            }
        """)
        btn_minus.clicked.connect(self._decrease)
        layout.addWidget(btn_minus)

    def _update_label(self):
        val_str = f"{self.value:02d}"
        self.lbl_display.setText(f"<b style='font-family:Segoe UI, Vazirmatn; font-size:16px; color:#F8FAFC;'>{to_persian_numbers(val_str)}</b> <span style='font-family:Vazirmatn; font-size:11.5px; color:#94A3B8;'>{self.unit_label}</span>")

    def _increase(self):
        if self.value + self.step <= self.max_val:
            self.value += self.step
            self._update_label()
            self.valueChanged.emit(self.value)

    def _decrease(self):
        if self.value - self.step >= self.min_val:
            self.value -= self.step
            self._update_label()
            self.valueChanged.emit(self.value)

    def set_value(self, new_val: int):
        self.value = max(self.min_val, min(self.max_val, new_val))
        self._update_label()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self._increase()
        else:
            self._decrease()
        event.accept()


class DailyGoalSettingDialog(StudioBaseDialog):
    """دیالوگ مدرن تنظیم هدف کاری روزانه با کنترلرهای بازطراحی‌شده"""
    def __init__(self, current_minutes: int = 480, parent=None):
        super().__init__(parent=parent)
        self.target_minutes = current_minutes
        self.setFixedWidth(440)
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "تنظیم هدف کاری امروز",
            "مدت‌زمان هدف تدوین روزانه خود را تعیین کنید",
            icon_name="settings",
            icon_color="#6366F1"
        )

        cur_hours = max(1, self.target_minutes // 60)
        cur_mins = self.target_minutes % 60

        # ۱. دکمه‌های انتخاب سریع (Presets)
        lbl_p = QLabel("انتخاب سریع:")
        lbl_p.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #8F909D; font-weight: 600;")
        self.container_layout.addWidget(lbl_p)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)

        presets = [
            ("۴ ساعت", 240),
            ("۶ ساعت", 360),
            ("۸ ساعت", 480),
            ("۱۰ ساعت", 600)
        ]

        for label, mins in presets:
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: #161F30;
                    color: #94A3B8;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                    font-size: 11.5px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #1E283D;
                    color: #F8FAFC;
                    border-color: #6366F1;
                }
            """)
            btn.clicked.connect(lambda _, m=mins: self._set_preset(m))
            preset_row.addWidget(btn)

        self.container_layout.addLayout(preset_row)

        # ۲. کنترلرهای بازطراحی‌شده ساعت و دقیقه در کنار هم
        lbl_adj = QLabel("تنظیم دقیق زمان هدف:")
        lbl_adj.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #8F909D; font-weight: 600; margin-top: 4px;")
        self.container_layout.addWidget(lbl_adj)

        steppers_row = QHBoxLayout()
        steppers_row.setSpacing(10)

        # استپر ساعت
        self.hour_stepper = StudioStepperWidget(
            value=cur_hours, 
            min_val=1, 
            max_val=24, 
            step=1, 
            unit_label="ساعت",
            parent=self
        )
        steppers_row.addWidget(self.hour_stepper, stretch=1)

        # استپر دقیقه (گام‌های ۱۵ دقیقه‌ای)
        self.min_stepper = StudioStepperWidget(
            value=cur_mins, 
            min_val=0, 
            max_val=45, 
            step=15, 
            unit_label="دقیقه",
            parent=self
        )
        steppers_row.addWidget(self.min_stepper, stretch=1)

        self.container_layout.addLayout(steppers_row)

        # ۳. دکمه‌های عملیاتی
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        btn_box.setContentsMargins(0, 8, 0, 0)

        btn_save = QPushButton("ذخیره هدف کاری")
        btn_save.setFixedHeight(38)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 800;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        btn_save.clicked.connect(self._save)
        btn_box.addWidget(btn_save, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #1E283D; color: #F8FAFC; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _set_preset(self, minutes: int):
        self.hour_stepper.set_value(minutes // 60)
        self.min_stepper.set_value(minutes % 60)

    def _save(self):
        self.target_minutes = (self.hour_stepper.value * 60) + self.min_stepper.value
        self.accept()