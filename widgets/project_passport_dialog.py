# ==================================================
# FILE: widgets/project_passport_dialog.py
# ==================================================
import os
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QWidget, 
    QGridLayout, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QRegion
)
from sqlalchemy import select, func

from database.models import Project
from database.db_manager import db
from time_tracking.models import WorkSession
from core.project_controller import ProjectController
from core.settings_manager import SettingsManager
from core.persian_utils import gregorian_to_jalali, to_persian_numbers, format_toman
from core.icon_provider import IconProvider
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


class ProjectPassportImageExporter:
    """موتور رندر بوم شناسنامه با رزولوشن بالا و بدون به‌هم‌ریختگی مقیاس"""
    @staticmethod
    def export_widget_to_image(target_widget: QWidget, output_path: str, scale_factor: float = 2.0) -> bool:
        painter = None
        try:
            if not target_widget:
                return False

            orig_size = target_widget.size()
            target_widget.adjustSize()
            
            target_width = 960
            target_height = max(target_widget.height(), target_widget.sizeHint().height(), 700)
            target_widget.resize(target_width, target_height)

            img_w = int(target_width * scale_factor)
            img_h = int(target_height * scale_factor)

            image = QImage(img_w, img_h, QImage.Format.Format_ARGB32_Premultiplied)
            image.setDevicePixelRatio(scale_factor)
            image.fill(QColor("#080C14"))

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            target_widget.render(
                painter, 
                QPoint(0, 0), 
                QRegion(), 
                QWidget.RenderFlag.DrawWindowBackground | QWidget.RenderFlag.DrawChildren
            )
            painter.end()
            painter = None

            target_widget.resize(orig_size)

            out_path_obj = Path(output_path)
            out_path_obj.parent.mkdir(parents=True, exist_ok=True)

            final_path_str = str(out_path_obj.resolve())
            if not final_path_str.lower().endswith(".png"):
                final_path_str += ".png"

            return image.save(final_path_str, "PNG")
        except Exception:
            if painter is not None and painter.isActive():
                painter.end()
            traceback.print_exc()
            return False


