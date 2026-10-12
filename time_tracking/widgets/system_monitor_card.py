# ==================================================
# FILE: time_tracking/widgets/system_monitor_card.py
# ==================================================
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QSizePolicy, QWidget
)
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, 
    QPen, QBrush, QPainterPath
)
from core.signals import global_signals


def interpolate_color(c1: QColor, c2: QColor, factor: float) -> QColor:
    """درونیابی خطی پیوسته بین دو رنگ برای ترنزیشن روان"""
    f = max(0.0, min(1.0, factor))
    r = int(c1.red() + (c2.red() - c1.red()) * f)
    g = int(c1.green() + (c2.green() - c1.green()) * f)
    b = int(c1.blue() + (c2.blue() - c1.blue()) * f)
    a = int(c1.alpha() + (c2.alpha() - c1.alpha()) * f)
    return QColor(r, g, b, a)


class NeonGlowProgressBar(QWidget):
    """نوار باریک پیشرفت با جلوه نوری ملایم نئونی"""
    def __init__(self, base_color: str, parent=None):
        super().__init__(parent)
        self.base_color = QColor(base_color)
        self.progress_pct = 0.0
        self.setFixedHeight(4)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)

    def set_progress(self, pct: float):
        self.progress_pct = max(0.0, min(100.0, pct))
        self.update()

    def set_color(self, color: QColor):
        self.base_color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0, 0, w, h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#080C14"))
        painter.drawRoundedRect(rect, 2, 2)

        if self.progress_pct > 0.0:
            fill_w = max(4.0, (self.progress_pct / 100.0) * w)
            fill_rect = QRectF(0, 0, fill_w, h)

            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0.0, QColor(self.base_color.red(), self.base_color.green(), self.base_color.blue(), 130))
            grad.setColorAt(0.75, self.base_color)
            grad.setColorAt(1.0, QColor("#FFFFFF"))

            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(fill_rect, 2, 2)

        painter.end()


class HardwarePrecisionTile(QFrame):
    """
    تایل سخت‌افزاری با عنوان فارسی، محتوای کاملاً انگلیسی،
    ترنزیشن آرام ۸۰۰ میلی‌ثانیه‌ای اعداد و شیفت تدریجی رنگ در لود سنگین
    """
    def __init__(self, farsi_title: str, base_accent_hex: str, parent=None):
        super().__init__(parent)
        self.farsi_title = farsi_title
        self.base_color = QColor(base_accent_hex)
        self.current_tint = QColor(base_accent_hex)
        self.target_tint = QColor(base_accent_hex)

        self.current_pct = 0.0
        self.anim = None

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
        self.setFixedHeight(92)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # ردیف بالا: عنوان فارسی در راست، مقدار درصدی انگلیسی در چپ
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        lbl_t = QLabel(self.farsi_title)
        lbl_t.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: #94A3B8; background: transparent; border: none;")
        top_row.addWidget(lbl_t)
        top_row.addStretch()

        self.lbl_val = QLabel("0.0%")
        self.lbl_val.setStyleSheet(f"font-family: 'Segoe UI', sans-serif; font-size: 13.5px; font-weight: 800; color: {self.base_color.name()}; background: transparent; border: none;")
        top_row.addWidget(self.lbl_val)
        layout.addLayout(top_row)

        self.pb_neon = NeonGlowProgressBar(self.base_color.name(), self)
        layout.addWidget(self.pb_neon)

        # متن مشخصات کاملاً انگلیسی و استاندارد
        self.lbl_primary_detail = QLabel("...")
        self.lbl_primary_detail.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 9.5px; font-weight: 600; color: #F8FAFC; background: transparent; border: none;")
        layout.addWidget(self.lbl_primary_detail)

        self.lbl_secondary_detail = QLabel("")
        self.lbl_secondary_detail.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 8.5px; font-weight: 500; color: #818CF8; background: transparent; border: none;")
        layout.addWidget(self.lbl_secondary_detail)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0, 0, w, h)

        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.setClipPath(path)

        # ترکیب پس‌زمینه بر مبنای رنگ کنونی به صورت کاملاً نرم
        tint = self.current_tint
        base_bg = interpolate_color(QColor("#121826"), QColor("#1D1217"), (self.current_pct - 30.0) / 70.0 if self.current_pct > 30.0 else 0.0)
        painter.fillRect(rect, base_bg)

        # هاله نوری در گوشه کارت
        radial = QRadialGradient(QPointF(w * 0.85, h * 0.15), w * 0.70)
        glow_alpha = min(85, int(20 + (self.current_pct * 0.6)))
        radial.setColorAt(0.0, QColor(tint.red(), tint.green(), tint.blue(), glow_alpha))
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, radial)

        painter.setClipping(False)
        border_alpha = min(150, int(25 + (self.current_pct * 1.1)))
        painter.setPen(QPen(QColor(tint.red(), tint.green(), tint.blue(), border_alpha), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), 8, 8)
        painter.end()

    def set_details(self, primary: str, secondary: str = ""):
        if primary != self.lbl_primary_detail.text():
            self.lbl_primary_detail.setText(primary)
        if secondary != self.lbl_secondary_detail.text():
            self.lbl_secondary_detail.setText(secondary)

    def set_value_smooth(self, target_val: float):
        target_val = max(0.0, min(100.0, target_val))

        # رنگ هدف بر اساس فشار
        if target_val >= 80.0:
            target_color = QColor("#EF4444")
        elif target_val >= 55.0:
            target_color = QColor("#FB923C")
        else:
            target_color = self.base_color

        start_val = self.current_pct
        start_color = QColor(self.current_tint)

        if self.anim and self.anim.state() == QVariantAnimation.State.Running:
            self.anim.stop()

        # انیمیشن ۸۰۰ میلی‌‌ثانیه‌ای ملایم و چشم‌نواز
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(800)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)

        def _step(progress_ratio):
            factor = float(progress_ratio)
            val = start_val + (target_val - start_val) * factor
            self.current_pct = val
            self.current_tint = interpolate_color(start_color, target_color, factor)

            self.pb_neon.set_progress(val)
            self.pb_neon.set_color(self.current_tint)
            self.lbl_val.setText(f"{val:.1f}%")
            self.lbl_val.setStyleSheet(f"font-family: 'Segoe UI', sans-serif; font-size: 13.5px; font-weight: 800; color: {self.current_tint.name()}; background: transparent; border: none;")
            self.update()

        self.anim.valueChanged.connect(_step)
        self.anim.start()


