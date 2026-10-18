# ==================================================
# FILE: widgets/project_card.py
# ==================================================
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QSize, QTimer, QVariantAnimation, QEasingCurve, Signal, QRectF, QPointF
)
from PySide6.QtGui import (
    QColor, QPainter, QLinearGradient, QRadialGradient, QBrush, QPen, QFont, QFontMetrics
)

from config import open_path_in_os
from core.persian_utils import (
    format_toman, gregorian_to_jalali, to_persian_numbers, clean_studio_display_name
)
from core.project_controller import ProjectController
from core.finance_controller import FinanceController
from core.settings_manager import SettingsManager
from core.nle_messenger_helper import NleLauncherHelper
from widgets.base_card import BaseProjectCard
from widgets.status_badge import StatusPillBadge, StatusType
from widgets.project_details_dialog import ProjectDetailsDialog
from widgets.edit_project_dialog import EditProjectDialog
from widgets.new_transaction_dialog import NewTransactionDialog
from widgets.project_timeline import NewRevisionDialog
from widgets.dynamic_clip_bar import DynamicClipOverviewBar
from widgets.studio_share_dialog import StudioShareDialog
from widgets.quick_messenger_popup import QuickMessengerMiniPopup
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog
from widgets.studio_menu import StudioMenu
from core.signals import global_signals
from core.icon_provider import IconProvider


def interpolate_color(c1: QColor, c2: QColor, factor: float) -> QColor:
    """درونیابی خطی پیوسته بین دو رنگ برای ترنزیشن نرم و سینمایی"""
    f = max(0.0, min(1.0, factor))
    r = int(c1.red() + (c2.red() - c1.red()) * f)
    g = int(c1.green() + (c2.green() - c1.green()) * f)
    b = int(c1.blue() + (c2.blue() - c1.blue()) * f)
    a = int(c1.alpha() + (c2.alpha() - c1.alpha()) * f)
    return QColor(r, g, b, a)


def get_persian_nle_name(file_path: str) -> str:
    """تشخیص نرم‌افزار تدوین و بازگردانی نام ۱۰۰٪ فارسی"""
    if not file_path:
        return "پروژه تدوین"
    p = Path(file_path)
    ext = p.suffix.replace(".", "").upper()
    nle_names = {
        "PRPROJ": "پریمیر",
        "DRP": "داوینچی",
        "AEP": "افتر افکت",
        "FCPXML": "فاینال کات",
        "XML": "تایم‌لاین XML",
        "EDL": "فایل EDL",
        "PSD": "فتوشاپ",
        "SESX": "آدیشن",
        "CPR": "کیوبیس"
    }
    return nle_names.get(ext, f"پروژه {ext}")


