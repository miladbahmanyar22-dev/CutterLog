# ==================================================
# FILE: widgets/dashboard_welcome_header.py
# ==================================================
import random
import math
from datetime import datetime
import jdatetime
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, 
    QGraphicsOpacityEffect, QWidget, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QTimer, QTime, QPropertyAnimation, 
    QEasingCurve, Property, QRectF, QPointF
)
from PySide6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient, 
    QPen, QBrush, QPainterPath, QFont
)

from core.settings_manager import SettingsManager
from core.persian_utils import to_persian_numbers, get_persian_date_readable

EDITING_QUOTES = [
    "تدوین یعنی روح بخشیدن به نماهای پراکنده؛ امروز فریم‌ها را به داستان تبدیل کن.",
    "هر کات یک تصمیم هنری است؛ ریتم داستان در دستان توست.",
    "در تدوین، سکوت‌ها و مکث‌ها به اندازه کات‌ها قدرتمندند.",
    "بهترین تدوین آن است که احساس شود، نه اینکه دیده شود.",
    "کات درست در لحظه درست، جادوی سینما را خلق می‌کند.",
    "یک تایم‌لاین منظم، ذهن آرام و خروجی شاهکار می‌سازد.",
    "تدوین هنر دور ریختن خوب‌ها برای خلق شاهکار است.",
    "ریتم را با چشمان نبین، با قلبت احساس کن.",
    "تفاوت کار خوب با کار عالی در توجه به فریم‌های پایانی است.",
    "تدوین‌گر آخرین نویسنده و اولین مخاطب فیلم است."
]


# ----------------------------------------------------
# ویجت‌های ارقام دیجیتال و تایم‌کد (کاملاً دست‌نخورده)
# ----------------------------------------------------
class AnimatedDigitCell(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 22)
        self._current_char = "۰"
        self._next_char = "۰"
        self._offset = 0.0

        self.anim = QPropertyAnimation(self, b"offset")
        self.anim.setDuration(160)
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
        if self.anim.state() == QPropertyAnimation.State.Running:
            self.anim.stop()
            self._current_char = self._next_char

        self._next_char = new_char
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def set_char_instant(self, char: str):
        self.anim.stop()
        self._current_char = char
        self._next_char = char
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