class SystemMonitorCard(QFrame):
    """
    کارت مرکز پایش سخت‌افزار CutterLog
    فقط عناوین پردازنده / حافظه رم / گرافیک فارسی، بقیه مشخصات کاملاً انگلیسی
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StudioSystemHubCard")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(195)
        self.setStyleSheet("""
            QFrame#StudioSystemHubCard {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        self.init_ui()
        global_signals.system_activity_updated.connect(self.update_metrics)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # هدر وضعیت و نام برنامه در فوکوس
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_app_name = QLabel("🎬 آماده شروع کار")
        self.lbl_app_name.setStyleSheet("font-size: 13px; font-weight: 800; color: #F8FAFC;")
        top_row.addWidget(self.lbl_app_name, stretch=1)

        self.lbl_cutterlog_load = QLabel("CutterLog: CPU 0.0% | RAM 0 MB")
        self.lbl_cutterlog_load.setStyleSheet("""
            font-family: 'Segoe UI', sans-serif;
            font-size: 9.5px;
            font-weight: 600;
            color: #64748B;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            padding: 2px 6px;
        """)
        top_row.addWidget(self.lbl_cutterlog_load)

        self.lbl_status_pill = QLabel("● سیستم پایدار")
        self.lbl_status_pill.setStyleSheet("""
            font-size: 10.5px;
            font-weight: 700;
            color: #10B981;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 6px;
            padding: 2px 8px;
        """)
        top_row.addWidget(self.lbl_status_pill)
        layout.addLayout(top_row)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.05);")
        layout.addWidget(div)

        # تایل‌های ۳‌گانه (عناوین فارسی، بقیه اجزا کاملاً انگلیسی)
        grid_row = QHBoxLayout()
        grid_row.setSpacing(8)
        grid_row.setDirection(QHBoxLayout.Direction.LeftToRight)

        self.tile_cpu = HardwarePrecisionTile("پردازنده", "#818CF8", self)
        self.tile_ram = HardwarePrecisionTile("حافظه رم", "#38BDF8", self)
        self.tile_gpu = HardwarePrecisionTile("گرافیک", "#F59E0B", self)

        grid_row.addWidget(self.tile_cpu)
        grid_row.addWidget(self.tile_ram)
        grid_row.addWidget(self.tile_gpu)
        layout.addLayout(grid_row)

        layout.addStretch()

        self.lbl_footer = QLabel("⚡ Hardware Engine Monitor (5s Balanced Refresh Rate)")
        self.lbl_footer.setStyleSheet("font-family: 'Segoe UI', sans-serif; font-size: 9px; color: #64748B; padding-right: 2px;")
        layout.addWidget(self.lbl_footer)

    def update_metrics(self, data: dict):
        app = data.get("active_app", "برنامه عمومی")
        self.lbl_app_name.setText(f"🎬 {app}")

        state = data.get("state", "idle")
        is_rendering = data.get("is_rendering", False)

        # مصرف خود CutterLog به زبان انگلیسی
        cl_cpu = data.get("cutterlog_cpu_pct", 0.0)
        cl_ram = data.get("cutterlog_ram_mb", 0.0)
        self.lbl_cutterlog_load.setText(f"CutterLog: CPU {cl_cpu:.1f}% | RAM {int(cl_ram)} MB")

        # پردازنده (CPU)
        cpu_pct = float(data.get("cpu_percent", 0.0))
        cpu_name = data.get("cpu_name", "Processor")
        cores = data.get("cpu_cores", 4)
        threads = data.get("cpu_threads", 8)
        freq_str = data.get("cpu_freq_str", "")

        cpu_sub = f"{cores} Cores / {threads} Threads"
        if freq_str and freq_str != "N/A":
            cpu_sub += f" • {freq_str}"

        self.tile_cpu.set_details(primary=cpu_name, secondary=cpu_sub)
        self.tile_cpu.set_value_smooth(cpu_pct)

        # حافظه رم (RAM)
        ram_pct = float(data.get("ram_percent", 0.0))
        ram_used = data.get("ram_used_gb", 0.0)
        ram_total = data.get("ram_total_gb", 16.0)
        ram_free = data.get("ram_free_gb", 0.0)

        ram_primary = f"{ram_used:.1f} GB / {ram_total:.1f} GB"
        ram_secondary = f"Available: {ram_free:.1f} GB"
        self.tile_ram.set_details(primary=ram_primary, secondary=ram_secondary)
        self.tile_ram.set_value_smooth(ram_pct)

        # گرافیک (GPU)
        gpu_pct = float(data.get("gpu_percent", 0.0))
        gpu_name = data.get("gpu_name", "Graphics")
        vram_used = data.get("vram_used_gb", 0.0)
        vram_total = data.get("vram_total_gb", 0.0)
        g_3d = data.get("gpu_3d", "N/A")
        g_enc = data.get("gpu_encode", "N/A")

        if vram_total > 0:
            gpu_primary = f"{gpu_name} ({vram_used:.1f} / {vram_total:.1f} GB VRAM)"
        else:
            gpu_primary = f"{gpu_name} (Unified / iGPU)"

        gpu_sec_parts = []
        if g_3d != "N/A":
            gpu_sec_parts.append(f"3D: {g_3d}")
        if g_enc != "N/A":
            gpu_sec_parts.append(f"Encode: {g_enc}")
        gpu_temp = data.get("gpu_temp", "N/A")
        if gpu_temp != "N/A":
            gpu_sec_parts.append(gpu_temp)

        gpu_secondary = " • ".join(gpu_sec_parts) if gpu_sec_parts else "Hardware Engine Ready"
        self.tile_gpu.set_details(primary=gpu_primary, secondary=gpu_secondary)
        self.tile_gpu.set_value_smooth(gpu_pct)

        # بج وضعیت سیستم
        if is_rendering:
            self.lbl_status_pill.setText("⚡ رندر / پردازش سنگین")
            self.lbl_status_pill.setStyleSheet("color: #38BDF8; background: rgba(56,189,248,0.12); border: 1px solid rgba(56,189,248,0.3); border-radius: 6px; padding: 2px 8px; font-weight: 700;")
        elif state == "editing":
            self.lbl_status_pill.setText("● تدوین فعال")
            self.lbl_status_pill.setStyleSheet("color: #10B981; background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3); border-radius: 6px; padding: 2px 8px; font-weight: 700;")
        elif state in ["outside_editing", "distraction"]:
            self.lbl_status_pill.setText("○ برنامه‌های جانبی")
            self.lbl_status_pill.setStyleSheet("color: #F59E0B; background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.3); border-radius: 6px; padding: 2px 8px; font-weight: 600;")
        else:
            self.lbl_status_pill.setText("⏳ آماده‌‌به‌کار")
            self.lbl_status_pill.setStyleSheet("color: #94A3B8; background: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 2px 8px;")