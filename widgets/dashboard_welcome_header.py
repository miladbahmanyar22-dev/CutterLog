# ==================================================
# FILE: widgets/dashboard_welcome_header.py
# ==================================================
from pathlib import Path
from datetime import datetime
import jdatetime
from typing import Optional

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, 
    QWidget, QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, QTimer, QRectF, QPropertyAnimation, 
    QEasingCurve, Property
)
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, 
    QBrush, QPen, QMouseEvent
)

from core.settings_manager import SettingsManager
from core.project_controller import ProjectController
from core.persian_utils import to_persian_numbers, get_persian_date_readable
from core.signals import global_signals
from time_tracking.timer_engine import TimeTrackingEngine


class StaticSlotDigit(QWidget):
    """
    اسلات قفل‌شده رقم بدون کوچک‌ترین جابه‌جایی چپ/راست (Zero Jitter)
    با ترانزیشن فید نرم و بدون خطای disconnect در سیگنال
    """
    def __init__(self, width: int, font_size: int = 24, font_color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self.slot_width = width
        self.font_size = font_size
        self.font_color = font_color
        self.current_text = "۰۰"
        self._target_text = ""
        self._fade_level = 1.0
        self._is_fading_in = False

        h = int(font_size * 1.5)
        self.setFixedSize(self.slot_width, h)

        self.lbl = QLabel(self.current_text, self)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl.setGeometry(0, 0, self.slot_width, h)
        self.lbl.setStyleSheet(f"""
            QLabel {{
                font-family: 'Vazirmatn';
                font-size: {self.font_size}px;
                font-weight: 900;
                color: {self.font_color};
                background: transparent;
                border: none;
                padding: 0;
            }}
        """)

        self.opacity_effect = QGraphicsOpacityEffect(self.lbl)
        self.lbl.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        self.anim = QPropertyAnimation(self, b"fade_level", self)
        self.anim.setDuration(160)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.anim.finished.connect(self._on_animation_phase_finished)

    def get_fade_level(self) -> float:
        return self._fade_level

    def set_fade_level(self, val: float):
        self._fade_level = val
        self.opacity_effect.setOpacity(val)

    fade_level = Property(float, get_fade_level, set_fade_level)

    def _on_animation_phase_finished(self):
        if not self._is_fading_in:
            self.current_text = self._target_text
            self.lbl.setText(self.current_text)
            self._is_fading_in = True
            self.anim.setStartValue(0.45)
            self.anim.setEndValue(1.0)
            self.anim.start()
        else:
            self._is_fading_in = False

    def set_value(self, new_text: str):
        if new_text == self.current_text and self.anim.state() != QPropertyAnimation.State.Running:
            return

        self._target_text = new_text
        self._is_fading_in = False
        self.anim.stop()
        self.anim.setStartValue(self.opacity_effect.opacity())
        self.anim.setEndValue(0.45)
        self.anim.start()


class MasterTimecodeModule(QFrame):
    """
    ماژول ساعت استودیویی لوکس با پایداری کامل ارقام و بدون پرش به چپ و راست
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(228, 88)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        
        self.target_ratio = 0.0

        self.setObjectName("MasterTimecodeModule")
        self.setStyleSheet("""
            QFrame#MasterTimecodeModule {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0E1322, stop:0.5 #090D18, stop:1 #060812);
                border: 1px solid rgba(99, 102, 241, 0.28);
                border-radius: 12px;
            }
        """)

        self.init_ui()

    def init_ui(self):
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(14, 8, 14, 8)
        main_lay.setSpacing(2)
        main_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ۱. هدر بالای ساعت
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)
        top_row.setDirection(QHBoxLayout.Direction.LeftToRight)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        led_dot = QLabel("●")
        led_dot.setStyleSheet("color: #00F0FF; font-size: 7px; background: transparent; border: none;")
        top_row.addWidget(led_dot)

        lbl_ref = QLabel("MASTER TC • 25 FPS")
        lbl_ref.setStyleSheet("""
            font-family: 'Segoe UI', sans-serif;
            font-size: 8px;
            font-weight: 800;
            color: #6366F1;
            letter-spacing: 0.8px;
            background: transparent;
            border: none;
        """)
        top_row.addWidget(lbl_ref)
        top_row.addStretch()

        self.lbl_target_pct = QLabel("۰٪")
        self.lbl_target_pct.setStyleSheet("""
            font-family: 'Vazirmatn';
            font-size: 10px;
            font-weight: 800;
            color: #34D399;
            background: transparent;
            border: none;
        """)
        top_row.addWidget(self.lbl_target_pct)

        main_lay.addLayout(top_row)

        # ۲. ردیف ارقام با موقعیت کاملاً ثابت و قفل‌شده در محور افقی
        digits_row = QHBoxLayout()
        digits_row.setContentsMargins(0, 0, 0, 0)
        digits_row.setSpacing(0)
        digits_row.setDirection(QHBoxLayout.Direction.LeftToRight)
        digits_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # اسلات ساعت
        self.digit_hours = StaticSlotDigit(width=44, font_size=23, font_color="#F8FAFC", parent=self)
        digits_row.addWidget(self.digit_hours)

        # دو نقطه ثابت
        lbl_colon = QLabel(":")
        lbl_colon.setFixedWidth(12)
        lbl_colon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_colon.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 20px;
                font-weight: 900;
                color: #818CF8;
                background: transparent;
                border: none;
                padding-bottom: 3px;
            }
        """)
        digits_row.addWidget(lbl_colon)

        # اسلات دقیقه
        self.digit_minutes = StaticSlotDigit(width=44, font_size=23, font_color="#F8FAFC", parent=self)
        digits_row.addWidget(self.digit_minutes)

        # فاصله تفکیک‌کننده ثابت
        sep_space = QLabel("")
        sep_space.setFixedWidth(6)
        sep_space.setStyleSheet("background: transparent; border: none;")
        digits_row.addWidget(sep_space)

        # اسلات ثانیه‌شمار فیروزه‌ای
        self.digit_seconds = StaticSlotDigit(width=38, font_size=16, font_color="#00F0FF", parent=self)
        digits_row.addWidget(self.digit_seconds)

        main_lay.addLayout(digits_row)

        # ۳. نوار خطی نئونی پیشرفت هدف کاری در پایین
        self.progress_track = QFrame()
        self.progress_track.setFixedHeight(2.5)
        self.progress_track.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.08);
                border-radius: 1.25px;
                border: none;
            }
        """)
        track_lay = QHBoxLayout(self.progress_track)
        track_lay.setContentsMargins(0, 0, 0, 0)
        track_lay.setSpacing(0)
        track_lay.setDirection(QHBoxLayout.Direction.LeftToRight)

        self.progress_fill = QFrame()
        self.progress_fill.setFixedHeight(2.5)
        self.progress_fill.setStyleSheet("background-color: #6366F1; border-radius: 1.25px; border: none;")
        track_lay.addWidget(self.progress_fill)
        track_lay.addStretch()

        main_lay.addWidget(self.progress_track)

    def set_time_state(self, h: int, m: int, s: int, ratio: float):
        self.digit_hours.set_value(to_persian_numbers(f"{h:02d}"))
        self.digit_minutes.set_value(to_persian_numbers(f"{m:02d}"))
        self.digit_seconds.set_value(to_persian_numbers(f"{s:02d}"))

        self.target_ratio = max(0.0, min(1.0, ratio))
        pct_int = int(self.target_ratio * 100)
        self.lbl_target_pct.setText(f"{to_persian_numbers(pct_int)}٪")

        track_w = self.progress_track.width() if self.progress_track.width() > 0 else 190
        fill_w = max(0, int(track_w * self.target_ratio))
        self.progress_fill.setFixedWidth(fill_w)

        if self.target_ratio >= 1.0:
            self.progress_fill.setStyleSheet("background-color: #10B981; border-radius: 1.25px; border: none;")
            self.lbl_target_pct.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10px; font-weight: 800; color: #10B981; background: transparent; border: none;")
        else:
            self.progress_fill.setStyleSheet("background-color: #6366F1; border-radius: 1.25px; border: none;")
            self.lbl_target_pct.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10px; font-weight: 800; color: #818CF8; background: transparent; border: none;")


class DashboardWelcomeHeader(QFrame):
    """
    هدر پیشخوان مینیمال، لوکس و متمرکز استودیو
    Monolithic Studio Master Slate
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardWelcomeHeaderFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(116)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self._is_hovered = False

        self.urgent_project_id: Optional[int] = None
        self.urgent_text: str = ""

        self.init_ui()
        self._setup_timer()
        self.update_all()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 12, 20, 12)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # پنل راست: تایپوگرافی ادیتوریال و پایش هویتی
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # خط اول: خوش‌آمدگویی رسمی + بج آنلاین
        greeting_row = QHBoxLayout()
        greeting_row.setSpacing(10)
        greeting_row.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_greeting = QLabel("خوش‌آمدید")
        self.lbl_greeting.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 16px;
                font-weight: 900;
                color: #F8FAFC;
                background: transparent;
                border: none;
            }
        """)
        greeting_row.addWidget(self.lbl_greeting)

        self.badge_status = QLabel("●  آماده تدوین")
        self.badge_status.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 10px;
                font-weight: 700;
                color: #34D399;
                background-color: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.28);
                border-radius: 6px;
                padding: 2px 8px;
            }
        """)
        greeting_row.addWidget(self.badge_status)
        greeting_row.addStretch()
        text_col.addLayout(greeting_row)

        # خط دوم: تاریخ تقویم شمسی و شیفت کاری
        self.lbl_date_shift = QLabel()
        self.lbl_date_shift.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 11.5px;
                font-weight: 500;
                color: #94A3B8;
                background: transparent;
                border: none;
            }
        """)
        text_col.addWidget(self.lbl_date_shift)

        # خط سوم: خط متادیتا و پایش فوری ددلاین
        self.lbl_pipeline_status = QLabel()
        self.lbl_pipeline_status.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_pipeline_status.mouseReleaseEvent = self._on_status_clicked
        self.lbl_pipeline_status.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 11px;
                font-weight: 600;
                color: #64748B;
                background: transparent;
                border: none;
            }
        """)
        text_col.addWidget(self.lbl_pipeline_status)

        layout.addLayout(text_col, stretch=1)

        # جداکننده خطی ظریف
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setFixedHeight(54)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        layout.addWidget(divider)

        # پنل چپ: ماژول ساعت با پایداری کامل ارقام
        self.timecode_module = MasterTimecodeModule(self)
        layout.addWidget(self.timecode_module)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            w = float(self.width())
            h = float(self.height())
            rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

            # پس‌زمینه تیتانیومی تاریک و عمیق
            bg_grad = QLinearGradient(0, 0, w, h)
            if self._is_hovered:
                bg_grad.setColorAt(0.0, QColor("#101625"))
                bg_grad.setColorAt(0.6, QColor("#0C111C"))
                bg_grad.setColorAt(1.0, QColor("#080C14"))
                border_pen = QPen(QColor(99, 102, 241, 70), 1.0)
            else:
                bg_grad.setColorAt(0.0, QColor("#0E1321"))
                bg_grad.setColorAt(0.6, QColor("#0A0E18"))
                bg_grad.setColorAt(1.0, QColor("#070A12"))
                border_pen = QPen(QColor(255, 255, 255, 12), 1.0)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_grad))
            painter.drawRoundedRect(rect, 12, 12)

            # هاله نوری محو پشت نام کاربری
            glow = QRadialGradient(w * 0.85, h * 0.35, w * 0.5)
            glow.setColorAt(0.0, QColor(99, 102, 241, 18 if self._is_hovered else 10))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(glow))
            painter.drawRoundedRect(rect, 12, 12)

            # کادر بیرونی شارپ
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 12, 12)
        finally:
            painter.end()

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def _setup_timer(self):
        self.timer_clock = QTimer(self)
        self.timer_clock.timeout.connect(self._tick)
        self.timer_clock.start(1000)

    def _tick(self):
        now = datetime.now()

        ratio = 0.0
        try:
            engine = TimeTrackingEngine.instance()
            today_sec = engine.get_today_total_active_seconds()
            target_mins = engine.get_daily_goal_minutes()
            target_sec = max(1, target_mins * 60)
            ratio = min(1.0, today_sec / target_sec)
        except Exception:
            pass

        self.timecode_module.set_time_state(now.hour, now.minute, now.second, ratio)

    def _get_shift_label(self, hour: int) -> str:
        if 5 <= hour < 12:
            return "شیفت کاری صبح"
        elif 12 <= hour < 17:
            return "شیفت کاری عصر"
        elif 17 <= hour < 21:
            return "ساعات اوج تدوین"
        return "شیفت شب استودیو"

    def _scan_deadlines(self):
        self.urgent_project_id = None
        self.urgent_text = ""
        now = datetime.utcnow()

        try:
            active_projects = ProjectController.get_active_projects()
            candidates = []

            for p in active_projects:
                c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p)
                if pct >= 100 or not p.deadline:
                    continue

                delta_hours = (p.deadline - now).total_seconds() / 3600.0
                if delta_hours <= 48:
                    candidates.append((delta_hours, p))

            if candidates:
                candidates.sort(key=lambda x: x[0])
                hours_left, p = candidates[0]
                self.urgent_project_id = p.id
                title = p.couple_names or p.title

                if hours_left < 0:
                    time_desc = f"{to_persian_numbers(abs(int(hours_left // 24)))} روز گذشته از موعد!"
                elif hours_left <= 24:
                    time_desc = f"تنها {to_persian_numbers(int(hours_left))} ساعت باقی‌مانده"
                else:
                    time_desc = f"{to_persian_numbers(int(hours_left // 24))} روز مانده"

                self.urgent_text = f"⏳ نزدیک‌ترین موعد تحویل: «{title}» ({time_desc})"
        except Exception:
            pass

    def _on_status_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.urgent_project_id:
            global_signals.navigate_and_focus_project.emit(self.urgent_project_id)

    def update_all(self):
        now = datetime.now()
        settings = SettingsManager.load_settings()
        editor_name = settings.get("editor_name", "").strip() or "تدوین‌گر گرامی"

        self.lbl_greeting.setText(f"خوش‌آمدید، {editor_name}")

        today_j = jdatetime.date.today()
        date_str = get_persian_date_readable(today_j)
        shift_str = self._get_shift_label(now.hour)
        self.lbl_date_shift.setText(f"{date_str}   •   {shift_str}")

        self._scan_deadlines()

        if self.urgent_text:
            self.lbl_pipeline_status.setText(self.urgent_text)
            self.lbl_pipeline_status.setStyleSheet("""
                QLabel {
                    font-family: 'Vazirmatn';
                    font-size: 11px;
                    font-weight: 700;
                    color: #FB923C;
                    background: transparent;
                    border: none;
                }
                QLabel:hover {
                    color: #FDBA74;
                }
            """)
            self.lbl_pipeline_status.setToolTip("کلیک برای هدایت مستقیم به پرونده این پروژه")
        else:
            self.lbl_pipeline_status.setText("✦  پایپ‌لاین پروژه‌ها در وضعیت منظم و پایدار قرار دارد")
            self.lbl_pipeline_status.setStyleSheet("""
                QLabel {
                    font-family: 'Vazirmatn';
                    font-size: 11px;
                    font-weight: 500;
                    color: #64748B;
                    background: transparent;
                    border: none;
                }
            """)
            self.lbl_pipeline_status.setToolTip("")

        self._tick()
        self.update()