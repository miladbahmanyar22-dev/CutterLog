# ==================================================
# FILE: widgets/project_passport_dialog.py
# ==================================================
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QWidget, 
    QGridLayout, QFileDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap
from sqlalchemy import select, func

from database.models import Project
from database.db_manager import db
from time_tracking.models import WorkSession
from core.project_controller import ProjectController
from core.settings_manager import SettingsManager
from core.persian_utils import gregorian_to_jalali, to_persian_numbers, format_toman
from core.icon_provider import IconProvider
from core.image_exporter import ProjectPassportImageExporter
from widgets.project_financial_summary_widget import ProjectFinancialSummaryWidget
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog


def format_seconds_to_persian_duration(total_seconds: int) -> str:
    if not total_seconds or total_seconds <= 0:
        return "۰ دقیقه"
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    if h > 0 and m > 0:
        return f"{to_persian_numbers(h)} ساعت و {to_persian_numbers(m)} دقیقه"
    elif h > 0:
        return f"{to_persian_numbers(h)} ساعت"
    return f"{to_persian_numbers(m)} دقیقه"


class ProjectPassportDialog(StudioBaseDialog):
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent=parent)
        self.project_id = project_id
        self.setMinimumSize(800, 640)
        self.resize(880, 780)
        self.init_ui()

    def _make_clean_label(self, text: str, style: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background: transparent !important; border: none !important; outline: none !important; {style}")
        return lbl

    def init_ui(self):
        project = ProjectController.get_project_by_id(self.project_id)
        if not project:
            self.reject()
            return

        settings = SettingsManager.load_settings()
        couple_str = project.couple_names or project.title or "پروژه بدون نام"
        p_num = f"{project.project_number:03d}" if project.project_number else f"{project.id:03d}"
        client_str = project.client.company if (project.client and project.client.company) else (project.client.full_name if project.client else "بدون استودیو")
        event_str = gregorian_to_jalali(project.event_date) if project.event_date else "-"

        # ۱. سربرگ استاندارد
        self.build_header(
            f"شناسنامه رسمی: {couple_str}  ({to_persian_numbers(p_num)})",
            f"طرف قرارداد: {client_str}    |    تاریخ مراسم: {event_str}",
            icon_name="check",
            icon_color="#10B981"
        )

        # ۲. محتوای اسکرول‌پذیر
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        # ویجت اصلی محتوا که عینا رندر خواهد شد
        self.content_widget = QWidget()
        self.content_widget.setObjectName("PassportContentWidget")
        self.content_widget.setStyleSheet("""
            QWidget#PassportContentWidget {
                background-color: #0B0F17;
            }
        """)
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(12, 10, 12, 14)
        content_layout.setSpacing(14)

        # کارت مشخصات کلی
        initial_delivery_str = gregorian_to_jalali(project.delivered_at) if project.delivered_at else (gregorian_to_jalali(project.completed_at) if project.completed_at else "ثبت‌نشده")
        
        summary_card = QFrame()
        summary_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        s_grid = QGridLayout(summary_card)
        s_grid.setContentsMargins(18, 14, 18, 14)
        s_grid.setHorizontalSpacing(24)
        s_grid.setVerticalSpacing(8)

        s_grid.addWidget(self._make_clean_label("تاریخ ثبت اولیه:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 0, 0)
        s_grid.addWidget(self._make_clean_label(gregorian_to_jalali(project.created_at), "font-family: 'Vazirmatn'; font-size: 12px; font-weight: 700; color: #F8FAFC;"), 0, 1)

        s_grid.addWidget(self._make_clean_label("تحویل اولیه به استودیو:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 0, 2)
        s_grid.addWidget(self._make_clean_label(initial_delivery_str, "font-family: 'Vazirmatn'; font-size: 12px; font-weight: 700; color: #10B981;"), 0, 3)

        s_grid.addWidget(self._make_clean_label("تعداد کلیپ‌ها:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 1, 0)
        s_grid.addWidget(self._make_clean_label(f"{to_persian_numbers(len(project.clips))} مورد", "font-family: 'Vazirmatn'; font-size: 12px; font-weight: 700; color: #F8FAFC;"), 1, 1)

        s_grid.addWidget(self._make_clean_label("دوره‌های اصلاحیه:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 1, 2)
        s_grid.addWidget(self._make_clean_label(f"{to_persian_numbers(len(project.revisions))} دوره", "font-family: 'Vazirmatn'; font-size: 12px; font-weight: 700; color: #F8FAFC;"), 1, 3)

        content_layout.addWidget(summary_card)

        # استخراج مجموع زمان کل و زمان اختصاصی هر کلیپ
        clip_durations: Dict[int, int] = {}
        with db.get_session() as session:
            tot_sec = session.execute(
                select(func.sum(WorkSession.active_duration)).where(WorkSession.project_id == project.id)
            ).scalar() or 0

            sess_cnt = session.execute(
                select(func.count(WorkSession.id)).where(WorkSession.project_id == project.id)
            ).scalar() or 0

            last_sess = session.scalars(
                select(WorkSession).where(WorkSession.project_id == project.id).order_by(WorkSession.start_time.desc())
            ).first()
            last_activity_str = gregorian_to_jalali(last_sess.end_time or last_sess.start_time) if last_sess else "ثبت نشده"

            clip_stmt = select(WorkSession.clip_id, func.sum(WorkSession.active_duration)).where(
                WorkSession.project_id == project.id,
                WorkSession.clip_id != None
            ).group_by(WorkSession.clip_id)
            
            for row in session.execute(clip_stmt).all():
                if row[0]:
                    clip_durations[row[0]] = row[1] or 0

        # کارت سوابق راندمان کل پروژه
        content_layout.addWidget(self._make_clean_label("۱. سوابق راندمان و زمان خالص کل تدوین", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #6366F1;"))
        time_card = QFrame()
        time_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 8px;")
        t_grid = QGridLayout(time_card)
        t_grid.setContentsMargins(18, 12, 18, 12)
        t_grid.setHorizontalSpacing(24)
        t_grid.setVerticalSpacing(8)

        t_grid.addWidget(self._make_clean_label("مجموع زمان خالص تدوین:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 0, 0)
        t_grid.addWidget(self._make_clean_label(format_seconds_to_persian_duration(tot_sec), "font-family: 'Vazirmatn'; font-size: 12px; font-weight: 800; color: #10B981;"), 0, 1)

        t_grid.addWidget(self._make_clean_label("تعداد کل جلسات کاری:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 0, 2)
        t_grid.addWidget(self._make_clean_label(f"{to_persian_numbers(sess_cnt)} جلسه", "font-family: 'Vazirmatn'; font-size: 12px; font-weight: 700; color: #818CF8;"), 0, 3)

        t_grid.addWidget(self._make_clean_label("آخرین فعالیت ثبت‌شده:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 1, 0)
        t_grid.addWidget(self._make_clean_label(last_activity_str, "font-family: 'Vazirmatn'; font-size: 12px; font-weight: 700; color: #F8FAFC;"), 1, 1)

        avg_sec = tot_sec // sess_cnt if sess_cnt > 0 else 0
        t_grid.addWidget(self._make_clean_label("میانگین زمان هر جلسه:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 1, 2)
        t_grid.addWidget(self._make_clean_label(format_seconds_to_persian_duration(avg_sec), "font-family: 'Vazirmatn'; font-size: 12px; font-weight: 700; color: #FBBF24;"), 1, 3)

        content_layout.addWidget(time_card)

        # ۲. سوابق کلیپ‌های اولیه
        content_layout.addWidget(self._make_clean_label("۲. سوابق تحویل، مدت‌زمان و تاریخ تکمیل هر کلیپ", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #6366F1;"))
        clips_card = QFrame()
        clips_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        clips_lay = QVBoxLayout(clips_card)
        clips_lay.setContentsMargins(16, 12, 16, 12)
        clips_lay.setSpacing(8)

        for clip in project.clips:
            r_box = QHBoxLayout()
            r_box.setSpacing(12)
            
            mark = "✓" if clip.is_completed else "○"
            color_c = "#10B981" if clip.is_completed else "#94A3B8"
            lbl_c = self._make_clean_label(f"{mark}    {clip.clip_name}", f"font-family: 'Vazirmatn'; color: {color_c}; font-size: 12px; font-weight: 700;")
            r_box.addWidget(lbl_c, stretch=2)
            
            clip_dur_sec = clip_durations.get(clip.id, 0)
            dur_display = format_seconds_to_persian_duration(clip_dur_sec) if clip_dur_sec > 0 else "ثبت نشده"
            dur_color = "#38BDF8" if clip_dur_sec > 0 else "#64748B"
            lbl_dur = self._make_clean_label(f"⏱️ زمان تدوین: <b style='color:{dur_color};'>{dur_display}</b>", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
            r_box.addWidget(lbl_dur, stretch=2)

            if clip.completed_at:
                dt_str = gregorian_to_jalali(clip.completed_at)
                lbl_d = self._make_clean_label(f"تکمیل: {dt_str}", "font-family: 'Vazirmatn'; color: #10B981; font-size: 11px; font-weight: 600;")
            else:
                lbl_d = self._make_clean_label("وضعیت: در حال تدوین", "font-family: 'Vazirmatn'; color: #64748B; font-size: 11px;")
            r_box.addWidget(lbl_d, alignment=Qt.AlignmentFlag.AlignLeft)

            clips_lay.addLayout(r_box)

        content_layout.addWidget(clips_card)

        # ۳. سوابق دوره‌های اصلاحیه
        content_layout.addWidget(self._make_clean_label("۳. سوابق و تاریخچه دوره‌های اصلاحیه", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #6366F1;"))
        if not project.revisions:
            empty_rev = self._make_clean_label("این پروژه بدون نیاز به اصلاحیه، در تحویل اولیه با موفقیت تکمیل و تحویل داده شده است.", "font-family: 'Vazirmatn'; color: #64748B; font-size: 12px; padding: 10px;")
            empty_card = QFrame()
            empty_card.setStyleSheet("background-color: #121826; border: 1px dashed rgba(255, 255, 255, 0.08); border-radius: 8px;")
            empty_lay = QVBoxLayout(empty_card)
            empty_lay.addWidget(empty_rev, alignment=Qt.AlignmentFlag.AlignCenter)
            content_layout.addWidget(empty_card)
        else:
            for rev in project.revisions:
                rev_card = QFrame()
                rev_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 8px;")
                r_lay = QVBoxLayout(rev_card)
                r_lay.setContentsMargins(16, 12, 16, 12)
                r_lay.setSpacing(6)

                top_r = QHBoxLayout()
                extra_fee = getattr(rev, 'extra_fee', 0) or 0
                fee_info = f"  (هزینه دوره: {format_toman(extra_fee)})" if extra_fee > 0 else ""
                
                lbl_rt = self._make_clean_label(f"<b>{rev.title}</b>{fee_info}", "font-family: 'Vazirmatn'; font-size: 12.5px; color: #F8FAFC;")
                top_r.addWidget(lbl_rt, stretch=1)

                reg_s = gregorian_to_jalali(rev.requested_at)
                comp_s = gregorian_to_jalali(rev.completed_at) if rev.completed_at else "در حال انجام"
                lbl_rd = self._make_clean_label(f"درخواست: {reg_s}    |    تحویل: {comp_s}", "font-family: 'Vazirmatn'; color: #94A3B8; font-size: 11px;")
                top_r.addWidget(lbl_rd)
                r_lay.addLayout(top_r)

                for t in rev.tasks:
                    mark = "✓" if t.is_completed else "○"
                    color_t = "#10B981" if t.is_completed else "#F59E0B"
                    t_lbl = self._make_clean_label(f"{mark}    {t.task_text}", f"font-family: 'Vazirmatn'; color: {color_t}; font-size: 11.5px; margin-right: 8px;")
                    r_lay.addWidget(t_lbl)

                content_layout.addWidget(rev_card)

        # ۴. گزارش مالی
        content_layout.addWidget(self._make_clean_label("۴. گزارش مالی و تسویه حساب", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #6366F1;"))
        fin_summary = ProjectController.get_project_financial_summary(project)
        self.passport_fin_widget = ProjectFinancialSummaryWidget(financial_data=fin_summary)
        content_layout.addWidget(self.passport_fin_widget)

        # ۵. امضا و مهر رسمی
        sign_path = settings.get("studio_signature_path", "")
        if sign_path and Path(sign_path).exists():
            sign_box = QHBoxLayout()
            sign_box.setContentsMargins(10, 6, 10, 0)
            sign_box.addStretch()
            
            sign_col = QVBoxLayout()
            sign_col.setSpacing(4)
            sign_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            lbl_sign_title = self._make_clean_label("مهر و امضای رسمی مدیریت / تدوین‌گر:", "font-family: 'Vazirmatn'; font-size: 11px; color: #8F909D;")
            sign_col.addWidget(lbl_sign_title)
            
            lbl_sign_img = QLabel()
            lbl_sign_img.setFixedHeight(65)
            lbl_sign_img.setStyleSheet("background: transparent !important; border: none !important;")
            pix_s = QPixmap(sign_path).scaled(160, 65, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_sign_img.setPixmap(pix_s)
            sign_col.addWidget(lbl_sign_img)
            
            sign_box.addLayout(sign_col)
            content_layout.addLayout(sign_box)

        scroll.setWidget(self.content_widget)
        self.container_layout.addWidget(scroll, stretch=1)

        # ۶. نوار دکمه‌های پایانی
        foot_layout = QHBoxLayout()
        foot_layout.setSpacing(8)

        btn_export = QPushButton("خروجی تصویر شناسنامه (PNG)")
        btn_export.setIcon(IconProvider.get_icon("save", "#FFFFFF", size=14))
        btn_export.setIconSize(QSize(14, 14))
        btn_export.setFixedHeight(38)
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        btn_export.clicked.connect(self._export_image)
        foot_layout.addWidget(btn_export, stretch=2)

        btn_close = QPushButton("بستن")
        btn_close.setFixedHeight(38)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #F8FAFC;
                background-color: #1E283D;
            }
        """)
        btn_close.clicked.connect(self.accept)
        foot_layout.addWidget(btn_close, stretch=1)

        self.container_layout.addLayout(foot_layout)

    def _export_image(self):
        project = ProjectController.get_project_by_id(self.project_id)
        if not project:
            return

        couple_clean = (project.couple_names or project.title or "پروژه").replace(" ", "-").replace("/", "-")
        client_name = project.client.company if (project.client and project.client.company) else (project.client.full_name if project.client else "استودیو")
        client_clean = client_name.replace(" ", "-")
        p_num = f"{project.project_number:03d}" if project.project_number else f"{project.id:03d}"
        default_filename = f"CutterLog_{p_num}_{couple_clean}_{client_clean}_شناسنامه.png"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره تصویر شناسنامه رسمی پروژه",
            default_filename,
            "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        if file_path:
            # رندر مستقیم ویجت با کیفیت Retina بدون به‌هم‌ریختگی
            if ProjectPassportImageExporter.export_widget_to_image(self.content_widget, file_path, scale_factor=2.0):
                StudioConfirmDialog.ask(
                    self, 
                    title="موفقیت", 
                    message="تصویر شناسنامه رسمی دقیقاً مطابق با پنجره نرم‌افزار ذخیره شد.", 
                    details=f"مسیر ذخیره:\n{file_path}",
                    confirm_text="متوجه شدم",
                    icon_name="check"
                )
            else:
                StudioConfirmDialog.ask(
                    self, 
                    title="خطا", 
                    message="خطا در تولید و ذخیره فایل تصویر شناسنامه.", 
                    is_danger=True,
                    icon_name="alert"
                )