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


class NeonGlowProgressBar(QWidget):
    """نوار پیشرفت سفارشی با گرادیان نئونی و نور انتهایی متحرک"""
    def __init__(self, base_color: str, parent=None):
        super().__init__(parent)
        self.base_color_hex = base_color
        self.progress_pct = 0.0
        self.setFixedHeight(6)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_progress(self, pct: float):
        self.progress_pct = max(0.0, min(100.0, pct))
        self.update()

    def set_base_color(self, hex_color: str):
        self.base_color_hex = hex_color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0, 0, w, h)

        # پس‌زمینه تیره نوار
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#080C14"))
        painter.drawRoundedRect(rect, 3, 3)

        if self.progress_pct > 0.0:
            fill_w = max(6.0, (self.progress_pct / 100.0) * w)
            fill_rect = QRectF(0, 0, fill_w, h)

            grad = QLinearGradient(0, 0, fill_w, 0)
            col = QColor(self.base_color_hex)
            
            grad.setColorAt(0.0, QColor(col.red(), col.green(), col.blue(), 130))
            grad.setColorAt(0.75, col)
            grad.setColorAt(1.0, QColor("#FFFFFF"))

            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(fill_rect, 3, 3)

        painter.end()


class HardwareMeterTile(QFrame):
    """تایل داینامیک با تغییر هوشمند رنگ Ambient Tint و هاله نوری در لود بالا"""
    def __init__(self, title: str, accent_color: str, default_model: str = "...", parent=None):
        super().__init__(parent)
        self.title = title
        self.accent_color = accent_color
        self.current_pct = 0
        self.anim = None
        self.glow_intensity = 35
        self.active_tint_color = QColor(accent_color)

        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
        self.setFixedHeight(88)

        self.init_ui(default_model)

    def init_ui(self, default_model: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        
        lbl_t = QLabel(self.title)
        lbl_t.setStyleSheet("font-family: -apple-system, 'Segoe UI', sans-serif; font-size: 11px; font-weight: 700; color: #94A3B8; background: transparent; border: none;")
        top_row.addWidget(lbl_t)
        top_row.addStretch()

        self.lbl_val = QLabel("0%")
        self.lbl_val.setStyleSheet(f"""
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
            font-weight: 800;
            color: {self.accent_color};
            background: transparent;
            border: none;
        """)
        top_row.addWidget(self.lbl_val)

        layout.addLayout(top_row)

        self.pb_neon = NeonGlowProgressBar(self.accent_color, self)
        layout.addWidget(self.pb_neon)

        self.lbl_model = QLabel(default_model)
        self.lbl_model.setStyleSheet("font-family: -apple-system, 'Segoe UI', sans-serif; font-size: 9.5px; font-weight: 600; color: #F8FAFC; background: transparent; border: none;")
        layout.addWidget(self.lbl_model)

        self.lbl_sub_stat = QLabel("")
        self.lbl_sub_stat.setStyleSheet("font-family: -apple-system, 'Segoe UI', sans-serif; font-size: 9px; font-weight: 500; color: #818CF8; background: transparent; border: none;")
        layout.addWidget(self.lbl_sub_stat)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        rect = QRectF(0, 0, w, h)

        path = QPainterPath()
        path.addRoundedRect(rect, 8, 8)
        painter.setClipPath(path)

        # محاسبه رنگ پس‌زمینه داینامیک (Ambient Tint) متناسب با لود
        if self.current_pct >= 75:
            base_bg = QColor("#1D1217")  # ته‌رنگ قرمز تیره هنگام رندرینگ سنگین
            tint_glow = QColor("#EF4444")
            border_alpha = min(180, int(50 + (self.current_pct * 1.3)))
        elif self.current_pct >= 50:
            base_bg = QColor("#1B1713")  # ته‌رنگ نارنجی هنگام کار سنگین
            tint_glow = QColor("#FB923C")
            border_alpha = min(150, int(40 + (self.current_pct * 1.1)))
        else:
            base_bg = QColor("#121826")  # تم تاریک آرام
            tint_glow = QColor(self.accent_color)
            border_alpha = min(120, int(30 + (self.current_pct * 0.8)))

        painter.fillRect(rect, base_bg)

        # هاله نوری داینامیک (Radial Glow) در گوشه کارت
        glow_alpha = min(110, int(self.glow_intensity + (self.current_pct * 0.75)))
        radial_glow = QColor(tint_glow.red(), tint_glow.green(), tint_glow.blue(), glow_alpha)

        radial = QRadialGradient(QPointF(w * 0.85, h * 0.15), w * 0.70)
        radial.setColorAt(0.0, radial_glow)
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(rect, radial)

        # خط مرزی نوری گرادیانتی
        painter.setClipping(False)
        border_col = QColor(tint_glow.red(), tint_glow.green(), tint_glow.blue(), border_alpha)
        painter.setPen(QPen(border_col, 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), 8, 8)

        painter.end()

    def set_model_and_stat(self, model_name: str, sub_stat: str = ""):
        if model_name and self.lbl_model.text() != model_name:
            self.lbl_model.setText(model_name)
        if sub_stat != self.lbl_sub_stat.text():
            self.lbl_sub_stat.setText(sub_stat)

    def set_value_smooth(self, target_val: int):
        target_val = max(0, min(100, target_val))

        # تنظیم رنگ نشانگر و عدد متناسب با شدت فشار کاری
        if target_val >= 75:
            active_color = "#EF4444"
        elif target_val >= 50:
            active_color = "#FB923C"
        else:
            active_color = self.accent_color

        self.pb_neon.set_base_color(active_color)
        self.lbl_val.setStyleSheet(f"font-family: 'Segoe UI', sans-serif; font-size: 13px; font-weight: 800; color: {active_color}; background: transparent; border: none;")

        if self.anim and self.anim.state() == QVariantAnimation.State.Running:
            self.anim.stop()

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(320)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(self.current_pct)
        self.anim.setEndValue(target_val)
        self.anim.valueChanged.connect(self._on_anim_step)
        self.anim.start()
        self.current_pct = target_val

    def _on_anim_step(self, val):
        v = int(val)
        self.pb_neon.set_progress(val)
        self.lbl_val.setText(f"{v}%")
        self.update()


class SystemMonitorCard(QFrame):
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

        # ۱. هدر وضعیت و نام برنامه فعال
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_app_name = QLabel("🎬 آماده شروع کار")
        self.lbl_app_name.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #F8FAFC;")
        top_row.addWidget(self.lbl_app_name, stretch=1)

        self.lbl_status_pill = QLabel("● سیستم پایدار")
        self.lbl_status_pill.setStyleSheet("""
            font-size: 11px;
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

        # ۲. تایل‌های ۳ گانه با استایل Ambient Glow
        grid_row = QHBoxLayout()
        grid_row.setSpacing(8)
        grid_row.setDirection(QHBoxLayout.Direction.LeftToRight)

        self.tile_cpu = HardwareMeterTile("CPU Processor", "#818CF8", "Detecting...", self)
        self.tile_ram = HardwareMeterTile("System RAM", "#38BDF8", "Detecting...", self)
        self.tile_gpu = HardwareMeterTile("GPU Graphics", "#F59E0B", "Detecting...", self)

        grid_row.addWidget(self.tile_cpu)
        grid_row.addWidget(self.tile_ram)
        grid_row.addWidget(self.tile_gpu)
        layout.addLayout(grid_row)

        layout.addStretch()

        # ۳. فوتر توضیحات
        self.lbl_auto_pilot = QLabel("⚡ مانیتورینگ زنده سخت‌افزار با هاله نوری و تغییر داینامیک ته‌رنگ کارت‌ها")
        self.lbl_auto_pilot.setStyleSheet("font-size: 9.5px; color: #64748B; padding-right: 2px;")
        layout.addWidget(self.lbl_auto_pilot)

    def update_metrics(self, data: dict):
        app = data.get("active_app", "General App")
        self.lbl_app_name.setText(f"🎬 {app}")

        state = data.get("state", "idle")
        is_rendering = data.get("is_rendering", False)

        hw_specs = data.get("hardware_specs", {})
        if hw_specs:
            # مشخصات پردازنده (CPU)
            cpu_name = hw_specs.get("cpu_name", "CPU")
            cores_cnt = hw_specs.get("cpu_cores", 8)
            self.tile_cpu.set_model_and_stat(cpu_name, f"{cores_cnt} Threads Active")

            # مشخصات حافظه رم (RAM)
            ram_used = data.get("ram_used_gb", 0.0)
            ram_tot = hw_specs.get("ram_total_gb", 16.0)
            ram_free = data.get("ram_free_gb", 0.0)
            self.tile_ram.set_model_and_stat(
                f"{ram_used:.1f} / {ram_tot:.1f} GB Used",
                f"{ram_free:.1f} GB Available"
            )

            # مشخصات کارت گرافیک (GPU & VRAM)
            gpu_name = hw_specs.get("gpu_name", "GPU")
            vram_used = data.get("vram_used_gb", 0.0)
            vram_tot = hw_specs.get("vram_total_gb", 0.0)
            
            if vram_tot > 0:
                vram_desc = f"{vram_used:.1f} / {vram_tot:.1f} GB VRAM"
            elif vram_used > 0:
                vram_desc = f"{vram_used:.1f} GB VRAM Used"
            else:
                vram_desc = "Dedicated GPU"

            self.tile_gpu.set_model_and_stat(gpu_name, vram_desc)

        # بج وضعیت
        if state == "editing":
            self.lbl_status_pill.setText("● تدوین فعال")
            self.lbl_status_pill.setStyleSheet("color: #10B981; background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3); border-radius: 6px; padding: 2px 8px; font-weight: 700;")
        elif state == "processing" or is_rendering:
            self.lbl_status_pill.setText("⚡ رندر / پردازش")
            self.lbl_status_pill.setStyleSheet("color: #38BDF8; background: rgba(56,189,248,0.12); border: 1px solid rgba(56,189,248,0.3); border-radius: 6px; padding: 2px 8px; font-weight: 700;")
        elif state in ["outside_editing", "distraction"]:
            self.lbl_status_pill.setText("○ سایر برنامه‌ها")
            self.lbl_status_pill.setStyleSheet("color: #F59E0B; background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.3); border-radius: 6px; padding: 3px 10px; font-weight: 600;")
        else:
            self.lbl_status_pill.setText("⏳ آماده‌به‌کار")
            self.lbl_status_pill.setStyleSheet("color: #94A3B8; background: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 2px 8px;")

        # درصدها و انیمیشن روان پر شدن
        cpu = int(data.get("cpu_percent", 0))
        ram = int(data.get("ram_percent", 0))
        gpu = int(data.get("gpu_percent", 0))

        self.tile_cpu.set_value_smooth(cpu)
        self.tile_ram.set_value_smooth(ram)
        self.tile_gpu.set_value_smooth(gpu)