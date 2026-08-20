# ==================================================
# FILE: widgets/dashboard_welcome_header.py
# ==================================================
import random
from datetime import datetime
import jdatetime
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, 
    QPushButton, QGraphicsOpacityEffect, QWidget, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QTimer, QTime, QSize, QPropertyAnimation, 
    QEasingCurve, Property, QRectF, QPointF
)
from PySide6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, 
    QPen, QBrush, QPainterPath, QFont
)

from core.settings_manager import SettingsManager
from core.persian_utils import to_persian_numbers, get_persian_date_readable
from core.icon_provider import IconProvider

EDITING_QUOTES = [
    "تدوین یعنی روح بخشیدن به نماهای پراکنده؛ امروز فریم‌ها را به داستان تبدیل کن.",
    "هر کات یک تصمیم هنری است؛ ریتم داستان در دستان توست.",
    "در تدوین، سکوت‌ها و مکث‌ها به اندازه کات‌ها قدرتمندند.",
    "بهترین تدوین آن است که احساس شود، نه اینکه دیده شود.",
    "کات درست در لحظه درست، جادوی سینما را خلق می‌کند.",
    "یک تایم‌لاین منظم، ذهن آرام و خروجی شاهکار می‌سازد.",
    "تدوین هنر دور ریختن خوب‌ها برای خلق شاهکار است.",
    "ریتم را با چشمانت نبین، با قلبت احساس کن.",
    "تفاوت کار خوب با کار عالی در توجه به فریم‌های پایانی است.",
    "تدوین‌گر آخرین نویسنده و اولین مخاطب فیلم است."
]


class AnimatedDigitCell(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 22)
        self._current_char = "۰"
        self._next_char = "۰"
        self._offset = 0.0

        self.anim = QPropertyAnimation(self, b"offset")
        self.anim.setDuration(240)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, val: float):
        self._offset = val
        self.update()

    offset = Property(float, get_offset, set_offset)

    def set_char(self, new_char: str):
        if self._current_char == new_char:
            return
        self._next_char = new_char
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.finished.connect(self._on_anim_finished)
        self.anim.start()

    def set_char_instant(self, char: str):
        self._current_char = char
        self._next_char = char
        self._offset = 0.0
        self.update()

    def _on_anim_finished(self):
        try:
            self.anim.finished.disconnect(self._on_anim_finished)
        except Exception:
            pass
        self._current_char = self._next_char
        self._offset = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        font = QFont("Vazirmatn", 11, QFont.Weight.Black)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        painter.setFont(font)

        w, h = float(self.width()), float(self.height())

        if self._offset == 0.0:
            painter.setPen(QColor("#A5B4FC"))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, self._current_char)
        else:
            old_y = -self._offset * h
            alpha_old = max(0, int(255 * (1.0 - self._offset)))
            painter.setPen(QColor(165, 180, 252, alpha_old))
            painter.drawText(QRectF(0, old_y, w, h), Qt.AlignmentFlag.AlignCenter, self._current_char)

            new_y = (1.0 - self._offset) * h
            alpha_new = min(255, int(255 * self._offset))
            painter.setPen(QColor(165, 180, 252, alpha_new))
            painter.drawText(QRectF(0, new_y, w, h), Qt.AlignmentFlag.AlignCenter, self._next_char)

        painter.end()


class TimeSegmentBlock(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 26)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(14, 20, 34, 0.90);
                border: 1px solid rgba(99, 102, 241, 0.22);
                border-radius: 5px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 0, 1, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.digit1 = AnimatedDigitCell(self)
        self.digit2 = AnimatedDigitCell(self)
        layout.addWidget(self.digit1)
        layout.addWidget(self.digit2)


class StudioTimecodeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setFixedHeight(28)
        self.setFixedWidth(132)
        self._colon_visible = True
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.block_hour = TimeSegmentBlock(self)
        layout.addWidget(self.block_hour)

        self.lbl_colon1 = QLabel(":")
        self.lbl_colon1.setFixedWidth(4)
        self.lbl_colon1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_colon1.setStyleSheet("color: #6366F1; font-family: 'Segoe UI'; font-size: 13px; font-weight: 900; background: transparent; border: none;")
        layout.addWidget(self.lbl_colon1)

        self.block_min = TimeSegmentBlock(self)
        layout.addWidget(self.block_min)

        self.lbl_colon2 = QLabel(":")
        self.lbl_colon2.setFixedWidth(4)
        self.lbl_colon2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_colon2.setStyleSheet("color: #6366F1; font-family: 'Segoe UI'; font-size: 13px; font-weight: 900; background: transparent; border: none;")
        layout.addWidget(self.lbl_colon2)

        self.block_sec = TimeSegmentBlock(self)
        layout.addWidget(self.block_sec)

    def set_time_string(self, time_str: str, animated: bool = True):
        digits = [c for c in time_str if c.isdigit()]
        if len(digits) < 6:
            return

        cells = [
            self.block_hour.digit1, self.block_hour.digit2,
            self.block_min.digit1, self.block_min.digit2,
            self.block_sec.digit1, self.block_sec.digit2
        ]

        for i, d in enumerate(digits):
            fa_char = to_persian_numbers(d)
            if animated:
                cells[i].set_char(fa_char)
            else:
                cells[i].set_char_instant(fa_char)

        self._colon_visible = not self._colon_visible
        colon_color = "#818CF8" if self._colon_visible else "rgba(99, 102, 241, 0.40)"
        self.lbl_colon1.setStyleSheet(f"color: {colon_color}; font-family: 'Segoe UI'; font-size: 13px; font-weight: 900; background: transparent; border: none;")
        self.lbl_colon2.setStyleSheet(f"color: {colon_color}; font-family: 'Segoe UI'; font-size: 13px; font-weight: 900; background: transparent; border: none;")


