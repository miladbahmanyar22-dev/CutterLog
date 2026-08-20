# ==================================================
# FILE: widgets/studio_invoice_dialog.py
# ==================================================
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QWidget, 
    QGridLayout, QFileDialog
)
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QFont, QPen, QBrush

from database.models import Client
from database.db_manager import db
from core.settings_manager import SettingsManager
from core.finance_controller import FinanceController
from core.persian_utils import format_toman, to_persian_numbers, gregorian_to_jalali
from core.icon_provider import IconProvider
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog


class StudioInvoiceImageExporter:
    """موتور رندرینگ فاکتور رسمی تجمیعی استودیو با وضوح بالا و ابعاد پویا"""
    @staticmethod
    def export_invoice_image(client_id: int, output_path: str) -> bool:
        try:
            with db.get_session() as session:
                client = session.get(Client, client_id)
                client_name = client.company or client.full_name if client else "استودیو"
                manager_name = client.full_name if client and client.company else ""

            summary = FinanceController.get_studio_debt_summary(client_id)
            unsettled_list = summary.get("unsettled_projects", [])
            settings = SettingsManager.load_settings()

            width = 1200
            margin = 55.0
            content_w = width - (margin * 2.0)

            font_title = QFont("Vazirmatn", 16, QFont.Weight.ExtraBold)
            font_section = QFont("Vazirmatn", 12, QFont.Weight.Bold)
            font_body = QFont("Vazirmatn", 10, QFont.Weight.Normal)
            font_bold = QFont("Vazirmatn", 10, QFont.Weight.Bold)
            font_meta = QFont("Vazirmatn", 9, QFont.Weight.Normal)

            for f in [font_title, font_section, font_body, font_bold, font_meta]:
                f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

            projects_count = len(unsettled_list)
            h_header = 140.0 + 20.0
            h_table = 45.0 + (projects_count * 34.0) + 45.0
            h_bank = 135.0
            h_note = 70.0 if settings.get("invoice_footer_note") else 0.0
            h_sign = 110.0 if settings.get("studio_signature_path") and Path(settings.get("studio_signature_path")).exists() else 0.0
            h_footer = 50.0

            total_height = int(margin + h_header + h_table + h_bank + h_note + h_sign + h_footer + margin)

            image = QImage(width, total_height, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(QColor("#0E131F"))

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            current_y = margin

            # ۱. هدر رسمی فاکتور
            h_rect = QRectF(margin, current_y, content_w, 140)
            painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
            painter.setBrush(QBrush(QColor("#161F30")))
            painter.drawRoundedRect(h_rect, 12, 12)

            studio_brand = settings.get("studio_name") or "استودیوی تدوین تخصصی"
            painter.setFont(font_title)
            painter.setPen(QColor("#F8FAFC"))
            painter.drawText(QRectF(margin + 24, current_y + 20, content_w - 48, 32), Qt.AlignmentFlag.AlignRight, f"صورت‌حساب و فاکتور تسویه حساب: {studio_brand}")

            today_shamsi = gregorian_to_jalali(datetime.now())
            painter.setFont(font_meta)
            painter.setPen(QColor("#94A3B8"))
            meta_str = f"کارفرما / آتلیه طرف حساب: {client_name} {f'({manager_name})' if manager_name else ''}    |    تاریخ صدور: {today_shamsi}"
            painter.drawText(QRectF(margin + 24, current_y + 60, content_w - 48, 22), Qt.AlignmentFlag.AlignRight, meta_str)

            logo_path = settings.get("studio_logo_path", "")
            if logo_path and Path(logo_path).exists():
                logo_pix = QPixmap(logo_path).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(int(margin + 24), int(current_y + 30), logo_pix)
            else:
                b_rect = QRectF(margin + 24, current_y + 35, 140, 32)
                painter.setPen(QPen(QColor("#F59E0B"), 1))
                painter.setBrush(QBrush(QColor(245, 158, 11, 25)))
                painter.drawRoundedRect(b_rect, 6, 6)
                painter.setFont(font_bold)
                painter.setPen(QColor("#F59E0B"))
                painter.drawText(b_rect, Qt.AlignmentFlag.AlignCenter, "صورت‌حساب رسمی")

            current_y += 160.0

            # ۲. جدول ریز پروژه‌ها
            painter.setFont(font_section)
            painter.setPen(QColor("#6366F1"))
            painter.drawText(QRectF(margin, current_y, content_w, 28), Qt.AlignmentFlag.AlignRight, "ریز پروژه‌های تحویل‌شده دارای مانده بدهی:")
            current_y += 34.0

            tbl_rect = QRectF(margin, current_y, content_w, h_table)
            painter.setPen(QPen(QColor(255, 255, 255, 12), 1))
            painter.setBrush(QBrush(QColor("#141B2A")))
            painter.drawRoundedRect(tbl_rect, 8, 8)

            painter.setFont(font_bold)
            painter.setPen(QColor("#94A3B8"))
            row_y = current_y + 12.0
            painter.drawText(QRectF(margin + content_w - 60, row_y, 50, 22), Qt.AlignmentFlag.AlignCenter, "ردیف")
            painter.drawText(QRectF(margin + content_w - 450, row_y, 380, 22), Qt.AlignmentFlag.AlignRight, "نام پروژه / عروس و داماد")
            painter.drawText(QRectF(margin + 380, row_y, 160, 22), Qt.AlignmentFlag.AlignCenter, "مبلغ کل قرارداد")
            painter.drawText(QRectF(margin + 200, row_y, 160, 22), Qt.AlignmentFlag.AlignCenter, "دریافتی")
            painter.drawText(QRectF(margin + 20, row_y, 160, 22), Qt.AlignmentFlag.AlignLeft, "مانده بدهی")

            painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
            painter.drawLine(int(margin), int(row_y + 26), int(margin + content_w), int(row_y + 26))

            row_y += 34.0
            for idx, p in enumerate(unsettled_list):
                painter.setFont(font_body)
                painter.setPen(QColor("#F8FAFC"))
                painter.drawText(QRectF(margin + content_w - 60, row_y, 50, 22), Qt.AlignmentFlag.AlignCenter, to_persian_numbers(idx + 1))
                painter.drawText(QRectF(margin + content_w - 450, row_y, 380, 22), Qt.AlignmentFlag.AlignRight, f"{p['title']}  ({to_persian_numbers(p['project_number'])})")
                painter.drawText(QRectF(margin + 380, row_y, 160, 22), Qt.AlignmentFlag.AlignCenter, format_toman(p['total_fee']))
                painter.drawText(QRectF(margin + 200, row_y, 160, 22), Qt.AlignmentFlag.AlignCenter, format_toman(p['total_paid']))
                painter.setFont(font_bold)
                painter.setPen(QColor("#F59E0B"))
                painter.drawText(QRectF(margin + 20, row_y, 160, 22), Qt.AlignmentFlag.AlignLeft, format_toman(p['remaining']))
                row_y += 34.0

            painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
            painter.drawLine(int(margin), int(row_y), int(margin + content_w), int(row_y))
            row_y += 10.0
            painter.setFont(font_bold)
            painter.setPen(QColor("#F8FAFC"))
            painter.drawText(QRectF(margin + content_w - 450, row_y, 380, 22), Qt.AlignmentFlag.AlignRight, "مجموع کل بدهی قابل پرداخت:")
            painter.setPen(QColor("#10B981"))
            painter.drawText(QRectF(margin + 20, row_y, 250, 22), Qt.AlignmentFlag.AlignLeft, format_toman(summary['total_remaining']))

            current_y += h_table + 20.0

            # ۳. اطلاعات حساب بانکی
            bank_rect = QRectF(margin, current_y, content_w, 125)
            painter.setPen(QPen(QColor(99, 102, 241, 40), 1))
            painter.setBrush(QBrush(QColor("#161F30")))
            painter.drawRoundedRect(bank_rect, 8, 8)

            painter.setFont(font_bold)
            painter.setPen(QColor("#818CF8"))
            painter.drawText(QRectF(margin + 20, current_y + 14, content_w - 40, 22), Qt.AlignmentFlag.AlignRight, "💳 اطلاعات حساب جهت واریز و تسویه:")

            card_num = settings.get("card_number") or "ثبت نشده در تنظیمات"
            iban_num = settings.get("iban") or "ثبت نشده در تنظیمات"
            phone = settings.get("phone") or "-"

            painter.setFont(font_body)
            painter.setPen(QColor("#F8FAFC"))
            painter.drawText(QRectF(margin + 20, current_y + 44, content_w - 40, 22), Qt.AlignmentFlag.AlignRight, f"شماره کارت بانکی: {card_num}")
            painter.drawText(QRectF(margin + 20, current_y + 70, content_w - 40, 22), Qt.AlignmentFlag.AlignRight, f"شماره شبا (IBAN): {iban_num}")
            painter.drawText(QRectF(margin + 20, current_y + 96, content_w - 40, 22), Qt.AlignmentFlag.AlignRight, f"شماره تماس هماهنگی: {phone}")

            current_y += 140.0

            # ۴. توضیحات
            note_text = settings.get("invoice_footer_note", "")
            if note_text:
                painter.setFont(font_meta)
                painter.setPen(QColor("#64748B"))
                painter.drawText(QRectF(margin, current_y, content_w, 45), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.TextWordWrap, f"توضیحات: {note_text}")
                current_y += 50.0

            # ۵. امضا
            sign_path = settings.get("studio_signature_path", "")
            if sign_path and Path(sign_path).exists():
                painter.setFont(font_meta)
                painter.setPen(QColor("#8F909D"))
                painter.drawText(QRectF(margin, current_y, content_w - 20, 20), Qt.AlignmentFlag.AlignLeft, "مهر و امضای مدیریت استودیو:")
                sign_pix = QPixmap(sign_path).scaled(180, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(int(margin + 20), int(current_y + 24), sign_pix)
                current_y += 105.0

            # ۶. پاورقی
            painter.setPen(QPen(QColor(255, 255, 255, 15), 1))
            painter.drawLine(int(margin), int(current_y), int(width - margin), int(current_y))
            
            painter.setFont(font_meta)
            painter.setPen(QColor("#64748B"))
            painter.drawText(QRectF(margin, current_y + 14, content_w, 25), Qt.AlignmentFlag.AlignRight, f"سامانه مدیریت پایپ‌لاین تدوین CutterLog Pro   |   تاریخ صدور فاکتور: {today_shamsi}")
            painter.drawText(QRectF(margin, current_y + 14, content_w, 25), Qt.AlignmentFlag.AlignLeft, "Official Studio Invoice & Billing Statement")

            painter.end()
            return image.save(output_path, "PNG")
        except Exception as e:
            print(f"Invoice Export Error: {e}")
            return False


class StudioInvoiceDialog(StudioBaseDialog):
    """دیالوگ پیش‌نمایش و صدور فاکتور رسمی تجمیعی استودیو با زبان بصری استودیو"""
    def __init__(self, client_id: int, parent=None):
        super().__init__(parent=parent)
        self.client_id = client_id
        self.setMinimumSize(740, 580)
        self.resize(820, 720)
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

        self.summary = FinanceController.get_studio_debt_summary(self.client_id)
        self.settings = SettingsManager.load_settings()

        today_str = gregorian_to_jalali(datetime.now())
        studio_brand = self.settings.get("studio_name") or "استودیوی تدوین"
        
        self.build_header(
            f"صورت‌حساب رسمی بدهی: {self.client_name}", 
            f"صادرکننده: {studio_brand}   |   تاریخ صدور: {today_str}",
            icon_name="dollar", 
            icon_color="#F59E0B"
        )

        # محتوای اسکرول‌پذیر
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(content_widget)
        c_lay.setContentsMargins(4, 4, 4, 4)
        c_lay.setSpacing(14)

        c_lay.addWidget(self._make_clean_label("ریز پروژه‌های تحویل‌شده دارای مانده بدهی:", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #6366F1;"))
        
        unsettled = self.summary.get("unsettled_projects", [])
        if not unsettled:
            empty_lbl = self._make_clean_label("تمامی پروژه‌های این استودیو تسویه شده و مانده بدهی وجود ندارد.", "color: #10B981; font-weight: bold; font-size: 13px; padding: 20px;")
            empty_card = QFrame()
            empty_card.setStyleSheet("background-color: #121826; border: 1px dashed rgba(255,255,255,0.08); border-radius: 8px;")
            e_lay = QVBoxLayout(empty_card)
            e_lay.addWidget(empty_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
            c_lay.addWidget(empty_card)
        else:
            tbl_card = QFrame()
            tbl_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
            t_lay = QVBoxLayout(tbl_card)
            t_lay.setContentsMargins(16, 12, 16, 12)
            t_lay.setSpacing(8)

            for idx, p in enumerate(unsettled):
                row = QHBoxLayout()
                p_num = f"{p['project_number']:03d}" if p.get('project_number') else f"{p['id']:03d}"
                lbl_title = self._make_clean_label(f"<b>{to_persian_numbers(idx + 1)}. {p['title']}</b> <span style='color:#818CF8;'>({to_persian_numbers(p_num)})</span>", "font-family: 'Vazirmatn'; color: #F8FAFC; font-size: 12.5px;")
                row.addWidget(lbl_title, stretch=2)

                lbl_fee = self._make_clean_label(f"کل: {format_toman(p['total_fee'])}  |  دریافتی: {format_toman(p['total_paid'])}", "font-family: 'Vazirmatn'; color: #94A3B8; font-size: 11.5px;")
                row.addWidget(lbl_fee, stretch=2)

                lbl_rem = self._make_clean_label(f"مانده: <b style='color:#F59E0B;'>{format_toman(p['remaining'])}</b>", "font-family: 'Vazirmatn'; font-size: 12.5px;")
                row.addWidget(lbl_rem, alignment=Qt.AlignmentFlag.AlignLeft)

                t_lay.addLayout(row)

            div = QFrame()
            div.setFrameShape(QFrame.Shape.HLine)
            div.setFixedHeight(1)
            div.setStyleSheet("background-color: rgba(255,255,255,0.08); border: none;")
            t_lay.addWidget(div)

            tot_row = QHBoxLayout()
            tot_row.addWidget(self._make_clean_label("مجموع کل بدهی قابل پرداخت استودیو:", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: bold; color: #F8FAFC;"), stretch=1)
            lbl_tot = self._make_clean_label(format_toman(self.summary.get("total_remaining", 0)), "font-family: 'Vazirmatn'; font-size: 15px; font-weight: 900; color: #10B981;")
            tot_row.addWidget(lbl_tot)
            t_lay.addLayout(tot_row)

            c_lay.addWidget(tbl_card)

        # اطلاعات بانکی
        c_lay.addWidget(self._make_clean_label("اطلاعات حساب بانکی جهت واریز و تسویه:", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #6366F1;"))
        bank_card = QFrame()
        bank_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        b_grid = QGridLayout(bank_card)
        b_grid.setContentsMargins(18, 14, 18, 14)
        b_grid.setHorizontalSpacing(24)
        b_grid.setVerticalSpacing(8)

        card_num = self.settings.get("card_number") or "ثبت نشده در تنظیمات"
        iban_num = self.settings.get("iban") or "ثبت نشده در تنظیمات"
        phone = self.settings.get("phone") or "-"

        b_grid.addWidget(self._make_clean_label("شماره کارت بانکی:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 0, 0)
        b_grid.addWidget(self._make_clean_label(card_num, "font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 700; color: #F8FAFC;"), 0, 1)

        b_grid.addWidget(self._make_clean_label("شماره شبا (IBAN):", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 1, 0)
        b_grid.addWidget(self._make_clean_label(iban_num, "font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 700; color: #F8FAFC;"), 1, 1)

        b_grid.addWidget(self._make_clean_label("شماره تماس پشتیبانی:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #64748B;"), 2, 0)
        b_grid.addWidget(self._make_clean_label(phone, "font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 700; color: #F8FAFC;"), 2, 1)

        c_lay.addWidget(bank_card)

        # متن پاورقی
        note = self.settings.get("invoice_footer_note", "")
        if note:
            lbl_n = self._make_clean_label(f"توضیحات و شرایط: {note}", "font-family: 'Vazirmatn'; color: #64748B; font-size: 11px;")
            lbl_n.setWordWrap(True)
            c_lay.addWidget(lbl_n)

        # امضا
        sign_path = self.settings.get("studio_signature_path", "")
        if sign_path and Path(sign_path).exists():
            sign_row = QHBoxLayout()
            sign_row.addStretch()
            s_col = QVBoxLayout()
            s_col.addWidget(self._make_clean_label("مهر و امضای مدیریت استودیو:", "font-family: 'Vazirmatn'; color: #8F909D; font-size: 11px;"))
            s_img = QLabel()
            s_img.setFixedHeight(65)
            s_img.setStyleSheet("background: transparent !important; border: none !important;")
            s_img.setPixmap(QPixmap(sign_path).scaled(160, 65, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            s_col.addWidget(s_img)
            sign_row.addLayout(s_col)
            c_lay.addLayout(sign_row)

        scroll.setWidget(content_widget)
        self.container_layout.addWidget(scroll, stretch=1)

        # فوتر دکمه‌ها
        f_lay = QHBoxLayout()
        f_lay.setSpacing(8)

        btn_export = QPushButton("خروجی تصویر فاکتور (PNG)")
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
        f_lay.addWidget(btn_export, stretch=2)

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
        f_lay.addWidget(btn_close, stretch=1)

        self.container_layout.addLayout(f_lay)

    def _export_image(self):
        clean_name = self.client_name.replace(" ", "-").replace("/", "-")
        default_filename = f"CutterLog_فاکتور_{clean_name}_{gregorian_to_jalali(datetime.now()).replace('/', '-')}.png"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره تصویر فاکتور رسمی استودیو",
            default_filename,
            "PNG Image (*.png);;JPEG Image (*.jpg)"
        )
        if file_path:
            if StudioInvoiceImageExporter.export_invoice_image(self.client_id, file_path):
                StudioConfirmDialog.ask(
                    self, 
                    title="موفقیت", 
                    message="تصویر فاکتور رسمی با کیفیت بالا ذخیره شد.", 
                    details=f"مسیر ذخیره:\n{file_path}",
                    confirm_text="متوجه شدم",
                    icon_name="check"
                )
            else:
                StudioConfirmDialog.ask(
                    self, 
                    title="خطا", 
                    message="خطا در تولید فایل تصویر فاکتور.", 
                    is_danger=True,
                    icon_name="alert"
                )