# ----------------------------------------------------
# کلاس هدر پیشخوان با Seasonal Studio Atmosphere
# ----------------------------------------------------
class DashboardWelcomeHeader(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardWelcomeHeaderFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.current_quote_idx = 0
        self._last_greeting_key = None
        self._last_day_key = None
        self.rotation_angle = 0.0

        self.current_season = "spring"
        self._init_season_structures()

        self.init_ui()
        self._setup_timer()
        self.update_all()

    # =========================================================================
    # سیستم فصلی خودکار (بدون Override تست)
    # =========================================================================
    def _get_current_season(self) -> str:
        """تشخیص خودکار فصل بر مبنای ماه تاریخ جاری سیستم شمسی"""
        try:
            today_j = jdatetime.date.today()
            month = today_j.month
        except Exception:
            month = 1

        if 1 <= month <= 3:
            return "spring"
        elif 4 <= month <= 6:
            return "summer"
        elif 7 <= month <= 9:
            return "autumn"
        else:
            return "winter"

    def _init_season_structures(self):
        """مقداردهی اولیه پایدار ساختار ذرات"""
        # ۱. گلبرگ‌های بهاری
        self._spring_petals = []
        for _ in range(4):
            self._spring_petals.append({
                "x": random.uniform(10.0, 110.0),
                "y": random.uniform(15.0, 105.0),
                "speed_x": random.uniform(0.25, 0.45),
                "speed_y": random.uniform(0.10, 0.25),
                "angle": random.uniform(0.0, 360.0),
                "rot_speed": random.uniform(0.3, 0.8),
                "scale": random.uniform(0.8, 1.2),
                "phase": random.uniform(0.0, 6.28)
            })

        # ۲. ذرات نورانی تابستانی
        self._summer_sparks = []
        for _ in range(3):
            self._summer_sparks.append({
                "orbit_r": random.uniform(34.0, 48.0),
                "speed": random.uniform(0.015, 0.035),
                "current_theta": random.uniform(0.0, 6.28),
                "pulse_phase": random.uniform(0.0, 6.28),
                "size": random.uniform(1.2, 1.8)
            })

        # ۳. برگ‌های پاییزی
        self._autumn_leaves = []
        colors_autumn = [
            QColor(217, 119, 6, 175),
            QColor(234, 88, 12, 160),
            QColor(185, 28, 28, 140)
        ]
        for i in range(3):
            self._autumn_leaves.append({
                "x": random.uniform(20.0, 100.0),
                "y": random.uniform(-10.0, 120.0),
                "speed_y": random.uniform(0.30, 0.50),
                "sway_amp": random.uniform(0.40, 0.70),
                "sway_phase": random.uniform(0.0, 6.28),
                "angle": random.uniform(0.0, 360.0),
                "rot_speed": random.uniform(0.2, 0.6),
                "scale": random.uniform(0.85, 1.15),
                "color": colors_autumn[i % len(colors_autumn)]
            })

        # ۴. دانه‌های برف زمستانی
        self._winter_snowflakes = []
        for _ in range(5):
            self._winter_snowflakes.append({
                "x": random.uniform(15.0, 105.0),
                "y": random.uniform(-5.0, 125.0),
                "speed_y": random.uniform(0.20, 0.40),
                "sway_freq": random.uniform(0.02, 0.04),
                "sway_phase": random.uniform(0.0, 6.28),
                "r": random.uniform(1.0, 2.0),
                "alpha": random.randint(110, 200)
            })

    def _update_season_animation(self):
        """به‌روزرسانی فریم‌ها بدون مصرف حافظه اضافه"""
        for p in self._spring_petals:
            p["x"] += p["speed_x"]
            p["y"] += math.sin(p["phase"]) * 0.20 + p["speed_y"]
            p["phase"] += 0.03
            p["angle"] += p["rot_speed"]
            if p["x"] > 130.0 or p["y"] > 125.0:
                p["x"] = random.uniform(-5.0, 15.0)
                p["y"] = random.uniform(10.0, 80.0)

        for s in self._summer_sparks:
            s["current_theta"] += s["speed"]
            s["pulse_phase"] += 0.04

        for leaf in self._autumn_leaves:
            leaf["y"] += leaf["speed_y"]
            leaf["x"] += math.sin(leaf["sway_phase"]) * leaf["sway_amp"]
            leaf["sway_phase"] += 0.035
            leaf["angle"] += leaf["rot_speed"]
            if leaf["y"] > 130.0:
                leaf["y"] = random.uniform(-15.0, -5.0)
                leaf["x"] = random.uniform(20.0, 95.0)

        for flake in self._winter_snowflakes:
            flake["y"] += flake["speed_y"]
            flake["x"] += math.sin(flake["sway_phase"]) * 0.15
            flake["sway_phase"] += flake["sway_freq"]
            if flake["y"] > 128.0:
                flake["y"] = random.uniform(-10.0, -2.0)
                flake["x"] = random.uniform(15.0, 105.0)

    def _paint_spring_atmosphere(self, painter: QPainter, cx: float, cy: float, is_night: bool):
        painter.save()
        painter.translate(cx - 30.0, cy + 18.0)
        
        branch_path = QPainterPath()
        branch_path.moveTo(-10.0, 15.0)
        branch_path.cubicTo(0.0, 5.0, 15.0, -5.0, 32.0, -12.0)
        
        branch_color = QColor(16, 185, 129, 65 if not is_night else 40)
        painter.setPen(QPen(branch_color, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(branch_path)

        leaf_color = QColor(52, 211, 153, 90 if not is_night else 50)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(leaf_color)

        leaf1 = QPainterPath()
        leaf1.moveTo(8.0, 0.0)
        leaf1.quadTo(12.0, -6.0, 17.0, -5.0)
        leaf1.quadTo(13.0, 1.0, 8.0, 0.0)
        painter.drawPath(leaf1)

        leaf2 = QPainterPath()
        leaf2.moveTo(22.0, -8.0)
        leaf2.quadTo(28.0, -13.0, 32.0, -11.0)
        leaf2.quadTo(26.0, -5.0, 22.0, -8.0)
        painter.drawPath(leaf2)
        painter.restore()

        petal_color = QColor(167, 243, 208, 140 if not is_night else 95)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(petal_color)

        for p in self._spring_petals:
            painter.save()
            painter.translate(p["x"], p["y"])
            painter.rotate(p["angle"])
            painter.scale(p["scale"], p["scale"])

            petal_path = QPainterPath()
            petal_path.moveTo(0.0, -3.0)
            petal_path.quadTo(2.2, 0.0, 0.0, 3.0)
            petal_path.quadTo(-2.2, 0.0, 0.0, -3.0)
            painter.drawPath(petal_path)
            painter.restore()

    def _paint_summer_atmosphere(self, painter: QPainter, cx: float, cy: float, is_night: bool):
        if is_night:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(251, 191, 36, 110))
            for s in self._summer_sparks:
                sx = cx + math.cos(s["current_theta"]) * (s["orbit_r"] * 0.75)
                sy = cy + math.sin(s["current_theta"]) * (s["orbit_r"] * 0.75)
                painter.drawEllipse(QPointF(sx, sy), s["size"] * 0.8, s["size"] * 0.8)
            return

        painter.setPen(Qt.PenStyle.NoPen)
        for s in self._summer_sparks:
            alpha = int(100 + math.sin(s["pulse_phase"]) * 45)
            painter.setBrush(QColor(251, 191, 36, alpha))
            sx = cx + math.cos(s["current_theta"]) * s["orbit_r"]
            sy = cy + math.sin(s["current_theta"]) * s["orbit_r"]
            painter.drawEllipse(QPointF(sx, sy), s["size"], s["size"])

    def _paint_autumn_atmosphere(self, painter: QPainter):
        painter.setPen(Qt.PenStyle.NoPen)
        for leaf in self._autumn_leaves:
            painter.save()
            painter.translate(leaf["x"], leaf["y"])
            painter.rotate(leaf["angle"])
            painter.scale(leaf["scale"], leaf["scale"])
            painter.setBrush(leaf["color"])

            leaf_path = QPainterPath()
            leaf_path.moveTo(0.0, -4.5)
            leaf_path.cubicTo(3.2, -2.0, 3.2, 2.0, 0.0, 4.5)
            leaf_path.cubicTo(-3.2, 2.0, -3.2, -2.0, 0.0, -4.5)
            painter.drawPath(leaf_path)

            painter.setPen(QPen(QColor(255, 255, 255, 60), 0.7))
            painter.drawLine(QPointF(0.0, -3.5), QPointF(0.0, 3.5))
            painter.restore()

    def _paint_winter_atmosphere(self, painter: QPainter):
        painter.setPen(Qt.PenStyle.NoPen)
        for flake in self._winter_snowflakes:
            painter.setBrush(QColor(224, 242, 254, flake["alpha"]))
            painter.drawEllipse(QPointF(flake["x"], flake["y"]), flake["r"], flake["r"])

    # =========================================================================
    # ساختار واسط کاربری (UI)
    # =========================================================================
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 14, 20, 14)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # ستون متن خوش‌آمدگویی
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        top_greeting_row = QHBoxLayout()
        top_greeting_row.setSpacing(8)
        top_greeting_row.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.lbl_period = QLabel()
        self.lbl_period.setStyleSheet("""
            font-family: 'Vazirmatn';
            font-size: 14px;
            font-weight: 500;
            color: #94A3B8;
            background: transparent;
            border: none;
        """)
        top_greeting_row.addWidget(self.lbl_period)

        self.lbl_editor = QLabel()
        self.lbl_editor.setStyleSheet("""
            font-family: 'Vazirmatn';
            font-size: 16px;
            font-weight: 800;
            color: #F8FAFC;
            background: transparent;
            border: none;
            letter-spacing: -0.2px;
        """)
        top_greeting_row.addWidget(self.lbl_editor)

        # کپسول وضعیت استاندارد، یکپارچه و مینیمال استودیو
        self.live_badge = QLabel()
        self.live_badge.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 10px;
                font-weight: 700;
                color: #818CF8;
                background-color: rgba(99, 102, 241, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 6px;
                padding: 2px 8px;
            }
        """)
        top_greeting_row.addWidget(self.live_badge)

        top_greeting_row.addStretch()
        text_col.addLayout(top_greeting_row)

        text_col.addSpacing(10)

        quote_row = QHBoxLayout()
        quote_row.setContentsMargins(0, 0, 0, 0)
        quote_row.setSpacing(8)
        quote_row.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        lbl_q_icon = QLabel("🎬")
        lbl_q_icon.setStyleSheet("font-size: 11px; background: transparent; border: none;")
        quote_row.addWidget(lbl_q_icon)

        self.lbl_quote = QLabel()
        self.lbl_quote.setWordWrap(False)
        self.lbl_quote.setStyleSheet("""
            font-family: 'Vazirmatn';
            font-size: 11.5px;
            color: #8F909D;
            border: none;
            background: transparent;
            font-style: italic;
        """)

        self.opacity_effect = QGraphicsOpacityEffect(self.lbl_quote)
        self.lbl_quote.setGraphicsEffect(self.opacity_effect)
        quote_row.addWidget(self.lbl_quote, stretch=1)

        text_col.addLayout(quote_row)
        layout.addLayout(text_col, stretch=1)

        # جداکننده ظریف وسط
        self.separator = QFrame()
        self.separator.setFixedWidth(1)
        self.separator.setFixedHeight(46)
        self.separator.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 rgba(255, 255, 255, 0.0), 
                stop:0.5 rgba(255, 255, 255, 0.10), 
                stop:1 rgba(255, 255, 255, 0.0));
            border: none;
        """)
        layout.addSpacing(18)
        layout.addWidget(self.separator)
        layout.addSpacing(18)

        # پنل ساعت و تایم‌کد
        time_pod = QFrame()
        time_pod.setFixedWidth(175)
        time_pod.setStyleSheet("""
            QFrame {
                background: rgba(18, 24, 38, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
            QFrame:hover {
                border-color: rgba(99, 102, 241, 0.35);
                background: rgba(22, 31, 48, 0.85);
            }
        """)
        time_pod.setMouseTracking(True)

        time_col = QVBoxLayout(time_pod)
        time_col.setContentsMargins(10, 8, 10, 8)
        time_col.setSpacing(3)
        time_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top_meta = QHBoxLayout()
        top_meta.setContentsMargins(0, 0, 0, 0)
        top_meta.setSpacing(4)
        top_meta.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dot_rec = QLabel("●")
        dot_rec.setStyleSheet("color: #EF4444; font-size: 7px; background: transparent; border: none;")
        top_meta.addWidget(dot_rec)

        lbl_tc = QLabel("TIMECODE • 25 FPS")
        lbl_tc.setStyleSheet("""
            font-family: 'Segoe UI', sans-serif;
            font-size: 7.5px;
            font-weight: 800;
            color: #818CF8;
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        """)
        top_meta.addWidget(lbl_tc)
        time_col.addLayout(top_meta)

        self.timecode_widget = StudioTimecodeWidget(time_pod)
        time_col.addWidget(self.timecode_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lbl_date = QLabel()
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date.setStyleSheet("""
            font-family: 'Vazirmatn';
            font-size: 9px;
            color: #64748B;
            font-weight: 500;
            border: none;
            background: transparent;
        """)
        time_col.addWidget(self.lbl_date)

        layout.addWidget(time_pod)

    # =========================================================================
    # موتور نقاشی (PaintEvent)
    # =========================================================================
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w, h = float(self.width()), float(self.height())
        rect = QRectF(0, 0, w, h)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.setClipPath(path)

        hour = datetime.now().hour
        is_night = (hour < 5 or hour >= 21)

        # گرادیان استاندارد استودیویی با ته‌مایه فصلی
        gradient = QLinearGradient(0, 0, w, h)
        if self.current_season == "spring":
            gradient.setColorAt(0.0, QColor("#101726"))
            gradient.setColorAt(0.5, QColor("#121F2B"))
            gradient.setColorAt(1.0, QColor("#0E1422"))
            season_glow_color = QColor(16, 185, 129, 20)
        elif self.current_season == "summer":
            gradient.setColorAt(0.0, QColor("#101726"))
            gradient.setColorAt(0.5, QColor("#142033"))
            gradient.setColorAt(1.0, QColor("#0E1422"))
            season_glow_color = QColor(56, 189, 248, 18)
        elif self.current_season == "autumn":
            gradient.setColorAt(0.0, QColor("#121624"))
            gradient.setColorAt(0.5, QColor("#1A1B29"))
            gradient.setColorAt(1.0, QColor("#0F1320"))
            season_glow_color = QColor(245, 158, 11, 18)
        else:  # winter
            gradient.setColorAt(0.0, QColor("#0E1422"))
            gradient.setColorAt(0.5, QColor("#11192A"))
            gradient.setColorAt(1.0, QColor("#0B101C"))
            season_glow_color = QColor(147, 197, 253, 16)

        painter.fillRect(rect, gradient)

        # هاله محیطی نرم
        glow = QRadialGradient(w * 0.25, h * 0.5, w * 0.45)
        glow.setColorAt(0.0, season_glow_color)
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, glow)

        # ── رندر لایه آسمان بر مبنای ساعت ──
        cx, cy = 56.0, h * 0.5
        painter.save()
        painter.translate(cx, cy)

        if 5 <= hour < 17:
            pen_sun = QPen(QColor(248, 250, 252, 180), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_sun)
            painter.setBrush(QColor(255, 255, 255, 25))
            painter.drawEllipse(QRectF(-26, -26, 52, 52))

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.rotate(self.rotation_angle)
            pen_ray = QPen(QColor(248, 250, 252, 120), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_ray)
            for angle in range(0, 360, 45):
                painter.save()
                painter.rotate(angle)
                painter.drawLine(QPointF(0, -32), QPointF(0, -42))
                painter.restore()

        elif 17 <= hour < 21:
            pen_horizon = QPen(QColor(248, 250, 252, 170), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_horizon)
            painter.setBrush(QColor(255, 255, 255, 25))
            painter.drawEllipse(QRectF(-28, -28, 56, 56))

            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(-60, 0), QPointF(60, 0))

        else:
            pen_moon = QPen(QColor(248, 250, 252, 180), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_moon)
            moon_full = QPainterPath()
            moon_full.addEllipse(QRectF(-24, -24, 48, 48))
            moon_cut = QPainterPath()
            moon_cut.addEllipse(QRectF(-6, -30, 42, 42))
            painter.setBrush(QColor(255, 255, 255, 20))
            painter.drawPath(moon_full.subtracted(moon_cut))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(248, 250, 252, 140))
            painter.drawEllipse(QPointF(-36, -14), 1.5, 1.5)
            painter.drawEllipse(QPointF(32, -18), 1.2, 1.2)
            painter.drawEllipse(QPointF(40, 12), 1.4, 1.4)

        painter.restore()

        # ── رندر لایه فصلی متحرک ──
        if self.current_season == "spring":
            self._paint_spring_atmosphere(painter, cx, cy, is_night)
        elif self.current_season == "summer":
            self._paint_summer_atmosphere(painter, cx, cy, is_night)
        elif self.current_season == "autumn":
            self._paint_autumn_atmosphere(painter)
        else:
            self._paint_winter_atmosphere(painter)

        # خط مرزی دور کارت
        painter.setClipping(False)
        painter.setPen(QPen(QColor(255, 255, 255, 14), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), 12, 12)
        painter.end()

    # =========================================================================
    # تایمرها و منطق به‌روزرسانی
    # =========================================================================
    def _setup_timer(self):
        self.timer_clock = QTimer(self)
        self.timer_clock.timeout.connect(self._tick)
        self.timer_clock.start(1000)

        self.timer_anim = QTimer(self)
        self.timer_anim.timeout.connect(self._tick_anim)
        self.timer_anim.start(50)

    def _tick(self):
        now = datetime.now()
        now_time = QTime.currentTime().toString("HH:mm:ss")
        self.timecode_widget.set_time_string(now_time, animated=True)

        greeting_text, mood_tag = self._get_time_greeting(now.hour)
        current_greeting_key = f"{greeting_text}_{now.hour}_{self.current_season}"
        if current_greeting_key != self._last_greeting_key:
            self._last_greeting_key = current_greeting_key
            self._refresh_greeting_text()

        today_key = (now.year, now.month, now.day)
        if today_key != self._last_day_key:
            self._last_day_key = today_key
            today_j = jdatetime.date.today()
            self.lbl_date.setText(get_persian_date_readable(today_j))
            new_season = self._get_current_season()
            if new_season != self.current_season:
                self.current_season = new_season

    def _tick_anim(self):
        self.rotation_angle += 0.3
        if self.rotation_angle >= 360.0:
            self.rotation_angle -= 360.0

        self._update_season_animation()
        self.update()

    def _get_time_greeting(self, hour: int = None) -> tuple[str, str]:
        if hour is None:
            hour = datetime.now().hour

        if 5 <= hour < 11:
            return "صبح بخیر،", "شیفت صبحگاهی"
        elif 11 <= hour < 17:
            return "ظهر بخیر،", "تمرکز روی تایم‌لاین"
        elif 17 <= hour < 21:
            return "عصر بخیر،", "ساعات اوج تدوین"
        else:
            return "شب بخیر،", "شیفت شب استودیو"

    def _refresh_greeting_text(self):
        settings = SettingsManager.load_settings()
        editor_name = settings.get("editor_name") or "تدوین‌گر گرامی"
        greeting_period, mood_tag = self._get_time_greeting()

        self.lbl_period.setText(greeting_period)
        self.lbl_editor.setText(f"{editor_name} 👋")

        season_icons = {
            "spring": "🌱",
            "summer": "☀️",
            "autumn": "🍂",
            "winter": "❄️"
        }
        s_icon = season_icons.get(self.current_season, "🎬")
        self.live_badge.setText(f"● {mood_tag} {s_icon}")

    def update_all(self):
        now = datetime.now()
        today_j = jdatetime.date.today()
        self._last_day_key = (now.year, now.month, now.day)

        self.current_season = self._get_current_season()

        greeting_period, mood_tag = self._get_time_greeting(now.hour)
        self._last_greeting_key = f"{greeting_period}_{now.hour}_{self.current_season}"

        self._refresh_greeting_text()

        self.current_quote_idx = (today_j.day - 1) % len(EDITING_QUOTES)
        self.lbl_quote.setText(f"« {EDITING_QUOTES[self.current_quote_idx]} »")
        self.opacity_effect.setOpacity(1.0)

        self.lbl_date.setText(get_persian_date_readable(today_j))

        now_time = QTime.currentTime().toString("HH:mm:ss")
        self.timecode_widget.set_time_string(now_time, animated=False)
        self.update()