class DashboardWelcomeHeader(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardWelcomeHeaderFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.current_quote_idx = 0
        self.is_animating = False
        self._last_greeting_key = None
        self._last_day_key = None
        self._glow_color = QColor(99, 102, 241, 35)

        self.init_ui()
        self._setup_timer()
        self.update_all()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # ۱. ستون تحیت و پیام انگیزشی
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        top_greeting_row = QHBoxLayout()
        top_greeting_row.setSpacing(8)
        top_greeting_row.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.live_badge = QLabel("● آنلاین")
        self.live_badge.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 9.5px;
                font-weight: 700;
                color: #10B981;
                background-color: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 8px;
                padding: 1px 6px;
            }
        """)
        top_greeting_row.addWidget(self.live_badge)

        self.lbl_greeting = QLabel()
        self.lbl_greeting.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14.5px; font-weight: 900; color: #F8FAFC; border: none; background: transparent;")
        top_greeting_row.addWidget(self.lbl_greeting)
        top_greeting_row.addStretch()
        text_col.addLayout(top_greeting_row)

        # کپسول شیشه‌ای نقل‌قول
        quote_card = QFrame()
        quote_card.setStyleSheet("background-color: rgba(16, 22, 35, 0.65); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px;")
        quote_row = QHBoxLayout(quote_card)
        quote_row.setContentsMargins(8, 4, 8, 4)
        quote_row.setSpacing(6)
        quote_row.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        lbl_q_icon = QLabel("🎬")
        lbl_q_icon.setStyleSheet("font-size: 10.5px; background: transparent; border: none;")
        quote_row.addWidget(lbl_q_icon)

        self.lbl_quote = QLabel()
        self.lbl_quote.setWordWrap(False)
        self.lbl_quote.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; border: none; background: transparent;")

        self.opacity_effect = QGraphicsOpacityEffect(self.lbl_quote)
        self.lbl_quote.setGraphicsEffect(self.opacity_effect)
        quote_row.addWidget(self.lbl_quote, stretch=1)

        text_col.addWidget(quote_card)
        layout.addLayout(text_col, stretch=1)

        # ۲. پاد ساعت استودیویی
        time_pod = QFrame()
        time_pod.setFixedWidth(175)
        time_pod.setStyleSheet("""
            QFrame {
                background-color: rgba(12, 17, 28, 0.88);
                border: 1px solid rgba(99, 102, 241, 0.22);
                border-radius: 8px;
            }
        """)
        time_col = QVBoxLayout(time_pod)
        time_col.setContentsMargins(8, 6, 8, 6)
        time_col.setSpacing(2)
        time_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_meta = QHBoxLayout()
        top_meta.setContentsMargins(2, 0, 2, 0)
        top_meta.setSpacing(4)
        top_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dot_rec = QLabel("●")
        dot_rec.setStyleSheet("color: #EF4444; font-size: 7.5px; background: transparent; border: none;")
        top_meta.addWidget(dot_rec)

        lbl_tc = QLabel("TIMECODE • 25 FPS")
        lbl_tc.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 8px; font-weight: 800; color: #818CF8; letter-spacing: 0.5px; background: transparent; border: none;")
        top_meta.addWidget(lbl_tc)
        time_col.addLayout(top_meta)

        self.timecode_widget = StudioTimecodeWidget(time_pod)
        time_col.addWidget(self.timecode_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lbl_date = QLabel()
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date.setStyleSheet("font-family: 'Vazirmatn'; font-size: 9.5px; color: #94A3B8; font-weight: 600; border: none; background: transparent;")
        time_col.addWidget(self.lbl_date)

        layout.addWidget(time_pod)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.setClipPath(path)

        painter.fillRect(rect, QColor("#111624"))

        glow = QRadialGradient(QPointF(self.width() * 0.90, 0), self.width() * 0.55)
        glow.setColorAt(0.0, self._glow_color)
        glow.setColorAt(1.0, QColor(17, 22, 36, 0))
        painter.fillRect(rect, glow)

        painter.setClipping(False)
        painter.setPen(QPen(QColor(255, 255, 255, 14), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0), 12, 12)
        painter.end()

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self):
        now = datetime.now()
        now_time = QTime.currentTime().toString("HH:mm:ss")
        self.timecode_widget.set_time_string(now_time, animated=True)

        greeting_text, icon_symbol, glow_col = self._get_time_greeting(now.hour)
        current_greeting_key = f"{greeting_text}_{icon_symbol}"
        if current_greeting_key != self._last_greeting_key:
            self._last_greeting_key = current_greeting_key
            self._glow_color = glow_col
            self._refresh_greeting_text()
            self.update()

        today_key = (now.year, now.month, now.day)
        if today_key != self._last_day_key:
            self._last_day_key = today_key
            today_j = jdatetime.date.today()
            self.lbl_date.setText(get_persian_date_readable(today_j))

    def _get_time_greeting(self, hour: int = None) -> tuple[str, str, QColor]:
        if hour is None:
            hour = datetime.now().hour
        if 5 <= hour < 11:
            return "صبح بخیر", "☀️", QColor(245, 158, 11, 40)
        elif 11 <= hour < 17:
            return "ظهر بخیر", "🌤️", QColor(56, 189, 248, 38)
        elif 17 <= hour < 21:
            return "عصر بخیر", "🌆", QColor(251, 146, 60, 42)
        else:
            return "شب بخیر", "🌙", QColor(99, 102, 241, 45)

    def _refresh_greeting_text(self):
        settings = SettingsManager.load_settings()
        editor_name = settings.get("editor_name") or "تدوین‌گر گرامی"
        greeting_text, icon_symbol, _ = self._get_time_greeting()
        self.lbl_greeting.setText(f"{greeting_text}، {editor_name} {icon_symbol}")

    def update_all(self):
        now = datetime.now()
        today_j = jdatetime.date.today()
        self._last_day_key = (now.year, now.month, now.day)
        
        greeting_text, icon_symbol, glow_col = self._get_time_greeting(now.hour)
        self._last_greeting_key = f"{greeting_text}_{icon_symbol}"
        self._glow_color = glow_col
        
        self._refresh_greeting_text()

        self.current_quote_idx = (today_j.day - 1) % len(EDITING_QUOTES)
        self.lbl_quote.setText(f"« {EDITING_QUOTES[self.current_quote_idx]} »")
        self.opacity_effect.setOpacity(1.0)

        self.lbl_date.setText(get_persian_date_readable(today_j))
        
        now_time = QTime.currentTime().toString("HH:mm:ss")
        self.timecode_widget.set_time_string(now_time, animated=False)
        self.update()