class AutoArchiveCountdownBadge(QWidget):
    """
    بج تایمر معکوس ماژولار استودیویی:
    - کپسول زمان‌سنج (HH:MM:SS) در سمت راست
    - کپسول روز در سمت چپ تایمر با عدد و کلمه روز کاملاً وسط‌چین
    - ارتفاع دقیقاً ۲۴ پیکسل و هم‌راستا با سایر بج‌های هدر
    """
    expired = Signal(int)

    def __init__(self, project_id: int, delivered_at: datetime, limit_days: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.delivered_at = delivered_at
        self.limit_days = limit_days
        self.total_limit_seconds = max(1, limit_days * 86400)

        self.days_str = "۰"
        self.time_str = "۰۰:۰۰:۰۰"
        self.has_days = False
        self.current_ratio = 1.0

        self.current_color = QColor("#10B981")
        self.target_color = QColor("#10B981")
        self.anim: Optional[QVariantAnimation] = None

        self.setFixedHeight(24)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Fixed)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self._on_tick)
        self.tick_timer.start()

        self._on_tick()

    def _calculate_remaining_seconds(self) -> int:
        now = datetime.utcnow()
        deadline = self.delivered_at + timedelta(days=self.limit_days)
        remaining = int((deadline - now).total_seconds())
        return max(0, remaining)

    def _on_tick(self):
        rem_sec = self._calculate_remaining_seconds()

        if rem_sec <= 0:
            self.tick_timer.stop()
            self.time_str = "انتقال به آرشیو"
            self.has_days = False
            self.current_ratio = 0.0
            self.current_color = QColor("#EF4444")
            self.updateGeometry()
            self.update()
            self.expired.emit(self.project_id)
            return

        days = rem_sec // 86400
        hours = (rem_sec % 86400) // 3600
        minutes = (rem_sec % 3600) // 60
        seconds = rem_sec % 60

        prev_has_days = self.has_days
        self.has_days = (days > 0)
        self.days_str = to_persian_numbers(str(days))
        self.time_str = to_persian_numbers(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        self.current_ratio = min(1.0, max(0.0, rem_sec / self.total_limit_seconds))

        if prev_has_days != self.has_days:
            self.updateGeometry()

        if self.current_ratio > 0.5:
            factor = (1.0 - self.current_ratio) * 2.0
            new_target = interpolate_color(QColor("#10B981"), QColor("#F59E0B"), factor)
        else:
            factor = (0.5 - self.current_ratio) * 2.0
            new_target = interpolate_color(QColor("#F59E0B"), QColor("#EF4444"), factor)

        if new_target.name() != self.target_color.name():
            self._animate_color_transition(new_target)
        else:
            self.update()

    def _animate_color_transition(self, target: QColor):
        if self.anim and self.anim.state() == QVariantAnimation.State.Running:
            self.anim.stop()

        start_c = QColor(self.current_color)
        self.target_color = target

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(1200)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)

        def _step(val: float):
            self.current_color = interpolate_color(start_c, target, float(val))
            self.update()

        self.anim.valueChanged.connect(_step)
        self.anim.start()

    def sizeHint(self) -> QSize:
        font_time = QFont("Segoe UI", 8, QFont.Weight.Bold)
        fm_time = QFontMetrics(font_time)
        time_w = max(66.0, float(fm_time.horizontalAdvance(self.time_str)) + 12.0)

        if self.has_days:
            font_num = QFont("Segoe UI", 8, QFont.Weight.Bold)
            font_word = QFont("Vazirmatn", 7, QFont.Weight.Bold)
            fm_num = QFontMetrics(font_num)
            fm_word = QFontMetrics(font_word)
            num_w = fm_num.horizontalAdvance(self.days_str)
            word_w = fm_word.horizontalAdvance("روز")
            inner_gap = 5.0
            day_w = max(26.0, float(num_w) + float(word_w) + inner_gap + 10.0)
            return QSize(int(time_w + day_w + 4.0), 24)
        return QSize(int(time_w), 24)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        c = self.current_color
        r, g, b = c.red(), c.green(), c.blue()

        h = float(self.height())
        capsule_h = h - 1.0
        capsule_y = 0.5

        if self.has_days:
            spacing = 4.0

            font_num = QFont("Segoe UI", 8, QFont.Weight.Bold)
            font_word = QFont("Vazirmatn", 7, QFont.Weight.Bold)
            fm_num = QFontMetrics(font_num)
            fm_word = QFontMetrics(font_word)

            num_w = float(fm_num.horizontalAdvance(self.days_str))
            word_w = float(fm_word.horizontalAdvance("روز"))
            inner_gap = 5.0

            day_w = max(26.0, num_w + word_w + inner_gap + 10.0)
            time_w = float(self.width()) - day_w - spacing - 1.0

            # ۱. کپسول ساعت (سمت راست: از x = 0.5)
            time_x = 0.5
            time_rect = QRectF(time_x, capsule_y, time_w, capsule_h)

            bg_grad_time = QLinearGradient(0, 0, 0, capsule_h)
            bg_grad_time.setColorAt(0.0, QColor(16, 22, 34, 235))
            bg_grad_time.setColorAt(1.0, QColor(8, 12, 20, 250))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_grad_time))
            painter.drawRoundedRect(time_rect, 6, 6)

            glow = QRadialGradient(QPointF(time_x + time_w * 0.85, capsule_h * 0.5), time_w * 0.5)
            glow.setColorAt(0.0, QColor(r, g, b, 26))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(glow))
            painter.drawRoundedRect(time_rect, 6, 6)

            rail_w = max(4.0, (time_w - 12.0) * self.current_ratio)
            rail_rect = QRectF(time_x + 6.0, capsule_h - 1.8, rail_w, 1.2)
            rail_grad = QLinearGradient(time_x + 6.0, 0, time_x + 6.0 + rail_w, 0)
            rail_grad.setColorAt(0.0, QColor(r, g, b, 50))
            rail_grad.setColorAt(1.0, QColor(r, g, b, 230))
            painter.setBrush(QBrush(rail_grad))
            painter.drawRoundedRect(rail_rect, 0.6, 0.6)

            border_time = QPen(QColor(r, g, b, 80), 1.0)
            painter.setPen(border_time)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(time_rect, 6, 6)

            font_time = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(font_time)
            painter.setPen(QColor(r, g, b))
            text_r = QRectF(time_x + 3.0, 0.0, time_w - 6.0, capsule_h)
            painter.drawText(text_r, Qt.AlignmentFlag.AlignCenter, self.time_str)

            # ۲. کپسول روز (سمت چپ تایمر - محتوا کاملاً در مرکز کپسول)
            day_x = time_x + time_w + spacing
            day_rect = QRectF(day_x, capsule_y, day_w, capsule_h)

            bg_grad_day = QLinearGradient(0, 0, 0, capsule_h)
            bg_grad_day.setColorAt(0.0, QColor(16, 22, 34, 235))
            bg_grad_day.setColorAt(1.0, QColor(8, 12, 20, 250))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_grad_day))
            painter.drawRoundedRect(day_rect, 6, 6)

            border_day = QPen(QColor(r, g, b, 80), 1.0)
            painter.setPen(border_day)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(day_rect, 6, 6)

            # محاسبه مرکزچین کردن کل بلاک (کلمه روز چرخیده + فاصله + عدد)
            block_total_w = word_w + inner_gap + num_w
            block_start_x = day_x + (day_w - block_total_w) / 2.0

            # کلمه «روز» چرخیده ۹۰ درجه در ابتدای بلاک (سمت راست در مختصات افقی)
            painter.save()
            pivot_x = block_start_x + (word_w / 2.0)
            pivot_y = capsule_y + (capsule_h / 2.0)
            painter.translate(pivot_x, pivot_y)
            painter.rotate(-90)
            painter.setFont(font_word)
            painter.setPen(QColor(r, g, b))
            painter.drawText(QRectF(-capsule_h / 2.0, -5.0, capsule_h, 10.0), Qt.AlignmentFlag.AlignCenter, "روز")
            painter.restore()

            # عدد روز دقیقاً چسبیده در ادامه کلمه روز
            num_x = block_start_x + word_w + inner_gap
            rect_day_num = QRectF(num_x, capsule_y, num_w, capsule_h)
            painter.setFont(font_num)
            painter.setPen(QColor(r, g, b))
            painter.drawText(rect_day_num, Qt.AlignmentFlag.AlignCenter, self.days_str)

        else:
            time_x = 0.5
            time_w = float(self.width()) - 1.0
            time_rect = QRectF(time_x, capsule_y, time_w, capsule_h)

            bg_grad_time = QLinearGradient(0, 0, 0, capsule_h)
            bg_grad_time.setColorAt(0.0, QColor(16, 22, 34, 235))
            bg_grad_time.setColorAt(1.0, QColor(8, 12, 20, 250))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_grad_time))
            painter.drawRoundedRect(time_rect, 6, 6)

            glow = QRadialGradient(QPointF(time_x + time_w * 0.85, capsule_h * 0.5), time_w * 0.5)
            glow.setColorAt(0.0, QColor(r, g, b, 26))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(QBrush(glow))
            painter.drawRoundedRect(time_rect, 6, 6)

            rail_w = max(4.0, (time_w - 12.0) * self.current_ratio)
            rail_rect = QRectF(time_x + 6.0, capsule_h - 1.8, rail_w, 1.2)
            rail_grad = QLinearGradient(time_x + 6.0, 0, time_x + 6.0 + rail_w, 0)
            rail_grad.setColorAt(0.0, QColor(r, g, b, 50))
            rail_grad.setColorAt(1.0, QColor(r, g, b, 230))
            painter.setBrush(QBrush(rail_grad))
            painter.drawRoundedRect(rail_rect, 0.6, 0.6)

            border_time = QPen(QColor(r, g, b, 80), 1.0)
            painter.setPen(border_time)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(time_rect, 6, 6)

            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor(r, g, b))
            text_r = QRectF(time_x + 4.0, 0.0, time_w - 8.0, capsule_h)
            painter.drawText(text_r, Qt.AlignmentFlag.AlignCenter, self.time_str)

        painter.end()

    def closeEvent(self, event):
        self.tick_timer.stop()
        super().closeEvent(event)


