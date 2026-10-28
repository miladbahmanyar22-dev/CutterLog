# ==================================================
# FILE: widgets/dashboard_welcome_header.py
# ==================================================
from pathlib import Path
from datetime import datetime
import jdatetime
from typing import Optional
import math

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, 
    QWidget, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QTimer, QRectF, QPointF
)
from PySide6.QtGui import (
    QPainter, QPainterPath, QColor, QLinearGradient, QRadialGradient, 
    QBrush, QPen, QFont, QPixmap
)

from core.settings_manager import SettingsManager
from core.project_controller import ProjectController
from core.persian_utils import to_persian_numbers, get_persian_date_readable
from core.signals import global_signals
from time_tracking.timer_engine import TimeTrackingEngine


class AmbientPulseClockWidget(QFrame):
    """
    ویجت ساعت استودیویی با تابش اتمسفریک و طبیعی خورشید (Organic Sun Haze)
    بدون خطوط تیز هندسی و با فید نرم در پس‌زمینه.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(264, 84)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        self.hour_str = "12"
        self.min_str = "00"
        self.sec_str = "00"
        self.work_ratio = 0.0

        self._glow_phase = 0.0
        self._drift_phase = 0.0

        self.setObjectName("AmbientClockCard")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("QFrame#AmbientClockCard { background: transparent; border: none; }")

        self._png_pixmap: Optional[QPixmap] = None
        self._load_png_asset()

        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(40)
        self._glow_timer.timeout.connect(self._advance_animation)
        self._glow_timer.start()

    def _load_png_asset(self):
        """بارگذاری فایل PNG در اندازه اصلی"""
        base_dir = Path(__file__).resolve().parent.parent
        possible_paths = [
            base_dir / "assets" / "images" / "persepolis_sketch.png",
            Path("assets/images/persepolis_sketch.png"),
        ]
        for p in possible_paths:
            if p.exists():
                pix = QPixmap(str(p))
                if not pix.isNull():
                    self._png_pixmap = pix
                    break

    def _advance_animation(self):
        self._glow_phase = (self._glow_phase + 0.022) % (2.0 * math.pi)
        self._drift_phase = (self._drift_phase + 0.012) % (2.0 * math.pi)
        self.update()

    def update_clock_data(self, now: datetime, ratio: float):
        self.hour_str = f"{now.hour:02d}"
        self.min_str = f"{now.minute:02d}"
        self.sec_str = f"{now.second:02d}"
        self.work_ratio = max(0.0, min(1.0, ratio))
        self.update()

    def _render_natural_sun_haze(self, painter: QPainter, origin: QPointF, pulse: float, clip_path: QPainterPath):
        """رسم تابش طبیعی، مه‌آلود و سینمایی بدون خطوط تیز هندسی"""
        painter.save()
        painter.setClipPath(clip_path)

        # ۱. مخروط نور مورب نرم (Soft Atmospheric Sun Beam)
        beam_target = QPointF(origin.x() - 95.0, origin.y() + 75.0)
        beam_grad = QLinearGradient(origin, beam_target)
        beam_alpha = int(32 + 18 * pulse)
        beam_grad.setColorAt(0.0, QColor(245, 225, 255, beam_alpha))
        beam_grad.setColorAt(0.35, QColor(190, 140, 255, int(beam_alpha * 0.7)))
        beam_grad.setColorAt(0.70, QColor(130, 80, 220, int(beam_alpha * 0.3)))
        beam_grad.setColorAt(1.0, QColor(25, 12, 45, 0))

        painter.setBrush(QBrush(beam_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        # زاویه شیب پرتو نوری عریض و فید شده
        painter.drawPolygon([
            QPointF(origin.x() - 15.0, origin.y()),
            QPointF(origin.x() + 25.0, origin.y()),
            QPointF(origin.x() - 30.0, origin.y() + 85.0),
            QPointF(origin.x() - 150.0, origin.y() + 85.0)
        ])

        # ۲. هاله دوم مایل به سمت راست (Secondary Soft Scattering)
        beam_right = QLinearGradient(origin, QPointF(origin.x() + 65.0, origin.y() + 80.0))
        sub_alpha = int(20 + 12 * pulse)
        beam_right.setColorAt(0.0, QColor(230, 205, 255, sub_alpha))
        beam_right.setColorAt(0.40, QColor(175, 125, 245, int(sub_alpha * 0.6)))
        beam_right.setColorAt(1.0, QColor(20, 10, 40, 0))

        painter.setBrush(QBrush(beam_right))
        painter.drawPolygon([
            QPointF(origin.x() - 5.0, origin.y()),
            QPointF(origin.x() + 25.0, origin.y()),
            QPointF(origin.x() + 85.0, origin.y() + 85.0),
            QPointF(origin.x() + 25.0, origin.y() + 85.0)
        ])

        # ۳. درخشش کروی خورشید و مه‌آلودگی پیرامون (Sun Corona)
        corona = QRadialGradient(origin, 70.0)
        corona.setColorAt(0.0, QColor(255, 245, 255, int(110 + 35 * pulse)))
        corona.setColorAt(0.25, QColor(215, 175, 255, int(65 + 20 * pulse)))
        corona.setColorAt(0.60, QColor(145, 90, 230, int(22 + 10 * pulse)))
        corona.setColorAt(1.0, QColor(18, 12, 30, 0))

        painter.setBrush(QBrush(corona))
        painter.drawEllipse(origin, 70.0, 70.0)

        # ۴. هسته گرم و متمرکز خورشید
        core = QRadialGradient(origin, 14.0)
        core.setColorAt(0.0, QColor(255, 255, 255, int(195 + 40 * pulse)))
        core.setColorAt(0.4, QColor(240, 215, 255, int(140 + 30 * pulse)))
        core.setColorAt(1.0, QColor(180, 120, 255, 0))

        painter.setBrush(QBrush(core))
        painter.drawEllipse(origin, 14.0, 14.0)

        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        w, h = float(self.width()), float(self.height())
        card = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        pulse = (math.sin(self._glow_phase) + 1.0) / 2.0

        clip_path = QPainterPath()
        clip_path.addRoundedRect(card, 16.0, 16.0)

        # ۱. پس‌زمینه کارت شیشه‌ای با عمق تیره
        base = QLinearGradient(0, 0, w, h)
        base.setColorAt(0.0, QColor(22, 19, 36, 252))
        base.setColorAt(0.5, QColor(15, 13, 24, 252))
        base.setColorAt(1.0, QColor(10, 9, 18, 254))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(base))
        painter.drawRoundedRect(card, 16, 16)

        # ۲. موقعیت کانون خورشید (شناوری ارگانیک و آرام)
        drift_x = math.cos(self._drift_phase) * 5.0
        drift_y = math.sin(self._drift_phase * 0.8) * 2.5
        sun_origin = QPointF(w * 0.77 + drift_x, 10.0 + drift_y)

        # ۳. رسم تابش مه و نور طبیعی خورشید
        self._render_natural_sun_haze(painter, sun_origin, pulse, clip_path)

        # ۴. رسم تصویر اسکچ تخت جمشید در اندازه اصلی روی تابش خورشید
        sep_x = 80.0
        if self._png_pixmap and not self._png_pixmap.isNull():
            painter.save()
            painter.setClipPath(clip_path)
            painter.setOpacity(0.54 + 0.08 * pulse)
            draw_x = int(w - self._png_pixmap.width())
            draw_y = int(h - self._png_pixmap.height())
            painter.drawPixmap(draw_x, draw_y, self._png_pixmap)
            painter.restore()

        # کادر خارجی ویجت
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(150, 115, 245, int(65 + 25 * pulse)), 1.2))
        painter.drawRoundedRect(card, 16, 16)

        # =====================================================================
        # ۵. ستون سمت چپ: رینگ دایره‌ای + آیکون ساعت محو + عدد درصد
        # =====================================================================
        ring_center = QPointF(42.0, h * 0.5)
        ring_radius = 24.0
        ring_rect = QRectF(
            ring_center.x() - ring_radius, 
            ring_center.y() - ring_radius, 
            ring_radius * 2, 
            ring_radius * 2
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(36, 28, 58, 220))
        painter.drawEllipse(ring_center, 19.5, 19.5)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(255, 255, 255, 18), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawEllipse(ring_rect)

        if self.work_ratio > 0.0:
            ring_grad = QLinearGradient(ring_rect.left(), ring_rect.top(), ring_rect.right(), ring_rect.bottom())
            ring_grad.setColorAt(0.0, QColor(147, 98, 255, 250))
            ring_grad.setColorAt(1.0, QColor(216, 180, 254, 255))
            painter.setPen(QPen(QBrush(ring_grad), 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            span_angle = int(-self.work_ratio * 360 * 16)
            painter.drawArc(ring_rect, 90 * 16, span_angle)

        icon_radius = 12.0
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(165, 140, 240, 50), 1.6))
        painter.drawEllipse(ring_center, icon_radius, icon_radius)
        painter.setPen(QPen(QColor(165, 140, 240, 60), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(ring_center, QPointF(ring_center.x(), ring_center.y() - 6.5))
        painter.drawLine(ring_center, QPointF(ring_center.x() + 5.0, ring_center.y()))

        pct_int = int(self.work_ratio * 100)
        pct_font = QFont("Segoe UI Variable Display", 11, QFont.Weight.Bold)
        pct_font.setStyleHint(QFont.StyleHint.SansSerif)
        painter.setFont(pct_font)
        painter.setPen(QColor(255, 255, 255, 255))
        painter.drawText(
            QRectF(ring_center.x() - 18.0, ring_center.y() - 14.0, 36.0, 28.0),
            Qt.AlignmentFlag.AlignCenter,
            f"{pct_int}"
        )

        # خط جداکننده محو عمودی
        sep_grad = QLinearGradient(sep_x, 16.0, sep_x, 68.0)
        sep_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
        sep_grad.setColorAt(0.5, QColor(255, 255, 255, 22))
        sep_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setPen(QPen(QBrush(sep_grad), 1.0))
        painter.drawLine(QPointF(sep_x, 16.0), QPointF(sep_x, 68.0))

        # =====================================================================
        # ۶. ستون سمت راست: ارقام زمان وسط‌چین و قفل‌شده
        # =====================================================================
        zone_left = sep_x
        zone_right = w - 10.0
        zone_w = zone_right - zone_left
        zone_h = h

        main_font = QFont("Segoe UI Variable Display", 29, QFont.Weight.Bold)
        main_font.setStyleHint(QFont.StyleHint.SansSerif)
        main_font.setKerning(False)
        main_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)

        sec_font = QFont("Segoe UI Variable Display", 14, QFont.Weight.DemiBold)
        sec_font.setStyleHint(QFont.StyleHint.SansSerif)
        sec_font.setKerning(False)

        fixed_time_w = 90.0
        fixed_sec_w = 22.0
        gap = 5.0
        total_block_w = fixed_time_w + gap + fixed_sec_w

        block_start_x = zone_left + (zone_w - total_block_w) / 2.0
        time_box_h = 44.0
        block_start_y = ((zone_h - time_box_h) / 2.0) - 3.5

        time_rect = QRectF(block_start_x, block_start_y, fixed_time_w, time_box_h)
        sec_rect = QRectF(block_start_x + fixed_time_w + gap, block_start_y + 3.0, fixed_sec_w, time_box_h)

        # سایه تیره عمیق زیر ارقام جهت ایجاد کنتراست
        painter.setFont(main_font)
        painter.setPen(QColor(6, 5, 12, 240))
        painter.drawText(time_rect.translated(0, 1.8), Qt.AlignmentFlag.AlignCenter, f"{self.hour_str}:{self.min_str}")

        painter.setPen(QColor(255, 255, 255, 255))
        painter.drawText(time_rect, Qt.AlignmentFlag.AlignCenter, f"{self.hour_str}:{self.min_str}")

        # رسم ثانیه‌شمار قفل‌شده
        painter.setFont(sec_font)
        painter.setPen(QColor(205, 180, 255, 255))
        painter.drawText(sec_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.sec_str)

        painter.end()


class DashboardWelcomeHeader(QFrame):
    """
    هدر پیشخوان استودیویی مدرن:
    - پنل سمت راست: خوش‌آمدگویی رسمی، تاریخ تقویم شمسی و نزدیک‌ترین موعد تحویل ددلاین
    - پنل سمت چپ: ساعت مینیمال نئونی با رینگ پیشرفت و وکتور PNG پس‌زمینه
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
        layout.setContentsMargins(24, 10, 20, 10)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # پنل راست: اطلاعات و تایپوگرافی
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

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

        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setFixedHeight(54)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        layout.addWidget(divider)

        # پنل چپ: ویجت ساعت با رینگ پیشرفت
        self.clock_widget = AmbientPulseClockWidget(self)
        layout.addWidget(self.clock_widget)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            w = float(self.width())
            h = float(self.height())
            rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)

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

        self.clock_widget.update_clock_data(now, ratio)

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