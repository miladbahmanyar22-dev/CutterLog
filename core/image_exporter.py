# ==================================================
# FILE: core/image_exporter.py
# ==================================================
import os
from pathlib import Path
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QImage, QPainter, QColor, QRegion
from PySide6.QtCore import Qt, QPoint


class ProjectPassportImageExporter:
    @staticmethod
    def export_widget_to_image(target_widget: QWidget, output_path: str, scale_factor: float = 3.0) -> bool:
        """
        رندر مستقیم و شفاف با کیفیت بسیار بالا (Ultra High-DPI / 300 DPI Crisp)
        بدون تاری یا افت کیفیت فونت‌های فارسی و آیکون‌ها.
        """
        try:
            if not target_widget:
                return False

            # ذخیره اندازه اصلی ویجت
            orig_size = target_widget.size()

            # محاسبه دقیق ابعاد بر اساس محتوا
            target_widget.adjustSize()
            target_width = max(target_widget.width(), target_widget.sizeHint().width(), 820)
            target_height = max(target_widget.height(), target_widget.sizeHint().height(), 900)

            # تنظیم موقت اندازه واقعی روی ویجت
            target_widget.resize(target_width, target_height)

            # ساخت بوم با ابعاد بزرگ واقعی (کیفیت اصلی 3X بدون Stretch بعدی)
            img_w = int(target_width * scale_factor)
            img_h = int(target_height * scale_factor)

            image = QImage(img_w, img_h, QImage.Format.Format_ARGB32_Premultiplied)
            image.setDevicePixelRatio(scale_factor)
            image.fill(QColor("#0B0F17"))

            # نقاشی مستقیم المان‌ها روی رزولوشن بالا
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

            # بازگردانی ویجت به اندازه پنجره اصلی
            target_widget.resize(orig_size)

            # اطمینان از وجود پوشه خروجی و ذخیره نهایی
            out_dir = os.path.dirname(output_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)

            return image.save(output_path, "PNG")

        except Exception as e:
            print(f"Export High-DPI Widget Error: {e}")
            return False