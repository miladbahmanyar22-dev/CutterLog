# ==================================================
# FILE: time_tracking/widgets/system_monitor_card.py
# ==================================================
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from core.signals import global_signals
from core.persian_utils import to_persian_numbers


class HardwareMeterTile(QFrame):
    """تایل مانیتورینگ منبع سخت‌افزاری همراه با نمایش دقیق مدل قطعه در زیر نوار پیشرفت"""
    def __init__(self, title: str, accent_color: str, default_model: str = "...", parent=None):
        super().__init__(parent)
        self.title = title
        self.accent_color = accent_color
        self.current_pct = 0
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
        self.setFixedHeight(74)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {self.accent_color}55;
                background-color: #1A2438;
            }}
            QLabel {{
                background: transparent;
                border: none;
                font-family: 'Vazirmatn';
            }}
        """)
        self.init_ui(default_model)

    def init_ui(self, default_model: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # ردیف عنوان و درصد
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        
        lbl_t = QLabel(self.title)
        lbl_t.setStyleSheet("font-size: 10.5px; font-weight: 600; color: #94A3B8;")
        top_row.addWidget(lbl_t)
        top_row.addStretch()

        self.lbl_val = QLabel("۰٪")
        self.lbl_val.setStyleSheet(f"font-family: 'Segoe UI', 'Vazirmatn'; font-size: 12.5px; font-weight: 800; color: {self.accent_color};")
        top_row.addWidget(self.lbl_val)

        layout.addLayout(top_row)

        # نوار باریک پیشرفت
        self.pb = QProgressBar()
        self.pb.setRange(0, 100)
        self.pb.setValue(0)
        self.pb.setFixedHeight(4)
        self.pb.setTextVisible(False)
        self.pb.setStyleSheet(f"""
            QProgressBar {{
                background-color: #0E131F;
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {self.accent_color}88, stop:1 {self.accent_color});
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.pb)

        # نمایش مدل دقیق سخت‌افزار در زیر خط پیشرفت
        self.lbl_model = QLabel(default_model)
        self.lbl_model.setStyleSheet("font-family: -apple-system, 'Segoe UI', 'Vazirmatn'; font-size: 9.5px; font-weight: 600; color: #64748B;")
        self.lbl_model.setWordWrap(False)
        layout.addWidget(self.lbl_model)

    def set_model_name(self, name: str):
        if name and self.lbl_model.text() != name:
            self.lbl_model.setText(name)
            self.lbl_model.setToolTip(name)

    def set_value_smooth(self, target_val: int):
        target_val = max(0, min(100, target_val))
        if abs(target_val - self.current_pct) < 2 and target_val != 0:
            return

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(self.current_pct)
        self.anim.setEndValue(target_val)
        self.anim.valueChanged.connect(self._on_anim_step)
        self.anim.start()
        self.current_pct = target_val

    def _on_anim_step(self, val):
        v = int(val)
        self.pb.setValue(v)
        self.lbl_val.setText(f"{to_persian_numbers(v)}٪")


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
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # ۱. هدر وضعیت و نام برنامه فعال
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_app_name = QLabel("🎬 Premiere Pro")
        self.lbl_app_name.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #F8FAFC;")
        top_row.addWidget(self.lbl_app_name, stretch=1)

        self.lbl_status_pill = QLabel("● تدوین فعال")
        self.lbl_status_pill.setStyleSheet("""
            font-size: 11px;
            font-weight: 700;
            color: #10B981;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 6px;
            padding: 3px 10px;
        """)
        top_row.addWidget(self.lbl_status_pill)
        layout.addLayout(top_row)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.05);")
        layout.addWidget(div)

        # ۲. تایل‌های ۳ گانه با مدل سخت‌افزار
        grid_row = QHBoxLayout()
        grid_row.setSpacing(8)

        self.tile_cpu = HardwareMeterTile("پردازنده (CPU)", "#818CF8", "در حال شناسایی...", self)
        self.tile_gpu = HardwareMeterTile("گرافیک (GPU)", "#38BDF8", "در حال شناسایی...", self)
        self.tile_ram = HardwareMeterTile("حافظه (RAM)", "#F59E0B", "در حال شناسایی...", self)

        grid_row.addWidget(self.tile_cpu)
        grid_row.addWidget(self.tile_gpu)
        grid_row.addWidget(self.tile_ram)
        layout.addLayout(grid_row)

        layout.addStretch()

        # ۳. فوتر هوشمند
        self.lbl_auto_pilot = QLabel("⚡ پایشگر هوشمند پایپ‌لاین: آماده تشخیص رندر و مدیریت زمان")
        self.lbl_auto_pilot.setStyleSheet("font-size: 10px; color: #64748B; padding-right: 2px;")
        layout.addWidget(self.lbl_auto_pilot)

    def update_metrics(self, data: dict):
        app = data.get("active_app", "برنامه عمومی")
        self.lbl_app_name.setText(f"🎬 {app}")

        state = data.get("state", "idle")
        is_rendering = data.get("is_rendering", False)

        # تنظیم مشخصات سخت‌افزار ارسالی از ترد مانیتورینگ
        hw_specs = data.get("hardware_specs", {})
        if hw_specs:
            self.tile_cpu.set_model_name(hw_specs.get("cpu_name", "CPU"))
            self.tile_gpu.set_model_name(hw_specs.get("gpu_name", "GPU"))
            self.tile_ram.set_model_name(hw_specs.get("ram_total_str", "RAM"))

        # وضعیت برچسب
        if state == "editing":
            self.lbl_status_pill.setText("● تدوین فعال")
            self.lbl_status_pill.setStyleSheet("color: #10B981; background: rgba(16,185,129,0.12); border: 1px solid rgba(16,185,129,0.3); border-radius: 6px; padding: 3px 10px; font-weight: 700;")
        elif state == "processing" or is_rendering:
            self.lbl_status_pill.setText("⚡ رندر / پردازش")
            self.lbl_status_pill.setStyleSheet("color: #38BDF8; background: rgba(56,189,248,0.12); border: 1px solid rgba(56,189,248,0.3); border-radius: 6px; padding: 3px 10px; font-weight: 700;")
        elif state in ["outside_editing", "distraction"]:
            self.lbl_status_pill.setText("○ سایر برنامه‌ها")
            self.lbl_status_pill.setStyleSheet("color: #F59E0B; background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.3); border-radius: 6px; padding: 3px 10px; font-weight: 600;")
        else:
            self.lbl_status_pill.setText("⏳ آماده‌به‌کار")
            self.lbl_status_pill.setStyleSheet("color: #94A3B8; background: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 3px 10px;")

        # مقداردهی درصدهای زنده با انیمیشن ملایم
        cpu = int(data.get("cpu_percent", 0))
        gpu = int(data.get("gpu_percent", 0))
        ram = int(data.get("ram_percent", 0))

        self.tile_cpu.set_value_smooth(cpu)
        self.tile_gpu.set_value_smooth(gpu)
        self.tile_ram.set_value_smooth(ram)