class ArchiveConfirmDialog(StudioBaseDialog):
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setFixedWidth(450)
        self.init_ui()

    def init_ui(self):
        project = ProjectController.get_project_by_id(self.project_id)
        fin = ProjectController.get_project_financial_summary(project)

        self.build_header("انتقال پرونده به آرشیو", "مختومه‌سازی و بایگانی پروژه نهایی", icon_name="archive", icon_color="#10B981")

        desc_card = QFrame()
        desc_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;")
        card_lay = QVBoxLayout(desc_card)
        card_lay.setContentsMargins(14, 12, 14, 12)
        card_lay.setSpacing(6)

        lbl_proj = QLabel(f"پروژه: <b style='color:#F8FAFC;'>{project.couple_names}</b>")
        lbl_proj.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8;")
        card_lay.addWidget(lbl_proj)

        lbl_status = QLabel("وضعیت تدوین: <b style='color:#10B981;'>کلیپ‌ها تکمیل و تحویل داده شده ✓</b>")
        lbl_status.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8;")
        card_lay.addWidget(lbl_status)

        lbl_fin = QLabel(f"وضعیت حساب: <b style='color:{fin['status_color']};'>{fin['status_label']}</b>")
        lbl_fin.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8;")
        card_lay.addWidget(lbl_fin)
        self.container_layout.addWidget(desc_card)

        note = QLabel("توجه: پرونده به بخش آرشیو منتقل می‌شود اما پیگیری مطالبات مالی و ثبت اصلاحیه همچنان فعال خواهد بود.")
        note.setWordWrap(True)
        note.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B;")
        self.container_layout.addWidget(note)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_confirm = QPushButton("تأیید و انتقال به آرشیو")
        btn_confirm.setFixedHeight(36)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_confirm.clicked.connect(self._confirm)
        btn_box.addWidget(btn_confirm, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _confirm(self):
        ProjectController.archive_project(self.project_id)
        self.accept()


class ProjectCard(BaseProjectCard):
    def __init__(self, project_data: dict, parent=None):
        project_id = project_data.get("id", 0)
        project_number = project_data.get("project_number", 1)
        
        super().__init__(
            project_id=project_id,
            project_number=project_number,
            parent=parent,
            accent_color="#818CF8",
            card_type="project"
        )
        self.project = project_data
        self.is_overdue = False
        self.setFixedHeight(236)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.init_card_content()

    def _apply_base_styles(self):
        self._apply_card_theme()

    def _apply_card_theme(self):
        if self.is_overdue:
            self.setStyleSheet("""
                QFrame#BaseCardFrame {
                    background-color: #14111E;
                    border: 1.5px solid rgba(239, 68, 68, 0.40);
                    border-radius: 12px;
                }
                QFrame#BaseCardFrame:hover {
                    border-color: #EF4444;
                    background-color: #181324;
                }
            """)
        else:
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

    def init_card_content(self):
        active_rev = self.project.get("active_revision_title")
        prog_val = self.project.get("progress_pct", 0)
        c_cnt = self.project.get("completed_clips", 0)
        t_cnt = self.project.get("total_clips", 0)
        status_info = self.project.get("status_info", {})
        status_key = status_info.get("key", "")

        self.is_overdue = False
        deadline_dt = self.project.get("deadline")
        if deadline_dt:
            now_dt = datetime.utcnow()
            if isinstance(deadline_dt, datetime) and (deadline_dt.date() - now_dt.date()).days < 0 and prog_val < 100:
                self.is_overdue = True

        self._apply_card_theme()

        # وضعیت و بج کپسولی
        if self.is_overdue:
            status_text = "ددلاین گذشته ⚠️"
            status_type = StatusType.DANGER
            status_symbol = "!"
        elif active_rev:
            prog_val = self.project.get("rev_progress_pct", 0)
            status_text = f"اصلاحیه: {to_persian_numbers(prog_val)}٪"
            status_type = StatusType.WARNING
            status_symbol = "●"
        else:
            if status_key == "under_review":
                status_text = "تحویل شد / منتظر بازبینی"
                status_type = StatusType.PENDING
                status_symbol = "⏳"
            elif prog_val >= 100 or (t_cnt > 0 and c_cnt == t_cnt):
                status_text = "آماده تحویل ✓"
                status_type = StatusType.COMPLETED
                status_symbol = "✓"
            elif c_cnt == 0:
                status_text = "در انتظار شروع"
                status_type = StatusType.NEUTRAL
                status_symbol = "○"
            else:
                status_text = f"پیشرفت: {to_persian_numbers(prog_val)}٪"
                status_type = StatusType.ACTIVE
                status_symbol = "●"

        self.status_badge = StatusPillBadge(label=status_text, status_type=status_type, custom_symbol=status_symbol)
        self.header_tags_layout.addWidget(self.status_badge)

        # بج وضعیت مالی
        rem_amount = self.project.get("remaining_amount", 0)
        is_settled = (rem_amount == 0) and (self.project.get("total_fee", 0) > 0)
        
        if is_settled:
            fin_label = "تسویه کامل ✓"
            fin_bg = "rgba(16, 185, 129, 0.16)"
            fin_color = "#34D399"
            fin_border = "rgba(16, 185, 129, 0.35)"
        else:
            fin_label = f"مانده: {format_toman(rem_amount)}"
            fin_bg = "rgba(251, 146, 60, 0.16)"
            fin_color = "#FB923C"
            fin_border = "rgba(251, 146, 60, 0.40)"
        
        badge_fin = QLabel(fin_label)
        badge_fin.setFixedHeight(24)
        badge_fin.setStyleSheet(f"""
            QLabel {{
                font-family: 'Vazirmatn';
                background-color: {fin_bg};
                color: {fin_color};
                border: 1px solid {fin_border};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 800;
            }}
        """)
        self.header_tags_layout.addWidget(badge_fin)

        # ========================================================
        # تایمر معکوس آرشیو خودکار نزدیک به کپسول مالی
        # ========================================================
        settings = SettingsManager.load_settings()
        limit_days = settings.get("auto_archive_delivered_days", 7)
        delivered_dt = None

        p_obj = ProjectController.get_project_by_id(self.project_id)
        if p_obj and p_obj.delivered_at and not p_obj.is_archived and status_key == "under_review" and limit_days > 0 and not active_rev:
            delivered_dt = p_obj.delivered_at

        if delivered_dt:
            self.archive_timer_badge = AutoArchiveCountdownBadge(
                project_id=self.project_id,
                delivered_at=delivered_dt,
                limit_days=limit_days,
                parent=self
            )
            self.archive_timer_badge.expired.connect(self._on_auto_archive_expired)
            self.header_tags_layout.addWidget(self.archive_timer_badge)

        self.header_tags_layout.addStretch()

        btn_more = QPushButton("⋮")
        btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_more.setFixedSize(24, 24)
        btn_more.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8F909D;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #F8FAFC;
                background-color: rgba(255, 255, 255, 0.08);
                border-radius: 4px;
            }
        """)
        btn_more.clicked.connect(lambda: self._show_context_menu(btn_more))
        self.header_layout.addWidget(btn_more)

        # عنوان و استودیو
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 2, 0, 2)
        
        couple_name = self.project.get("couple_names") or self.project.get("title", "پروژه")
        lbl_title = QLabel(couple_name)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14.5px; font-weight: 900; color: #F8FAFC; border: none; background: transparent;")
        title_box.addWidget(lbl_title)

        raw_client = self.project.get("client_name") or "بدون استودیو"
        client_display = clean_studio_display_name(raw_client)
        lbl_client = QLabel(f"استودیو: <span style='color:#38BDF8;'>{client_display}</span>")
        lbl_client.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; font-weight: 600; border: none; background: transparent;")
        title_box.addWidget(lbl_client)

        self.card_layout.addLayout(title_box)

        # نوار داینامیک کلیپ‌ها
        clips_data = self.project.get("clips_list", [])
        self.clip_bar = DynamicClipOverviewBar(clips_data=clips_data, parent=self)
        self.card_layout.addWidget(self.clip_bar)

        # باکس اطلاعات مالی و تاریخ
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #0A0E18;
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 7px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 5, 10, 5)
        info_layout.setSpacing(10)

        fee_str = format_toman(self.project.get("total_fee", 0))
        event_str = gregorian_to_jalali(self.project.get("event_date")) or "-"
        dead_str = gregorian_to_jalali(self.project.get("deadline")) or "-"

        lbl_fee = QLabel(f"قرارداد: <b style='color:#F8FAFC;'>{fee_str}</b>")
        lbl_fee.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
        info_layout.addWidget(lbl_fee)

        info_layout.addStretch()

        lbl_event = QLabel(f"مراسم: <b style='color:#818CF8;'>{event_str}</b>")
        lbl_event.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
        info_layout.addWidget(lbl_event)

        dead_color = "#EF4444" if self.is_overdue else "#FBBF24"
        lbl_dead = QLabel(f"تحویل: <b style='color:{dead_color};'>{dead_str}</b>")
        lbl_dead.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
        info_layout.addWidget(lbl_dead)

        self.card_layout.addWidget(info_frame)

        # نوار ابزار دکمه‌های پایین
        foot_row = QHBoxLayout()
        foot_row.setContentsMargins(0, 2, 0, 0)
        foot_row.setSpacing(6)

        can_deliver = (prog_val >= 100 or (t_cnt > 0 and c_cnt == t_cnt)) and (status_key != "under_review")
        if can_deliver:
            btn_deliver = QPushButton("تحویل به استودیو")
            btn_deliver.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_deliver.setToolTip("ثبت تحویل رسمی، ورود هزینه به بخش مالی و شروع بازبینی آتلیه")
            btn_deliver.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: rgba(6, 182, 212, 0.16);
                    color: #22D3EE;
                    border: 1px solid rgba(6, 182, 212, 0.40);
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 800;
                }
                QPushButton:hover {
                    background-color: #0891B2;
                    border-color: #22D3EE;
                    color: #FFFFFF;
                }
            """)
            btn_deliver.clicked.connect(self._mark_as_delivered)
            foot_row.addWidget(btn_deliver)

        has_path = bool(self.project.get("primary_path") and Path(self.project.get("primary_path")).exists())
        drive_border = "#10B981" if has_path else "#EF4444"

        btn_folder = QPushButton("پوشه راش‌ها")
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor if has_path else Qt.CursorShape.ForbiddenCursor)
        btn_folder.setStyleSheet(f"""
            QPushButton {{
                font-family: 'Vazirmatn';
                background-color: #141B2D;
                color: #F8FAFC;
                border: 1px solid {drive_border}40;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {drive_border};
                background-color: #1A243D;
            }}
        """)
        btn_folder.clicked.connect(self._open_folder)
        foot_row.addWidget(btn_folder)

        nle_path = self.project.get("nle_project_path", "")
        persian_nle = get_persian_nle_name(nle_path)
        has_nle_file = bool(nle_path and Path(nle_path).exists())

        btn_nle = QPushButton(persian_nle)
        btn_nle.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nle.setToolTip(f"اجرای پروژه در {persian_nle}\n{nle_path}" if has_nle_file else "فایل پروژه تدوین متصل نشده است")
        btn_nle.setStyleSheet(f"""
            QPushButton {{
                font-family: 'Vazirmatn';
                background-color: #141B2D;
                color: {'#C7D2FE' if has_nle_file else '#64748B'};
                border: 1px solid {'rgba(99, 102, 241, 0.4)' if has_nle_file else 'rgba(255, 255, 255, 0.08)'};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                border-color: #818CF8;
                background-color: #1D253E;
                color: #FFFFFF;
            }}
        """)
        btn_nle.clicked.connect(self._launch_nle_project)
        foot_row.addWidget(btn_nle)

        btn_msg = QPushButton("ارسال پیام")
        btn_msg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_msg.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(56, 189, 248, 0.12);
                color: #38BDF8;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0284C7;
                color: #FFFFFF;
            }
        """)
        btn_msg.clicked.connect(lambda: self._open_fast_messenger_popup(btn_msg))
        foot_row.addWidget(btn_msg)

        btn_add_rev = QPushButton("ثبت اصلاحیه")
        btn_add_rev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_rev.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(249, 115, 22, 0.12);
                color: #FB923C;
                border: 1px solid rgba(249, 115, 22, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #EA580C;
                color: #FFFFFF;
            }
        """)
        btn_add_rev.clicked.connect(self._open_new_revision)
        foot_row.addWidget(btn_add_rev)

        btn_pay = QPushButton("ثبت واریزی")
        btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pay.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(16, 185, 129, 0.12);
                color: #34D399;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #10B981;
                color: #FFFFFF;
            }
        """)
        btn_pay.clicked.connect(self._open_payment)
        foot_row.addWidget(btn_pay)

        foot_row.addStretch()

        btn_details = QPushButton("مشاهده پرونده ←")
        btn_details.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_details.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: transparent;
                color: #818CF8;
                border: none;
                font-size: 11.5px;
                font-weight: 800;
                padding: 4px 4px;
            }
            QPushButton:hover {
                color: #A5B4FC;
            }
        """)
        btn_details.clicked.connect(self._open_details)
        foot_row.addWidget(btn_details)

        self.card_layout.addLayout(foot_row)

    def _on_auto_archive_expired(self, project_id: int):
        if ProjectController.archive_project(project_id):
            couple = self.project.get("couple_names") or self.project.get("title") or "پروژه"
            global_signals.show_toast.emit(f"مهلت بازبینی به پایان رسید؛ پرونده «{couple}» خودکار به آرشیو منتقل شد.", "info")

    def _mark_as_delivered(self):
        couple = self.project.get("couple_names") or self.project.get("title") or "پروژه"
        fee = self.project.get("total_fee", 0)
        
        if StudioConfirmDialog.ask(
            self.window(),
            title="تأیید تحویل به استودیو",
            message=f"آیا فایل‌های پروژه «{couple}» آماده تحویل به استودیو است؟",
            details=f"با ثبت تحویل، مبلغ {format_toman(fee)} وارد دفتر مالی و مطالبات استودیو شده و شمارش معکوس بازبینی آغاز می‌گردد.",
            confirm_text="تأیید تحویل و ثبت در مالی",
            is_danger=False,
            icon_name="check"
        ):
            if ProjectController.mark_as_delivered(self.project_id):
                client_id = None
                p = ProjectController.get_project_by_id(self.project_id)
                if p:
                    client_id = p.client_id
                
                global_signals.transaction_recorded.emit(0)
                if client_id:
                    global_signals.client_balance_updated.emit(client_id)
                global_signals.show_toast.emit(f"پروژه «{couple}» با موفقیت تحویل شد و به دفتر مالی افزوده گردید.", "success")

    def _show_context_menu(self, parent_btn: QPushButton):
        menu = StudioMenu(self)

        prog_val = self.project.get("progress_pct", 0)
        t_cnt = self.project.get("total_clips", 0)
        c_cnt = self.project.get("completed_clips", 0)
        status_info = self.project.get("status_info", {})
        status_key = status_info.get("key", "")

        act_deliver = None
        if (prog_val >= 100 or (t_cnt > 0 and c_cnt == t_cnt)) and (status_key != "under_review"):
            act_deliver = menu.addAction(IconProvider.get_icon("check", "#06B6D4", size=14), "تحویل رسمی به استودیو")

        act_nle = menu.addAction(IconProvider.get_icon("nle_launch", "#818CF8", size=14), "اجرای فایل پروژه")
        act_edit = menu.addAction(IconProvider.get_icon("edit", "#818CF8", size=14), "ویرایش مشخصات پروژه")
        act_share = menu.addAction(IconProvider.get_icon("message", "#38BDF8", size=14), "ارسال فاکتور و وضعیت به استودیو")
        act_archive = menu.addAction(IconProvider.get_icon("archive", "#10B981", size=14), "انتقال به آرشیو")
        
        menu.addSeparator()
        act_delete = menu.addAction(IconProvider.get_icon("trash", "#EF4444", size=14), "حذف کامل پروژه")

        action = menu.show_beside_button(parent_btn)
        if act_deliver and action == act_deliver:
            self._mark_as_delivered()
        elif action == act_nle:
            self._launch_nle_project()
        elif action == act_edit:
            self._open_edit_dialog()
        elif action == act_share:
            self._open_share_dialog()
        elif action == act_archive:
            self._open_archive_confirm()
        elif action == act_delete:
            self._delete_project()

    def _launch_nle_project(self):
        nle_path = self.project.get("nle_project_path", "")
        success, message = NleLauncherHelper.launch_project(nle_path)
        if success:
            global_signals.show_toast.emit(message, "success")
        else:
            global_signals.show_toast.emit(message, "error")

    def _open_fast_messenger_popup(self, anchor_btn: QWidget):
        popup = QuickMessengerMiniPopup(self.project, self.window())
        popup.show_beside_widget(anchor_btn)

    def _open_edit_dialog(self):
        diag = EditProjectDialog(self.project_id, self.window())
        diag.exec()

    def _open_share_dialog(self):
        diag = StudioShareDialog(self.project_id, self.window())
        diag.exec()

    def _delete_project(self):
        couple = self.project.get('couple_names') or 'پروژه'
        if StudioConfirmDialog.ask(
            self.window(),
            title="حذف کامل پروژه",
            message=f"آیا از حذف کامل پرونده «{couple}» اطمینان دارید؟",
            details="هشدار: تمام کلیپ‌ها، دوره‌های اصلاحیه، لاگ‌ها و تراکنش‌های مالی متصل به این پروژه برای همیشه پاک خواهند شد.",
            confirm_text="حذف دائمی",
            is_danger=True,
            icon_name="trash"
        ):
            ProjectController.delete_project(self.project_id)

    def _open_new_revision(self):
        diag = NewRevisionDialog(self.project_id, self.window())
        diag.exec()

    def _open_archive_confirm(self):
        diag = ArchiveConfirmDialog(self.project_id, self.window())
        diag.exec()

    def _open_details(self):
        win = self.window()
        QTimer.singleShot(0, lambda: ProjectDetailsDialog(self.project_id, win).exec())

    def _open_payment(self):
        win = self.window()
        QTimer.singleShot(0, lambda: NewTransactionDialog(self.project_id, parent=win).exec())

    def _open_folder(self):
        path_str = self.project.get("primary_path")
        if not path_str or not Path(path_str).exists():
            global_signals.show_toast.emit("مسیر پوشه مشخص نشده یا هارد متصل نیست", "error")
            return
        open_path_in_os(path_str)