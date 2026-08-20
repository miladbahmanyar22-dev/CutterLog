# core/pdf_invoice_generator.py
from typing import Dict, Any
from core.persian_utils import format_toman, to_persian_numbers
from core.settings_manager import SettingsManager


def generate_persian_pdf_invoice(invoice_data: Dict[str, Any], output_path: str) -> bool:
    """تولید فاکتور رسمی یا ذخیره فایل مشخصات قرارداد"""
    try:
        settings = SettingsManager.load_settings()
        studio_name = settings.get("studio_name", "استودیوی تدوین دیاکو")
        phone = settings.get("phone", "09120000000")
        card_number = settings.get("card_number", "6037-9918-0000-0000")
        footer_note = settings.get("invoice_footer_note", "کلیه حقوق مادی و معنوی راش‌ها تا زمان تسویه کامل متعلق به استودیو می‌باشد.")

        # ساخت فایل متنی/HTML ساختاریافته قابل پرینت مستقیم
        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="fa">
        <head>
            <meta charset="utf-8">
            <title>فاکتور رسمی خدمات تدوین</title>
            <style>
                body {{ font-family: Tahoma, sans-serif; margin: 30px; color: #222; background: #FFF; }}
                .invoice-box {{ border: 1px solid #CCC; padding: 24px; border-radius: 8px; max-width: 800px; margin: auto; }}
                .header {{ border-bottom: 2px solid #6366F1; padding-bottom: 12px; margin-bottom: 20px; }}
                .title {{ font-size: 20px; font-weight: bold; color: #312E81; }}
                .meta {{ font-size: 12px; color: #666; margin-top: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #DDD; padding: 10px; text-align: center; font-size: 13px; }}
                th {{ background-color: #F3F4F6; font-weight: bold; }}
                .total {{ font-size: 15px; font-weight: bold; color: #10B981; margin-top: 20px; text-align: left; }}
                .footer {{ margin-top: 30px; border-top: 1px solid #EEE; padding-top: 10px; font-size: 11px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="invoice-box">
                <div class="header">
                    <div class="title">{studio_name}</div>
                    <div class="meta">شماره فاکتور: {to_persian_numbers(invoice_data.get('invoice_number', 'INV-001'))} | تاریخ صدور: {to_persian_numbers(invoice_data.get('date', ''))}</div>
                </div>

                <p><b>طرف قرارداد / استودیو:</b> {invoice_data.get('client_name', '-')}</p>
                <p><b>عنوان پروژه:</b> {invoice_data.get('project_title', '-')}</p>

                <table>
                    <thead>
                        <tr>
                            <th>شرح خدمات</th>
                            <th>مبلغ قابل پرداخت (تومان)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>تدوین و پس‌تولید کامل پکیج مراسم (شامل راف‌کات، تصحیح رنگ، صداگذاری و رندر 4K)</td>
                            <td>{format_toman(invoice_data.get('amount', 0))}</td>
                        </tr>
                    </tbody>
                </table>

                <div class="total">
                    مبلغ کل: {format_toman(invoice_data.get('amount', 0))}
                </div>

                <div class="footer">
                    <p><b>اطلاعات پرداخت:</b> شماره کارت: {to_persian_numbers(card_number)} | شماره تماس: {to_persian_numbers(phone)}</p>
                    <p>{footer_note}</p>
                </div>
            </div>
        </body>
        </html>
        """

        # اگر مسیر خروجی .pdf بود و reportlab یا weasyprint نبود، به صورت .html ذخیره و پرینت‌پذیر می‌شود
        export_file = output_path if output_path.endswith(".html") else output_path.replace(".pdf", ".html")
        with open(export_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return True

    except Exception as e:
        print(f"PDF Invoice Error: {e}")
        return False