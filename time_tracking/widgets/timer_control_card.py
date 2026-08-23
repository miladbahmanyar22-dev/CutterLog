# ==================================================
# FILE: time_tracking/widgets/timer_control_card.py
# ==================================================
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSizePolicy, QGraphicsOpacityEffect, QWidget
)
from PySide6.QtGui import QFontDatabase, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, QRectF
from time_tracking.timer_engine import TimeTrackingEngine
from core.signals import global_signals


def format_seconds_hms(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class RollingDigitSlot(QWidget):
    def __init__(self, font_name: str, font_size: int = 24, text_color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self.font_name = font_name
        self.font_size = font_size
        self.text_color_hex = text_color
        self.current_char = "0"
        self.next_char = "0"
        self._progress = 1.0

        self.setFixedSize(28, 44)
        self.anim = QPropertyAnimation(self, b"progress", self)
        self.anim.setDuration(240)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_progress(self) -> float:
        return self._progress

    def set_progress(self, val: float):
        self._progress = val
        self.update()

    progress = Property(float, get_progress, set_progress)

    def set_char(self, new_char: str, animate: bool = True):
        if self.current_char == new_char:
            return
        if not animate:
            self.current_char = new_char
            self.next_char = new_char
            self._progress = 1.0
            self.update()
            return

        self.next_char = new_char
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def set_color(self, color_hex: str):
        self.text_color_hex = color_hex
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())

        slot_rect = QRectF(0, 0, w, h)
        painter.setPen(QColor(255, 255, 255, 12))
        painter.setBrush(QColor("#0B101D"))
        painter.drawRoundedRect(slot_rect, 6, 6)

        painter.setClipRect(slot_rect)
        f = QFont(self.font_name, self.font_size, QFont.Weight.Bold)
        painter.setFont(f)
        painter.setPen(QColor(self.text_color_hex))

        if self._progress < 1.0:
            offset_curr = self._progress * h
            painter.drawText(QRectF(0, offset_curr, w, h), Qt.AlignmentFlag.AlignCenter, self.current_char)
            offset_next = -h + (self._progress * h)
            painter.drawText(QRectF(0, offset_next, w, h), Qt.AlignmentFlag.AlignCenter, self.next_char)
        else:
            self.current_char = self.next_char
            painter.drawText(slot_rect, Qt.AlignmentFlag.AlignCenter, self.current_char)


class TimerControlCard(QFrame):
    def __init__(self, on_pause_cb, on_finish_clip_cb, on_reopen_clip_cb=None, parent=None):
        super().__init__(parent)
        self.on_pause_cb = on_pause_cb
        self.on_finish_clip_cb = on_finish_clip_cb
        self.on_reopen_clip_cb = on_reopen_clip_cb
        self.engine = TimeTrackingEngine.instance()

        self.project_title = "پروژه‌ای انتخاب نشده"
        self.studio_title = "—"
        self.clip_title = "کلیپ انتخاب نشده"
        self.is_clip_locked = False
        self.accumulated_spent_seconds = 0
        self.digital_font_name = self._load_digital_font()
        self.colon_visible = True

        self.setObjectName("TimerHeroCard")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(195)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.init_ui()
        self._setup_pulse_animations()
        self._connect_signals()
        self.update_display_state()

    def _load_digital_font(self) -> str:
        try:
            if hasattr(sys, '_MEIPASS'):
                base_dir = Path(sys._MEIPASS)
            else:
                base_dir = Path(__file__).resolve().parent.parent.parent

            possible_paths = [
                base_dir / "fonts" / "DSEG7Classic-Regular.ttf",
                base_dir / "assets" / "fonts" / "DSEG7Classic-Regular.ttf",
                Path("fonts/DSEG7Classic-Regular.ttf").resolve(),
                Path("assets/fonts/DSEG7Classic-Regular.ttf").resolve(),
            ]

            for font_path in possible_paths:
                if font_path.exists():
                    font_id = QFontDatabase.addApplicationFont(str(font_path))
                    if font_id != -1:
                        families = QFontDatabase.applicationFontFamilies(font_id)
                        if families:
                            return families[0]
        except Exception:
            pass

        return "DSEG7 Classic"

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        # ۱. ردیف بالا
        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_status_badge = QLabel("آماده شروع فرآیند تدوین")
        self.lbl_status_badge.setFixedHeight(26)
        self.lbl_status_badge.setStyleSheet("""
            font-family: 'Vazirmatn';
            font-size: 11px;
            font-weight: 700;
            color: #94A3B8;
            background-color: #161F30;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 13px;
            padding: 0 14px;
        """)
        top_row.addWidget(self.lbl_status_badge)

        self.lbl_context = QLabel("پروژه و قطعه مورد نظر را انتخاب نمایید")
        self.lbl_context.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8; border: none; background: transparent;")
        top_row.addWidget(self.lbl_context, stretch=1)

        layout.addLayout(top_row)

        # ۲. پنل دیجیتال
        self.timer_screen = QFrame()
        self.timer_screen.setObjectName("TimerScreenFrame")
        self.timer_screen.setFixedHeight(68)
        self.timer_screen.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.timer_screen.setStyleSheet("""
            QFrame#TimerScreenFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #060911, stop:1 #0C1220);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        screen_layout = QHBoxLayout(self.timer_screen)
        screen_layout.setContentsMargins(12, 0, 12, 0)
        screen_layout.setSpacing(4)
        screen_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.slot_h1 = RollingDigitSlot(self.digital_font_name, text_color="#FFFFFF")
        self.slot_h2 = RollingDigitSlot(self.digital_font_name, text_color="#FFFFFF")

        self.lbl_colon1 = QLabel(":")
        self.lbl_colon1.setFixedWidth(14)
        self.lbl_colon1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_colon1.setStyleSheet(f"font-family:'{self.digital_font_name}', monospace; font-size:24px; font-weight:bold; color:#FFFFFF; background:transparent;")

        self.slot_m1 = RollingDigitSlot(self.digital_font_name, text_color="#FFFFFF")
        self.slot_m2 = RollingDigitSlot(self.digital_font_name, text_color="#FFFFFF")

        self.lbl_colon2 = QLabel(":")
        self.lbl_colon2.setFixedWidth(14)
        self.lbl_colon2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_colon2.setStyleSheet(f"font-family:'{self.digital_font_name}', monospace; font-size:24px; font-weight:bold; color:#FBBF24; background:transparent;")

        self.slot_s1 = RollingDigitSlot(self.digital_font_name, text_color="#FBBF24")
        self.slot_s2 = RollingDigitSlot(self.digital_font_name, text_color="#FBBF24")

        screen_layout.addWidget(self.slot_h1)
        screen_layout.addWidget(self.slot_h2)
        screen_layout.addWidget(self.lbl_colon1)
        screen_layout.addWidget(self.slot_m1)
        screen_layout.addWidget(self.slot_m2)
        screen_layout.addWidget(self.lbl_colon2)
        screen_layout.addWidget(self.slot_s1)
        screen_layout.addWidget(self.slot_s2)

        layout.addWidget(self.timer_screen)

        # ۳. دکمه‌های کنترل
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_start = QPushButton("شروع جلسه کاری")
        self.btn_start.setFixedHeight(38)
        self.btn_start.setMinimumWidth(170)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10B981, stop:1 #059669);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                font-size: 12.5px;
                font-weight: 800;
                padding: 0 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34D399, stop:1 #10B981);
                border-color: #6EE7B7;
            }
        """)
        self.btn_start.clicked.connect(self._handle_start)
        btn_row.addWidget(self.btn_start)

        # دکمه بازگشایی و لغو قفل (هنگام کلیک اشتباه یا نیاز به اصلاح مجدد)
        self.btn_reopen = QPushButton("🔓 بازگشایی و ادامه تدوین")
        self.btn_reopen.setFixedHeight(38)
        self.btn_reopen.setMinimumWidth(180)
        self.btn_reopen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reopen.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(99, 102, 241, 0.15);
                color: #818CF8;
                border: 1px solid rgba(99, 102, 241, 0.4);
                border-radius: 8px;
                font-size: 12.5px;
                font-weight: 700;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #6366F1;
                color: #FFFFFF;
                border-color: #818CF8;
            }
        """)
        self.btn_reopen.clicked.connect(self._handle_reopen)
        self.btn_reopen.setVisible(False)
        btn_row.addWidget(self.btn_reopen)

        self.btn_pause = QPushButton("توقف موقت جلسه")
        self.btn_pause.setFixedHeight(38)
        self.btn_pause.setMinimumWidth(125)
        self.btn_pause.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pause.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #1E283D;
                border-color: #6366F1;
                color: #818CF8;
            }
        """)
        self.btn_pause.clicked.connect(self.on_pause_cb)
        self.btn_pause.setVisible(False)
        btn_row.addWidget(self.btn_pause)

        self.btn_resume = QPushButton("ادامه جلسه کاری")
        self.btn_resume.setFixedHeight(38)
        self.btn_resume.setMinimumWidth(140)
        self.btn_resume.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_resume.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F59E0B, stop:1 #D97706);
                color: #000000;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 800;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FBBF24, stop:1 #F59E0B);
            }
        """)
        self.btn_resume.clicked.connect(self._handle_resume)
        self.btn_resume.setVisible(False)
        btn_row.addWidget(self.btn_resume)

        self.btn_finish_clip = QPushButton("تأیید و ثبت نهایی کلیپ")
        self.btn_finish_clip.setFixedHeight(38)
        self.btn_finish_clip.setMinimumWidth(160)
        self.btn_finish_clip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_finish_clip.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(16, 185, 129, 0.12);
                color: #34D399;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #10B981;
                color: #FFFFFF;
                border-color: #10B981;
            }
        """)
        self.btn_finish_clip.clicked.connect(self.on_finish_clip_cb)
        self.btn_finish_clip.setVisible(False)
        btn_row.addWidget(self.btn_finish_clip)

        layout.addLayout(btn_row)

        self.setStyleSheet("""
            QFrame#TimerHeroCard {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)

    def _setup_pulse_animations(self):
        self.opacity_effect = QGraphicsOpacityEffect(self.lbl_status_badge)
        self.lbl_status_badge.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        self.pulse_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.pulse_anim.setDuration(1200)
        self.pulse_anim.setStartValue(1.0)
        self.pulse_anim.setKeyValueAt(0.5, 0.35)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_anim.setLoopCount(-1)

    def _render_timer_display(self, total_seconds: int):
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60

        str_h = f"{h:02d}"
        str_m = f"{m:02d}"
        str_s = f"{s:02d}"

        animate = (self.engine.is_running and not self.engine.is_paused)

        if self.is_clip_locked:
            # حالت تکمیل‌شده: خاکستری، مات و بدون چشمک‌زدن
            color_hm = "#64748B"
            color_s = "#475569"
            colon_c = "#475569"
            self.timer_screen.setStyleSheet("""
                QFrame#TimerScreenFrame {
                    background-color: #101624;
                    border: 1px solid rgba(255, 255, 255, 0.04);
                    border-radius: 10px;
                }
            """)
        elif not self.engine.is_running:
            color_hm = "#64748B"
            color_s = "#475569"
            colon_c = "#475569"
            self.timer_screen.setStyleSheet("""
                QFrame#TimerScreenFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #060911, stop:1 #0C1220);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 10px;
                }
            """)
        elif self.engine.is_paused:
            color_hm = "#F8FAFC"
            color_s = "#F59E0B"
            colon_c = "#F59E0B"
            self.timer_screen.setStyleSheet("""
                QFrame#TimerScreenFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #060911, stop:1 #0C1220);
                    border: 1px solid rgba(245, 158, 11, 0.35);
                    border-radius: 10px;
                }
            """)
        else:
            color_hm = "#FFFFFF"
            color_s = "#FBBF24"
            colon_c = "#FBBF24" if self.colon_visible else "rgba(251,191,36,0.2)"
            self.colon_visible = not self.colon_visible
            self.timer_screen.setStyleSheet("""
                QFrame#TimerScreenFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #060911, stop:1 #0C1220);
                    border: 1px solid rgba(99, 102, 241, 0.35);
                    border-radius: 10px;
                }
            """)

        self.slot_h1.set_color(color_hm)
        self.slot_h2.set_color(color_hm)
        self.slot_m1.set_color(color_hm)
        self.slot_m2.set_color(color_hm)
        self.slot_s1.set_color(color_s)
        self.slot_s2.set_color(color_s)

        self.slot_h1.set_char(str_h[0], animate=animate)
        self.slot_h2.set_char(str_h[1], animate=animate)
        self.slot_m1.set_char(str_m[0], animate=animate)
        self.slot_m2.set_char(str_m[1], animate=animate)
        self.slot_s1.set_char(str_s[0], animate=animate)
        self.slot_s2.set_char(str_s[1], animate=animate)

        self.lbl_colon1.setStyleSheet(f"font-family:'{self.digital_font_name}', monospace; font-size:24px; font-weight:bold; color:{colon_c}; background:transparent;")
        self.lbl_colon2.setStyleSheet(f"font-family:'{self.digital_font_name}', monospace; font-size:24px; font-weight:bold; color:{colon_c}; background:transparent;")

    def _connect_signals(self):
        global_signals.timer_tick.connect(self._on_timer_tick)
        global_signals.session_started.connect(lambda _: self.update_display_state())
        global_signals.session_ended.connect(lambda _: self.update_display_state())
        global_signals.session_paused.connect(lambda _: self.update_display_state())
        global_signals.session_resumed.connect(lambda _: self.update_display_state())

    def set_context(self, project_title: str, studio_title: str, clip_title: str, is_completed: bool = False, accumulated_seconds: int = 0):
        self.project_title = project_title
        self.studio_title = studio_title
        self.clip_title = clip_title
        self.is_clip_locked = is_completed
        self.accumulated_spent_seconds = accumulated_seconds
        self._update_context_label()
        self.update_display_state()

    def _update_context_label(self):
        if self.is_clip_locked:
            self.lbl_context.setText(f"پروژه: <b style='color:#94A3B8;'>{self.project_title}</b> | قطعه: <span style='color:#64748B;'>{self.clip_title} (مختومه)</span>")
        elif self.engine.is_running:
            self.lbl_context.setText(f"پروژه فعال: <b style='color:#F8FAFC;'>{self.project_title}</b> | قطعه: <span style='color:#818CF8;'>{self.clip_title}</span> <span style='color:#64748B;'>({self.studio_title})</span>")
        else:
            self.lbl_context.setText(f"پروژه انتخابی: <b style='color:#F8FAFC;'>{self.project_title}</b> | قطعه: <span style='color:#818CF8;'>{self.clip_title}</span>")

    def _on_timer_tick(self, snap: dict):
        total_time_to_display = self.accumulated_spent_seconds + snap["active_seconds"]
        self._render_timer_display(total_time_to_display)

    def update_display_state(self):
        self._update_context_label()

        if self.is_clip_locked:
            self.pulse_anim.stop()
            self.opacity_effect.setOpacity(1.0)
            
            # دکمه شروع مخفی شده و دکمه بازگشایی ظاهر می‌شود
            self.btn_start.setVisible(False)
            self.btn_reopen.setVisible(True)
            self.btn_pause.setVisible(False)
            self.btn_resume.setVisible(False)
            self.btn_finish_clip.setVisible(False)
            
            self.lbl_status_badge.setText("🔒 وضعیت: تدوین و رندر نهایی تکمیل شد")
            self.lbl_status_badge.setStyleSheet("""
                font-family: 'Vazirmatn';
                font-size: 11px;
                font-weight: 700;
                color: #94A3B8;
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 13px;
                padding: 0 14px;
            """)
            self._render_timer_display(self.accumulated_spent_seconds)
            return

        self.btn_reopen.setVisible(False)

        if self.engine.is_running:
            self.btn_start.setVisible(False)
            self.btn_finish_clip.setVisible(True)

            if self.engine.is_paused:
                self.btn_pause.setVisible(False)
                self.btn_resume.setVisible(True)

                self.pulse_anim.stop()
                self.opacity_effect.setOpacity(1.0)

                self.lbl_status_badge.setText("توقف موقت فرآیند")
                self.lbl_status_badge.setStyleSheet("""
                    font-family: 'Vazirmatn';
                    font-size: 11px;
                    font-weight: 700;
                    color: #F59E0B;
                    background-color: rgba(245, 158, 11, 0.15);
                    border: 1px solid rgba(245, 158, 11, 0.35);
                    border-radius: 13px;
                    padding: 0 14px;
                """)
                self._render_timer_display(self.accumulated_spent_seconds + self.engine.active_seconds)
            else:
                self.btn_pause.setVisible(True)
                self.btn_resume.setVisible(False)

                self.lbl_status_badge.setText("در حال ثبت زمان تدوین")
                self.lbl_status_badge.setStyleSheet("""
                    font-family: 'Vazirmatn';
                    font-size: 11px;
                    font-weight: 800;
                    color: #10B981;
                    background-color: rgba(16, 185, 129, 0.16);
                    border: 1.5px solid #10B981;
                    border-radius: 13px;
                    padding: 0 14px;
                """)
                self._render_timer_display(self.accumulated_spent_seconds + self.engine.active_seconds)

                if self.pulse_anim.state() != QPropertyAnimation.State.Running:
                    self.pulse_anim.start()
        else:
            self.pulse_anim.stop()
            self.opacity_effect.setOpacity(1.0)

            self.btn_start.setVisible(True)
            self.btn_pause.setVisible(False)
            self.btn_resume.setVisible(False)
            self.btn_finish_clip.setVisible(False)

            self.lbl_status_badge.setText("آماده شروع فرآیند تدوین")
            self.lbl_status_badge.setStyleSheet("""
                font-family: 'Vazirmatn';
                font-size: 11px;
                font-weight: 700;
                color: #94A3B8;
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 13px;
                padding: 0 14px;
            """)
            self._render_timer_display(self.accumulated_spent_seconds)

    def _handle_start(self):
        if not self.engine.current_project_id:
            global_signals.show_toast.emit("لطفاً ابتدا یک پروژه یا کلیپ را انتخاب فرمایید.", "warning")
            return
        self.engine.start_session(self.engine.current_project_id, self.engine.current_clip_id)

    def _handle_resume(self):
        self.engine.resume_session()

    def _handle_reopen(self):
        if self.on_reopen_clip_cb:
            self.on_reopen_clip_cb()