class PassportMetricBox(QFrame):
    """کارت کوچک شاخص‌های آماری بالای شناسنامه"""
    def __init__(self, title: str, val_str: str, accent_color: str, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(68)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #8F909D; border: none; background: transparent;")
        lay.addWidget(lbl_t)

        lbl_v = QLabel(val_str)
        lbl_v.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 14px; font-weight: 800; color: {accent_color}; border: none; background: transparent;")
        lay.addWidget(lbl_v)


class ProjectPassportDialog(StudioBaseDialog):
    """دیالوگ شناسنامه رسمی تحویل اثر و مشخصات کامل فنی و اجرایی پروژه"""
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent=parent)
        self.project_id = project_id
        self.setMinimumSize(980, 720)
        self.resize(1020, 840)
        self.init_ui()

    def _make_clean_label(self, text: str, style: str = "") -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background: transparent !important; border: none !important; outline: none !important; {style}")
        return lbl

    def init_ui(self):
        project = ProjectController.get_project_by_id(self.project_id)
        if not project:
            self.reject()
            return

        self.settings = SettingsManager.load_settings()
        studio_brand = self.settings.get("studio_name", "").strip()
        editor_str = self.settings.get("editor_name", "").strip()

        couple_str = project.couple_names or project.title or "پروژه بدون نام"
        p_num = f"{project.project_number:03d}" if project.project_number else f"{project.id:03d}"
        client_str = project.client.company if (project.client and project.client.company) else (project.client.full_name if project.client else "بدون استودیو")
        manager_str = project.client.full_name if (project.client and project.client.company and project.client.full_name != project.client.company) else ""
        event_str = gregorian_to_jalali(project.event_date) if project.event_date else "-"
        today_str = gregorian_to_jalali(datetime.now())

        self.build_header(
            f"شناسنامه رسمی تحویل: {couple_str}",
            f"پرونده کد {to_persian_numbers(p_num)}   |   طرف قرارداد: {client_str}   |   تاریخ صدور: {today_str}",
            icon_name="check",
            icon_color="#10B981"
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        # کانتینر بیرونی برای مرکزچین کردن بوم سند
        scroll_outer_container = QWidget()
        scroll_outer_container.setStyleSheet("background: transparent;")
        outer_layout = QHBoxLayout(scroll_outer_container)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # بوم ثابت شناسنامه (Canvas فیکس ۹۶۰ پیکسل)
        self.content_widget = QWidget()
        self.content_widget.setObjectName("PassportPaperCanvas")
        self.content_widget.setFixedWidth(960)
        self.content_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.content_widget.setStyleSheet("""
            QWidget#PassportPaperCanvas {
                background-color: #0F1420;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        c_lay = QVBoxLayout(self.content_widget)
        c_lay.setContentsMargins(28, 24, 28, 24)
        c_lay.setSpacing(14)

        # ==========================================
        # ۱. سربرگ سازمانی شناسنامه (Executive Header)
        # ==========================================
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #141B2B; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 10px;")
        h_box = QHBoxLayout(header_card)
        h_box.setContentsMargins(22, 16, 22, 16)
        h_box.setSpacing(18)
        h_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # لوگو
        logo_path = self.settings.get("studio_logo_path", "")
        if logo_path and Path(logo_path).exists():
            try:
                logo_lbl = QLabel()
                logo_lbl.setFixedSize(72, 72)
                logo_lbl.setScaledContents(True)
                logo_lbl.setStyleSheet("background: transparent; border: none; border-radius: 8px;")
                logo_lbl.setPixmap(QPixmap(logo_path))
                h_box.addWidget(logo_lbl)
            except Exception:
                pass

        # عنوان و هویت رسمی تدوین‌گر بدون تکرار
        studio_info = QVBoxLayout()
        studio_info.setSpacing(3)
        
        if not studio_brand or studio_brand.lower() == editor_str.lower():
            primary_header_title = "شناسنامه رسمی تحویل و آرشیو تدوین"
            secondary_header_title = f"تدوین‌گر و تصحیح‌کننده رنگ: {editor_str}" if editor_str else "خدمات تخصصی تدوین و پس‌تولید ویدیو"
        else:
            primary_header_title = studio_brand
            secondary_header_title = f"مدیریت تدوین و پس‌تولید: {editor_str}" if editor_str else "خدمات تخصصی تدوین و تصحیح رنگ ویدیو"

        studio_info.addWidget(self._make_clean_label(primary_header_title, "font-family: 'Vazirmatn'; font-size: 16px; font-weight: 900; color: #F8FAFC;"))
        studio_info.addWidget(self._make_clean_label(secondary_header_title, "font-family: 'Vazirmatn'; font-size: 11.5px; color: #818CF8; font-weight: 600;"))
        
        studio_phone = self.settings.get("phone", "")
        if studio_phone:
            studio_info.addWidget(self._make_clean_label(f"تلفن هماهنگی: {to_persian_numbers(studio_phone)}", "font-family: 'Vazirmatn'; font-size: 10.5px; color: #64748B;"))
        h_box.addLayout(studio_info, stretch=1)

        # باکس شناسنامه سند و وضعیت تحویل
        meta_box = QFrame()
        meta_box.setStyleSheet("background-color: #101624; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px;")
        m_lay = QVBoxLayout(meta_box)
        m_lay.setContentsMargins(14, 10, 14, 10)
        m_lay.setSpacing(4)
        m_lay.setAlignment(Qt.AlignmentFlag.AlignRight)

        safe_doc_num = f"PASSPORT-{p_num}"
        m_lay.addWidget(self._make_clean_label(f"کد پرونده: <b style='color:#F8FAFC;'>{safe_doc_num}</b>", "font-family: 'Segoe UI', 'Vazirmatn'; font-size: 11.5px; color: #94A3B8;"))
        m_lay.addWidget(self._make_clean_label(f"تاریخ صدور: <b style='color:#F8FAFC;'>{today_str}</b>", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8;"))
        
        status_tag = self._make_clean_label("وضعیت اثر: تایید نهایی و مختومه ✓", "font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 800; color: #10B981; padding-top: 2px;")
        m_lay.addWidget(status_tag)

        h_box.addWidget(meta_box)
        c_lay.addWidget(header_card)

        # ==========================================
        # ۲. مشخصات طرفین و جزئیات رویداد
        # ==========================================
        parties_frame = QFrame()
        parties_frame.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px;")
        p_grid = QGridLayout(parties_frame)
        p_grid.setContentsMargins(18, 12, 18, 12)
        p_grid.setHorizontalSpacing(24)
        p_grid.setVerticalSpacing(6)

        p_grid.addWidget(self._make_clean_label("عنوان پروژه و عنوان مراسم:", "font-family: 'Vazirmatn'; font-size: 11px; font-weight: bold; color: #818CF8;"), 0, 0)
        p_grid.addWidget(self._make_clean_label(f"{couple_str} (کد: {to_persian_numbers(p_num)})", "font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: bold; color: #F8FAFC;"), 1, 0)
        p_grid.addWidget(self._make_clean_label(f"تاریخ برگزاری مراسم: {event_str}", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;"), 2, 0)

        p_grid.addWidget(self._make_clean_label("طرف دوم (کارفرما / آتلیه سفارش‌دهنده):", "font-family: 'Vazirmatn'; font-size: 11px; font-weight: bold; color: #818CF8;"), 0, 1)
        client_desc = f"{client_str}" + (f" (مدیریت: {manager_str})" if manager_str else "")
        p_grid.addWidget(self._make_clean_label(client_desc, "font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: bold; color: #F8FAFC;"), 1, 1)
        client_phone = project.client.phone if (project.client and project.client.phone) else "-"
        p_grid.addWidget(self._make_clean_label(f"شماره تماس کارفرما: {to_persian_numbers(client_phone)}", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;"), 2, 1)

        p_grid.setColumnStretch(0, 1)
        p_grid.setColumnStretch(1, 1)
        c_lay.addWidget(parties_frame)

        # استخراج آمار زمان جلسات
        clip_durations: Dict[int, int] = {}
        with db.get_session() as session:
            tot_sec = session.execute(
                select(func.sum(WorkSession.active_duration)).where(WorkSession.project_id == project.id)
            ).scalar() or 0

            sess_cnt = session.execute(
                select(func.count(WorkSession.id)).where(WorkSession.project_id == project.id)
            ).scalar() or 0

            clip_stmt = select(WorkSession.clip_id, func.sum(WorkSession.active_duration)).where(
                WorkSession.project_id == project.id,
                WorkSession.clip_id != None
            ).group_by(WorkSession.clip_id)
            
            for row in session.execute(clip_stmt).all():
                if row[0]:
                    clip_durations[row[0]] = row[1] or 0

        # ==========================================
        # ۳. کارت‌های شاخص سه‌گانه پروژه
        # ==========================================
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        initial_delivery_str = gregorian_to_jalali(project.delivered_at) if project.delivered_at else (gregorian_to_jalali(project.completed_at) if project.completed_at else "تحویل نهایی")

        kpi_row.addWidget(PassportMetricBox("تعداد کل کلیپ‌ها", f"{to_persian_numbers(len(project.clips))} کلیپ", "#38BDF8"))
        kpi_row.addWidget(PassportMetricBox("دوره‌های بازبینی و اصلاحیه", f"{to_persian_numbers(len(project.revisions))} دوره", "#C084FC" if project.revisions else "#64748B"))
        kpi_row.addWidget(PassportMetricBox("مجموع زمان خالص تدوین", format_seconds_to_persian_duration(tot_sec), "#10B981"))
        c_lay.addLayout(kpi_row)

        # ==========================================
        # ۴. جدول مهندسی‌شده سوابق کلیپ‌های مراسم (عنوان کلیپ کاملاً وسط‌چین)
        # ==========================================
        c_lay.addWidget(self._make_clean_label("فهرست کلیپ‌های نهایی، زمان تدوین و تاریخ تکمیل:", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #38BDF8; margin-top: 2px;"))

        clips_card = QFrame()
        clips_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        cl_grid = QGridLayout(clips_card)
        cl_grid.setContentsMargins(14, 12, 14, 12)
        cl_grid.setHorizontalSpacing(10)
        cl_grid.setVerticalSpacing(4)

        cl_headers = [
            ("ردیف", Qt.AlignmentFlag.AlignCenter),
            ("عنوان قطعه / کلیپ", Qt.AlignmentFlag.AlignCenter),
            ("مدت‌زمان خالص تدوین", Qt.AlignmentFlag.AlignCenter),
            ("تاریخ و زمان تحویل", Qt.AlignmentFlag.AlignCenter),
            ("وضعیت نهایی", Qt.AlignmentFlag.AlignCenter)
        ]

        th_cl_bg = QFrame()
        th_cl_bg.setFixedHeight(32)
        th_cl_bg.setStyleSheet("background-color: #161F30; border-radius: 6px;")
        cl_grid.addWidget(th_cl_bg, 0, 0, 1, 5)

        for col_idx, (h_title, align) in enumerate(cl_headers):
            th_lbl = self._make_clean_label(h_title, "font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; color: #818CF8;")
            th_lbl.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            cl_grid.addWidget(th_lbl, 0, col_idx)

        cl_grid.setColumnStretch(0, 4)   # ردیف
        cl_grid.setColumnStretch(1, 40)  # عنوان (وسط‌چین)
        cl_grid.setColumnStretch(2, 22)  # زمان
        cl_grid.setColumnStretch(3, 20)  # تاریخ
        cl_grid.setColumnStretch(4, 14)  # وضعیت

        for idx, clip in enumerate(project.clips):
            row_idx = idx + 1
            row_bg_color = "transparent" if idx % 2 == 0 else "rgba(255, 255, 255, 0.015)"
            row_frame = QFrame()
            row_frame.setStyleSheet(f"background-color: {row_bg_color}; border-radius: 4px;")
            cl_grid.addWidget(row_frame, row_idx, 0, 1, 5)

            clip_dur_sec = clip_durations.get(clip.id, 0)
            dur_display = format_seconds_to_persian_duration(clip_dur_sec) if clip_dur_sec > 0 else "ثبت نشده"
            completed_str = gregorian_to_jalali(clip.completed_at) if clip.completed_at else (initial_delivery_str if clip.is_completed else "در جریان تدوین")
            status_text = "تکمیل شده ✓" if clip.is_completed else "در حال انجام"
            status_color = "#10B981" if clip.is_completed else "#F59E0B"

            lbl_r0 = self._make_clean_label(to_persian_numbers(row_idx), "font-family: 'Vazirmatn'; font-size: 11px; color: #64748B;")
            lbl_r0.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl_grid.addWidget(lbl_r0, row_idx, 0)

            # عنوان قطعه / کلیپ در مرکز ستون قرار گرفته است
            lbl_r1 = self._make_clean_label(clip.clip_name, "font-family: 'Vazirmatn'; font-size: 12px; font-weight: 700; color: #F8FAFC;")
            lbl_r1.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl_grid.addWidget(lbl_r1, row_idx, 1)

            lbl_r2 = self._make_clean_label(dur_display, "font-family: 'Vazirmatn'; font-size: 11px; color: #38BDF8;")
            lbl_r2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl_grid.addWidget(lbl_r2, row_idx, 2)

            lbl_r3 = self._make_clean_label(completed_str, "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
            lbl_r3.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl_grid.addWidget(lbl_r3, row_idx, 3)

            lbl_r4 = self._make_clean_label(status_text, f"font-family: 'Vazirmatn'; font-size: 11px; font-weight: 700; color: {status_color};")
            lbl_r4.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl_grid.addWidget(lbl_r4, row_idx, 4)

        c_lay.addWidget(clips_card)

        # ==========================================
        # ۵. سوابق دوره‌های اصلاحیه با شماره‌گذاری ترتیبی تسک‌ها
        # ==========================================
        c_lay.addWidget(self._make_clean_label("سوابق دوره‌های اصلاحیه و تغییرات درخواستی:", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #38BDF8; margin-top: 2px;"))

        if not project.revisions:
            empty_rev_card = QFrame()
            empty_rev_card.setStyleSheet("background-color: #121826; border: 1px dashed rgba(255, 255, 255, 0.08); border-radius: 8px;")
            e_rev_lay = QVBoxLayout(empty_rev_card)
            e_rev_lay.setContentsMargins(14, 12, 14, 12)
            lbl_no_rev = self._make_clean_label("این اثر در تحویل اولیه به تایید کامل رسیده و بدون نیاز به اصلاحیه مختومه شده است ✓", "font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 600; color: #10B981;")
            e_rev_lay.addWidget(lbl_no_rev, alignment=Qt.AlignmentFlag.AlignCenter)
            c_lay.addWidget(empty_rev_card)
        else:
            rev_card = QFrame()
            rev_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
            r_lay = QVBoxLayout(rev_card)
            r_lay.setContentsMargins(16, 12, 16, 12)
            r_lay.setSpacing(10)

            for rev in project.revisions:
                rev_box = QFrame()
                rev_box.setStyleSheet("background-color: #101624; border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 6px;")
                rb_lay = QVBoxLayout(rev_box)
                rb_lay.setContentsMargins(14, 10, 14, 10)
                rb_lay.setSpacing(6)

                top_rb = QHBoxLayout()
                extra_fee = getattr(rev, 'extra_fee', 0) or 0
                fee_str = f" (هزینه دوره: {format_toman(extra_fee)})" if extra_fee > 0 else ""
                top_rb.addWidget(self._make_clean_label(f"<b>{rev.title}</b>{fee_str}", "font-family: 'Vazirmatn'; font-size: 12.5px; color: #F8FAFC;"), stretch=1)
                
                req_s = gregorian_to_jalali(rev.requested_at)
                comp_s = gregorian_to_jalali(rev.completed_at) if rev.completed_at else "تکمیل شده"
                top_rb.addWidget(self._make_clean_label(f"درخواست: {req_s}   |   تحویل: {comp_s}", "font-family: 'Vazirmatn'; font-size: 10.5px; color: #94A3B8;"))
                rb_lay.addLayout(top_rb)

                # تسک‌ها به صورت مرتب و شماره‌گذاری‌شده بعد از اعداد زیر هم قرار می‌گیرند
                for t_idx, t in enumerate(rev.tasks):
                    task_num_str = to_persian_numbers(t_idx + 1)
                    col = "#10B981" if t.is_completed else "#F59E0B"
                    check_mark = "✓" if t.is_completed else "○"
                    
                    task_text_formatted = f"<b style='color:#818CF8;'>{task_num_str}.</b>  <span style='color:{col}; font-weight:bold;'>[{check_mark}]</span>  {t.task_text}"
                    t_lbl = self._make_clean_label(task_text_formatted, "font-family: 'Vazirmatn'; font-size: 11.5px; color: #E2E8F0; padding-right: 6px;")
                    rb_lay.addWidget(t_lbl)

                r_lay.addWidget(rev_box)

            c_lay.addWidget(rev_card)

        # ==========================================
        # ۶. گزارش مالی و وضعیت تسویه
        # ==========================================
        c_lay.addWidget(self._make_clean_label("وضعیت مالی و تسویه‌حساب پروژه:", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #38BDF8; margin-top: 2px;"))
        
        fin_summary = ProjectController.get_project_financial_summary(project)
        fin_card = QFrame()
        fin_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        f_lay = QHBoxLayout(fin_card)
        f_lay.setContentsMargins(18, 12, 18, 12)
        f_lay.setSpacing(18)

        f_lay.addWidget(self._make_clean_label(f"مبلغ کل قرارداد: <b style='color:#F8FAFC;'>{format_toman(fin_summary['total_fee'])}</b>", "font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8;"), stretch=1)
        f_lay.addWidget(self._make_clean_label(f"مجموع پرداختی‌ها: <b style='color:#10B981;'>{format_toman(fin_summary['total_paid'])}</b>", "font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8;"), stretch=1)
        
        is_settled = fin_summary["is_settled"]
        rem_color = "#10B981" if is_settled else "#F59E0B"
        rem_text = "تسویه کامل (۰ تومان) ✓" if is_settled else f"مانده حساب: {format_toman(fin_summary['remaining'])}"
        f_lay.addWidget(self._make_clean_label(f"وضعیت حساب: <b style='color:{rem_color};'>{rem_text}</b>", "font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8;"), stretch=1)
        
        c_lay.addWidget(fin_card)

        # ==========================================
        # ۷. مهر و امضای تدوین‌گر
        # ==========================================
        sign_path = self.settings.get("studio_signature_path", "")
        sign_box = QHBoxLayout()
        sign_box.setContentsMargins(10, 4, 10, 0)
        
        lbl_validity = self._make_clean_label(
            "«کلیه فایل‌ها، راش‌ها و خروجی‌های این پروژه با تایید کامل کارفرما تحویل و مطابق استانداردهای کیفی استودیو بایگانی گردید.»", 
            "font-family: 'Vazirmatn'; font-size: 9.5px; color: #56618A; font-style: italic;"
        )
        sign_box.addWidget(lbl_validity, stretch=1)

        if sign_path and Path(sign_path).exists():
            try:
                sign_col = QVBoxLayout()
                sign_col.setSpacing(2)
                sign_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
                sign_col.addWidget(self._make_clean_label("مهر و امضای تدوین‌گر:", "font-family: 'Vazirmatn'; font-size: 10px; color: #8F909D;"))
                s_img = QLabel()
                s_img.setFixedHeight(54)
                s_img.setStyleSheet("background: transparent !important; border: none !important;")
                s_img.setPixmap(QPixmap(sign_path).scaled(130, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                sign_col.addWidget(s_img)
                sign_box.addLayout(sign_col)
            except Exception:
                pass

        c_lay.addLayout(sign_box)

        # ==========================================
        # ۸. نوار برندینگ و اصالت سند (Security Seal)
        # ==========================================
        software_badge = QFrame()
        software_badge.setFixedHeight(36)
        software_badge.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #0B0E17, stop:0.5 #121828, stop:1 #0B0E17);
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 8px;
            }
        """)
        sb_lay = QHBoxLayout(software_badge)
        sb_lay.setContentsMargins(16, 0, 16, 0)
        sb_lay.setSpacing(10)
        sb_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_verified = QLabel("VERIFIED PASSPORT")
        lbl_verified.setStyleSheet("""
            font-family: 'Segoe UI', sans-serif;
            font-size: 8.5px;
            font-weight: 900;
            color: #10B981;
            background-color: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 4px;
            padding: 2px 6px;
            letter-spacing: 0.5px;
        """)
        sb_lay.addWidget(lbl_verified)

        logo_icon = QLabel()
        logo_icon.setPixmap(IconProvider.get_pixmap("clp_brand_mark", "#818CF8", size=14))
        logo_icon.setStyleSheet("background: transparent; border: none;")
        sb_lay.addWidget(logo_icon)

        lbl_promo = self._make_clean_label(
            "صادرشده توسط سامانه مدیریت پایپ‌لاین و آرشیو تدوین CutterLog Pro",
            "font-family: 'Vazirmatn'; font-size: 11px; font-weight: 700; color: #F8FAFC;"
        )
        sb_lay.addWidget(lbl_promo)

        sb_lay.addStretch()

        lbl_promo_en = self._make_clean_label(
            "Official Post-Production Workflow & Ledger",
            "font-family: 'Segoe UI', sans-serif; font-size: 9.5px; font-weight: 600; color: #818CF8; letter-spacing: 0.3px;"
        )
        sb_lay.addWidget(lbl_promo_en)

        c_lay.addWidget(software_badge)

        outer_layout.addWidget(self.content_widget)
        scroll.setWidget(scroll_outer_container)
        self.container_layout.addWidget(scroll, stretch=1)

        # ==========================================
        # ۹. دکمه‌های اقدام زیر دیالوگ
        # ==========================================
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        btn_export = QPushButton("خروجی باکیفیت تصویر شناسنامه رسمی (PNG)")
        btn_export.setIcon(IconProvider.get_icon("save", "#FFFFFF", size=14))
        btn_export.setIconSize(QSize(14, 14))
        btn_export.setFixedHeight(40)
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-weight: 800;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_export.clicked.connect(self._export_image)
        action_bar.addWidget(btn_export, stretch=2)

        btn_close = QPushButton("بستن")
        btn_close.setFixedHeight(40)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 0 18px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; border-color: #6366F1; }
        """)
        btn_close.clicked.connect(self.accept)
        action_bar.addWidget(btn_close, stretch=1)

        self.container_layout.addLayout(action_bar)

    def _export_image(self):
        project = ProjectController.get_project_by_id(self.project_id)
        if not project:
            return

        couple_clean = (project.couple_names or project.title or "پروژه").replace(" ", "_").replace("/", "-")
        client_name = project.client.company if (project.client and project.client.company) else (project.client.full_name if project.client else "استودیو")
        client_clean = client_name.replace(" ", "_")
        p_num = f"{project.project_number:03d}" if project.project_number else f"{project.id:03d}"
        shamsi_clean = gregorian_to_jalali(datetime.now()).replace('/', '-')
        default_filename = f"شناسنامه_{p_num}_{couple_clean}_{client_clean}_{shamsi_clean}.png"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره تصویر شناسنامه رسمی پروژه",
            default_filename,
            "PNG Image (*.png)"
        )
        if not file_path:
            return

        try:
            success = ProjectPassportImageExporter.export_widget_to_image(self.content_widget, file_path, scale_factor=2.0)
            if success:
                StudioConfirmDialog.ask(
                    self, 
                    title="موفقیت", 
                    message="تصویر شناسنامه رسمی با بالاترین کیفیت Ultra-HD ذخیره شد.", 
                    details=f"مسیر ذخیره:\n{file_path}",
                    confirm_text="متوجه شدم",
                    icon_name="check"
                )
            else:
                StudioConfirmDialog.ask(
                    self, 
                    title="خطا", 
                    message="خطا در ذخیره تصویر شناسنامه.", 
                    is_danger=True,
                    icon_name="alert"
                )
        except Exception as err:
            StudioConfirmDialog.ask(
                self, 
                title="خطا", 
                message=f"خطای سیستمی رخ داد:\n{err}", 
                is_danger=True,
                icon_name="alert"
            )