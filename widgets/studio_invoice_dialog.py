# ==================================================
# FILE: widgets/studio_invoice_dialog.py
# ==================================================
import os
import traceback
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QWidget, 
    QGridLayout, QFileDialog, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QRegion
)

from database.models import Client
from database.db_manager import db
from core.settings_manager import SettingsManager
from core.project_controller import ProjectController
from core.finance_controller import FinanceController
from core.persian_utils import format_toman, to_persian_numbers, gregorian_to_jalali
from core.icon_provider import IconProvider
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog


class StudioInvoiceImageExporter:
    """موتور رندر باکیفیت و دقیق برای خروجی تصویر بدون به‌هم‌ریختگی ابعاد"""
    @staticmethod
    def export_widget_to_image(target_widget: QWidget, output_path: str, scale_factor: float = 2.0) -> bool:
        painter = None
        try:
            if not target_widget:
                return False

            orig_size = target_widget.size()
            target_widget.adjustSize()
            
            target_width = 960
            target_height = max(target_widget.height(), target_widget.sizeHint().height(), 650)
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


class InvoiceMetricBox(QFrame):
    """کارت کوچک شاخص‌های مالی بالای فاکتور"""
    def __init__(self, title: str, amount_str: str, accent_color: str, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(68)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #8F909D; border: none; background: transparent;")
        lay.addWidget(lbl_t)

        lbl_v = QLabel(amount_str)
        lbl_v.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 14px; font-weight: 800; color: {accent_color}; border: none; background: transparent;")
        lay.addWidget(lbl_v)


class StudioInvoiceDialog(StudioBaseDialog):
    """دیالوگ سند رسمی فاکتور استودیو با معماری ثابت بوم و گرید منظم"""
    def __init__(self, client_id: int, parent=None):
        super().__init__(parent=parent)
        self.client_id = client_id
        self.setMinimumSize(980, 720)
        self.resize(1020, 840)
        self.init_ui()

    def _make_clean_label(self, text: str, style: str = "") -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background: transparent !important; border: none !important; outline: none !important; {style}")
        return lbl

    def init_ui(self):
        with db.get_session() as session:
            client = session.get(Client, self.client_id)
            if not client:
                self.reject()
                return
            self.client_name = client.company or client.full_name
            self.manager_name = client.full_name if client.company else ""
            self.client_phone = client.phone or "-"
            self.client_notes = client.notes or ""

        self.summary = FinanceController.get_studio_debt_summary(self.client_id)
        self.settings = SettingsManager.load_settings()

        today_str = gregorian_to_jalali(datetime.now())
        studio_brand = self.settings.get("studio_name", "").strip()
        editor_str = self.settings.get("editor_name", "").strip()
        
        self.build_header(
            f"صورت‌حساب رسمی: {self.client_name}", 
            f"سند تجمیعی پروژه‌های تحویل‌شده و وضعیت مطالبات   |   تاریخ صدور: {today_str}",
            icon_name="dollar", 
            icon_color="#10B981"
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        # کانتینر بیرونی برای وسط‌چین کردن بوم فاکتور
        scroll_outer_container = QWidget()
        scroll_outer_container.setStyleSheet("background: transparent;")
        outer_layout = QHBoxLayout(scroll_outer_container)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # بوم ثابت فاکتور (Canvas با عرض ثابت ۹۶۰ پیکسل)
        self.invoice_content_widget = QWidget()
        self.invoice_content_widget.setObjectName("InvoicePaperCanvas")
        self.invoice_content_widget.setFixedWidth(960)
        self.invoice_content_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.invoice_content_widget.setStyleSheet("""
            QWidget#InvoicePaperCanvas {
                background-color: #0F1420;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        c_lay = QVBoxLayout(self.invoice_content_widget)
        c_lay.setContentsMargins(28, 24, 28, 24)
        c_lay.setSpacing(14)

        # ==========================================
        # ۱. سربرگ سازمانی (Executive Header)
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

        # عنوان استودیو و مشخصات بدون تکرار نام
        studio_info = QVBoxLayout()
        studio_info.setSpacing(3)
        
        # اگر نام برند خالی یا برابر با نام تدوین‌گر بود، عنوان رسمی سند درج می‌شود
        if not studio_brand or studio_brand.lower() == editor_str.lower():
            primary_header_title = "صورت‌حساب رسمی خدمات تدوین و پس‌تولید"
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

        # باکس شناسنامه سند و فاکتور
        meta_box = QFrame()
        meta_box.setStyleSheet("background-color: #101624; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px;")
        m_lay = QVBoxLayout(meta_box)
        m_lay.setContentsMargins(14, 10, 14, 10)
        m_lay.setSpacing(4)
        m_lay.setAlignment(Qt.AlignmentFlag.AlignRight)

        safe_doc_num = f"INV-{datetime.now().strftime('%y%m')}-{self.client_id:03d}"
        m_lay.addWidget(self._make_clean_label(f"شماره سند: <b style='color:#F8FAFC;'>{safe_doc_num}</b>", "font-family: 'Segoe UI', 'Vazirmatn'; font-size: 11.5px; color: #94A3B8;"))
        m_lay.addWidget(self._make_clean_label(f"تاریخ صدور: <b style='color:#F8FAFC;'>{today_str}</b>", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8;"))
        
        tot_rem = self.summary.get("total_remaining", 0)
        is_fully_settled = (tot_rem == 0)
        tag_color = "#10B981" if is_fully_settled else "#F59E0B"
        tag_text = "تسویه کامل (بدون بدهی) ✓" if is_fully_settled else "دارای مانده بدهی معوق"
        status_tag = self._make_clean_label(tag_text, f"font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 800; color: {tag_color}; padding-top: 2px;")
        m_lay.addWidget(status_tag)

        h_box.addWidget(meta_box)
        c_lay.addWidget(header_card)

        # ==========================================
        # ۲. پنل دو ستونه مشخصات طرفین قرارداد
        # ==========================================
        parties_frame = QFrame()
        parties_frame.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px;")
        p_grid = QGridLayout(parties_frame)
        p_grid.setContentsMargins(18, 12, 18, 12)
        p_grid.setHorizontalSpacing(24)
        p_grid.setVerticalSpacing(6)

        # طرف اول
        p_grid.addWidget(self._make_clean_label("طرف اول (تدوین‌گر / مجری پس‌تولید):", "font-family: 'Vazirmatn'; font-size: 11px; font-weight: bold; color: #818CF8;"), 0, 0)
        
        if studio_brand and editor_str and studio_brand.strip().lower() != editor_str.strip().lower():
            editor_display_name = f"{studio_brand} (تدوین‌گر: {editor_str})"
        elif editor_str:
            editor_display_name = f"{editor_str} (تدوین‌گر و تصحیح‌کننده رنگ)"
        else:
            editor_display_name = studio_brand or "تدوین‌گر ارشد"

        p_grid.addWidget(self._make_clean_label(editor_display_name, "font-family: 'Vazirmatn'; font-size: 12px; font-weight: bold; color: #F8FAFC;"), 1, 0)
        if studio_phone:
            p_grid.addWidget(self._make_clean_label(f"تلفن هماهنگی: {to_persian_numbers(studio_phone)}", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;"), 2, 0)

        # طرف دوم
        p_grid.addWidget(self._make_clean_label("طرف دوم (کارفرما / آتلیه همکار):", "font-family: 'Vazirmatn'; font-size: 11px; font-weight: bold; color: #818CF8;"), 0, 1)
        client_desc = f"{self.client_name}" + (f" (مدیریت: {self.manager_name})" if self.manager_name else "")
        p_grid.addWidget(self._make_clean_label(client_desc, "font-family: 'Vazirmatn'; font-size: 12px; font-weight: bold; color: #F8FAFC;"), 1, 1)
        p_grid.addWidget(self._make_clean_label(f"شماره تماس کارفرما: {to_persian_numbers(self.client_phone)}", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;"), 2, 1)

        p_grid.setColumnStretch(0, 1)
        p_grid.setColumnStretch(1, 1)
        c_lay.addWidget(parties_frame)

        # ==========================================
        # ۳. جدول مهندسی‌شده ریز پروژه‌ها
        # ==========================================
        c_lay.addWidget(self._make_clean_label("فهرست پروژه‌های تحویل‌شده و وضعیت مالی:", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #38BDF8; margin-top: 4px;"))

        unsettled = self.summary.get("unsettled_projects", [])
        settled = self.summary.get("settled_projects", [])
        all_display_projects = unsettled + settled

        table_card = QFrame()
        table_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        t_grid = QGridLayout(table_card)
        t_grid.setContentsMargins(14, 12, 14, 12)
        t_grid.setHorizontalSpacing(10)
        t_grid.setVerticalSpacing(4)

        headers = [
            ("ردیف", Qt.AlignmentFlag.AlignCenter),
            ("عنوان پروژه و مراسم", Qt.AlignmentFlag.AlignRight),
            ("تاریخ مراسم", Qt.AlignmentFlag.AlignCenter),
            ("کلیپ‌ها و اصلاحیه", Qt.AlignmentFlag.AlignCenter),
            ("ارزش قرارداد", Qt.AlignmentFlag.AlignCenter),
            ("مجموع دریافتی", Qt.AlignmentFlag.AlignCenter),
            ("مانده حساب", Qt.AlignmentFlag.AlignCenter)
        ]

        th_bg = QFrame()
        th_bg.setFixedHeight(32)
        th_bg.setStyleSheet("background-color: #161F30; border-radius: 6px;")
        t_grid.addWidget(th_bg, 0, 0, 1, 7)

        for col_idx, (h_title, align) in enumerate(headers):
            th_lbl = self._make_clean_label(h_title, "font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; color: #818CF8;")
            th_lbl.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            t_grid.addWidget(th_lbl, 0, col_idx)

        t_grid.setColumnStretch(0, 4)   # ردیف
        t_grid.setColumnStretch(1, 28)  # عنوان پروژه
        t_grid.setColumnStretch(2, 12)  # تاریخ مراسم
        t_grid.setColumnStretch(3, 16)  # کلیپ‌ها
        t_grid.setColumnStretch(4, 14)  # قرارداد
        t_grid.setColumnStretch(5, 13)  # دریافتی
        t_grid.setColumnStretch(6, 13)  # مانده

        with db.get_session() as session:
            for idx, p_summary in enumerate(all_display_projects):
                row_idx = idx + 1
                p_id = p_summary.get("id")
                p_obj = ProjectController.get_project_by_id(p_id)

                row_bg_color = "transparent" if idx % 2 == 0 else "rgba(255, 255, 255, 0.015)"
                row_frame = QFrame()
                row_frame.setStyleSheet(f"background-color: {row_bg_color}; border-radius: 4px;")
                t_grid.addWidget(row_frame, row_idx, 0, 1, 7)

                p_num = f"{p_summary.get('project_number', idx + 1):03d}"
                event_str = gregorian_to_jalali(p_obj.event_date) if (p_obj and p_obj.event_date) else "-"
                
                clips_count = len(p_obj.clips) if (p_obj and p_obj.clips) else 0
                revs_count = len(p_obj.revisions) if (p_obj and p_obj.revisions) else 0
                pkg_info = f"{to_persian_numbers(clips_count)} کلیپ"
                if revs_count > 0:
                    pkg_info += f" • {to_persian_numbers(revs_count)} اصلاح"

                rem_val = p_summary.get("remaining", 0)
                rem_color = "#F59E0B" if rem_val > 0 else "#10B981"
                rem_text = format_toman(rem_val) if rem_val > 0 else "تسویه ✓"

                lbl_r0 = self._make_clean_label(to_persian_numbers(row_idx), "font-family: 'Vazirmatn'; font-size: 11px; color: #64748B;")
                lbl_r0.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r0, row_idx, 0)

                lbl_r1 = self._make_clean_label(f"<b>{p_summary.get('title', '-')}</b> <span style='color:#64748B;'>({to_persian_numbers(p_num)})</span>", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #F8FAFC;")
                lbl_r1.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                t_grid.addWidget(lbl_r1, row_idx, 1)

                lbl_r2 = self._make_clean_label(event_str, "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
                lbl_r2.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r2, row_idx, 2)

                lbl_r3 = self._make_clean_label(pkg_info, "font-family: 'Vazirmatn'; font-size: 10.5px; color: #818CF8;")
                lbl_r3.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r3, row_idx, 3)

                lbl_r4 = self._make_clean_label(format_toman(p_summary.get("total_fee", 0)), "font-family: 'Vazirmatn'; font-size: 11px; color: #F8FAFC;")
                lbl_r4.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r4, row_idx, 4)

                lbl_r5 = self._make_clean_label(format_toman(p_summary.get("total_paid", 0)), "font-family: 'Vazirmatn'; font-size: 11px; color: #10B981;")
                lbl_r5.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r5, row_idx, 5)

                lbl_r6 = self._make_clean_label(rem_text, f"font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: {rem_color};")
                lbl_r6.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r6, row_idx, 6)

        c_lay.addWidget(table_card)

        # ==========================================
        # ۴. پنل دوتکه پایین (کارت بانکی و تجمیع مبالغ)
        # ==========================================
        bottom_panel = QHBoxLayout()
        bottom_panel.setSpacing(14)

        # کارت بانکی (سمت راست پایین)
        bank_plate = QFrame()
        bank_plate.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        bp_lay = QVBoxLayout(bank_plate)
        bp_lay.setContentsMargins(16, 12, 16, 12)
        bp_lay.setSpacing(6)

        bp_lay.addWidget(self._make_clean_label("اطلاعات واریز و تسویه حساب شتاب:", "font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #818CF8;"))

        card_num = self.settings.get("card_number") or "ثبت‌نشده در تنظیمات"
        iban_num = self.settings.get("iban") or "ثبت‌نشده در تنظیمات"

        card_box = QFrame()
        card_box.setStyleSheet("background-color: #0E131F; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px;")
        cb_lay = QVBoxLayout(card_box)
        cb_lay.setContentsMargins(10, 6, 10, 6)
        cb_lay.setSpacing(2)
        cb_lay.addWidget(self._make_clean_label(f"شماره کارت: <b style='color:#FBBF24; letter-spacing:1px;'>{card_num}</b>", "font-family: 'Segoe UI', monospace; font-size: 12px; color: #94A3B8;"))
        cb_lay.addWidget(self._make_clean_label(f"شماره شبا: {iban_num}", "font-family: 'Segoe UI', monospace; font-size: 10.5px; color: #64748B;"))
        bp_lay.addWidget(card_box)

        # شرط حقوقی تسویه به نفع تدوین‌گر
        lbl_legal_clause = self._make_clean_label(
            "«کلیه حقوق مادی و معنوی راش‌ها و خروجی‌های نهایی تا زمان تسویه کامل متعلق به تدوین‌گر می‌باشد. پس از تسویه کامل حساب، مجوز استفاده و آرشیو اثر به کارفرما واگذار می‌گردد.»",
            "font-family: 'Vazirmatn'; font-size: 10px; color: #94A3B8; line-height: 1.5; font-weight: 500;"
        )
        lbl_legal_clause.setWordWrap(True)
        bp_lay.addWidget(lbl_legal_clause)

        bottom_panel.addWidget(bank_plate, stretch=3)

        # باکس جمع‌بندی مالی (سمت چپ پایین)
        calc_box = QFrame()
        calc_box.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        calc_lay = QVBoxLayout(calc_box)
        calc_lay.setContentsMargins(18, 12, 18, 12)
        calc_lay.setSpacing(6)

        tot_fee = self.summary.get("total_fee", 0)
        tot_paid = self.summary.get("total_paid", 0)

        r_fee = QHBoxLayout()
        r_fee.addWidget(self._make_clean_label("ارزش کل قراردادها:", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;"))
        r_fee.addStretch()
        r_fee.addWidget(self._make_clean_label(format_toman(tot_fee), "font-family: 'Vazirmatn'; font-size: 11.5px; color: #F8FAFC;"))
        calc_lay.addLayout(r_fee)

        r_paid = QHBoxLayout()
        r_paid.addWidget(self._make_clean_label("مجموع پرداختی‌های ثبت‌شده:", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;"))
        r_paid.addStretch()
        r_paid.addWidget(self._make_clean_label(format_toman(tot_paid), "font-family: 'Vazirmatn'; font-size: 11.5px; color: #10B981;"))
        calc_lay.addLayout(r_paid)

        div_calc = QFrame()
        div_calc.setFrameShape(QFrame.Shape.HLine)
        div_calc.setFixedHeight(1)
        div_calc.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: none;")
        calc_lay.addWidget(div_calc)

        # هایلایت مبلغ نهایی
        final_box = QFrame()
        final_box.setFixedHeight(44)
        final_box_bg = "rgba(245, 158, 11, 0.12)" if tot_rem > 0 else "rgba(16, 185, 129, 0.12)"
        final_box_border = "rgba(245, 158, 11, 0.35)" if tot_rem > 0 else "rgba(16, 185, 129, 0.35)"
        final_box.setStyleSheet(f"background-color: {final_box_bg}; border: 1px solid {final_box_border}; border-radius: 6px;")
        fb_lay = QHBoxLayout(final_box)
        fb_lay.setContentsMargins(12, 0, 12, 0)
        fb_lay.addWidget(self._make_clean_label("مبلغ نهایی قابل تسویه:", "font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #F8FAFC;"))
        fb_lay.addStretch()
        lbl_rem_amount = self._make_clean_label(format_toman(tot_rem), f"font-family: 'Vazirmatn'; font-size: 15px; font-weight: 900; color: {'#F59E0B' if tot_rem > 0 else '#10B981'};")
        fb_lay.addWidget(lbl_rem_amount)
        calc_lay.addWidget(final_box)

        bottom_panel.addWidget(calc_box, stretch=2)
        c_lay.addLayout(bottom_panel)

        # ==========================================
        # ۵. مهر رسمی و امضای تدوین‌گر
        # ==========================================
        sign_path = self.settings.get("studio_signature_path", "")
        if sign_path and Path(sign_path).exists():
            try:
                sign_box = QHBoxLayout()
                sign_box.setContentsMargins(10, 0, 10, 0)
                sign_box.addStretch()
                
                sign_col = QVBoxLayout()
                sign_col.setSpacing(2)
                sign_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
                sign_col.addWidget(self._make_clean_label("مهر و امضای تدوین‌گر:", "font-family: 'Vazirmatn'; font-size: 10.5px; color: #8F909D;"))
                s_img = QLabel()
                s_img.setFixedHeight(54)
                s_img.setStyleSheet("background: transparent !important; border: none !important;")
                s_img.setPixmap(QPixmap(sign_path).scaled(130, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                sign_col.addWidget(s_img)
                sign_box.addLayout(sign_col)
                c_lay.addLayout(sign_box)
            except Exception:
                pass

        # ==========================================
        # ۶. نوار برندینگ و اصالت سند (Security Seal & Brand Badge)
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

        # بج وریفای شده
        lbl_verified = QLabel("VERIFIED INVOICE")
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
            "تولیدشده توسط سامانه مدیریت پایپ‌لاین تدوین CutterLog Pro",
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

        outer_layout.addWidget(self.invoice_content_widget)
        scroll.setWidget(scroll_outer_container)
        self.container_layout.addWidget(scroll, stretch=1)

        # ==========================================
        # ۷. دکمه‌های اقدام زیر دیالوگ
        # ==========================================
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        btn_export = QPushButton("خروجی باکیفیت تصویر فاکتور رسمی (PNG)")
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
        safe_name = "".join(c for c in self.client_name if c not in r'\/:*?"<>|').strip().replace(" ", "_")
        shamsi_clean = gregorian_to_jalali(datetime.now()).replace('/', '-')
        default_filename = f"فاکتور_{safe_name}_{shamsi_clean}.png"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره تصویر فاکتور رسمی استودیو",
            default_filename,
            "PNG Image (*.png)"
        )
        if not file_path:
            return

        try:
            success = StudioInvoiceImageExporter.export_widget_to_image(self.invoice_content_widget, file_path, scale_factor=2.0)
            if success:
                StudioConfirmDialog.ask(
                    self, 
                    title="موفقیت", 
                    message="تصویر فاکتور رسمی با بالاترین کیفیت Ultra-HD ذخیره شد.", 
                    details=f"مسیر ذخیره:\n{file_path}",
                    confirm_text="متوجه شدم",
                    icon_name="check"
                )
            else:
                StudioConfirmDialog.ask(
                    self, 
                    title="خطا", 
                    message="خطا در ذخیره تصویر فاکتور.", 
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