# core/report_exporter.py
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import arabic_reshaper
from bidi.algorithm import get_display
import polars as pl
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from core.persian_utils import format_toman, gregorian_to_jalali, to_persian_numbers


def shape_persian(text: str) -> str:
    """اصلاح جهت و اتصال حروف فارسی برای موتور ReportLab"""
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)


class ReportExporter:
    @staticmethod
    def export_transactions_to_excel(transactions: List[Dict[str, Any]], output_path: str):
        """خروجی رسمی اکسل از تمام تراکنش‌های مالی با استفاده از Polars"""
        if not transactions:
            return

        df = pl.DataFrame(transactions)
        df.write_excel(output_path)

    @staticmethod
    def generate_invoice_pdf(
        project_title: str,
        client_name: str,
        total_fee: int,
        transactions: List[Dict[str, Any]],
        output_path: str
    ):
        """تولید فاکتور رسمی PDF فارسی برای پروژه تدوین"""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        elements = []
        styles = getSampleStyleSheet()

        # استایل‌های متن
        title_style = ParagraphStyle(
            name="InvoiceTitle",
            fontSize=18,
            leading=22,
            alignment=1,  # وسط‌چین
            textColor=colors.HexColor("#1A1A1E")
        )
        
        info_style = ParagraphStyle(
            name="InvoiceInfo",
            fontSize=11,
            leading=16,
            alignment=2,  # راست‌چین
            textColor=colors.HexColor("#2E2E36")
        )

        # ۱. سربرگ فاکتور
        elements.append(Paragraph(shape_persian("صورت‌حساب خدمات تدوین و پس‌تولید ویدیو"), title_style))
        elements.append(Spacer(1, 15))

        # ۲. اطلاعات کلی فاکتور
        today_shamsi = gregorian_to_jalali(datetime.utcnow())
        info_data = [
            [
                shape_persian(f"تاریخ صدور: {today_shamsi}"),
                shape_persian(f"نام کارفرما: {client_name}")
            ],
            [
                shape_persian(f"وضعیت فاکتور: رسمی"),
                shape_persian(f"عنوان پروژه: {project_title}")
            ]
        ]
        info_table = Table(info_data, colWidths=[250, 250])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#24242A")),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))

        # ۳. جدول ریز تراکنش‌ها و پرداخت‌ها
        paid_sum = sum(t.get("amount", 0) for t in transactions)
        remaining_balance = total_fee - paid_sum

        table_data = [
            [
                shape_persian("مبلغ (تومان)"),
                shape_persian("نوع پرداخت"),
                shape_persian("تاریخ پرداخت"),
                shape_persian("ردیف")
            ]
        ]

        for idx, t in enumerate(transactions, 1):
            table_data.append([
                shape_persian(format_toman(t.get("amount", 0), use_persian_digits=False)),
                shape_persian(t.get("payment_type_label", "واریز")),
                shape_persian(gregorian_to_jalali(t.get("paid_at"))),
                shape_persian(str(idx))
            ])

        # ردیف‌های خلاصه مالی
        table_data.append([
            shape_persian(format_toman(total_fee, use_persian_digits=False)),
            shape_persian("مبلغ کل قرارداد:"),
            "", ""
        ])
        table_data.append([
            shape_persian(format_toman(paid_sum, use_persian_digits=False)),
            shape_persian("مجموع پرداختی:"),
            "", ""
        ])
        table_data.append([
            shape_persian(format_toman(remaining_balance, use_persian_digits=False)),
            shape_persian("مانده حساب:"),
            "", ""
        ])

        trx_table = Table(table_data, colWidths=[140, 140, 140, 50])
        trx_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#6366F1")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -4), [colors.HexColor("#F9FAFB"), colors.white]),
            ('BACKGROUND', (0, -3), (-1, -1), colors.HexColor("#F3F4F6")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(trx_table)

        doc.build(elements)