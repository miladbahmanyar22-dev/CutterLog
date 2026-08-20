# ==================================================
# FILE: time_tracking/widgets/system_monitor_card.py
# ==================================================
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt
from core.signals import global_signals
from core.persian_utils import to_persian_numbers


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
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # سربرگ وضعیت و نام برنامه
        top_row = QHBoxLayout()
        self.lbl_app_name = QLabel("🎬 Premiere Pro")
        self.lbl_app_name.setStyleSheet("font-size: 13px; font-weight: 800; color: #F8FAFC;")
        top_row.addWidget(self.lbl_app_name, stretch=1)

        self.lbl_status_pill = QLabel("● تدوین فعال")
        self.lbl_status_pill.setStyleSheet("""
            font-size: 11px;
            font-weight: 800;
            color: #10B981;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 10px;
            padding: 2px 8px;
        """)
        top_row.addWidget(self.lbl_status_pill)
        layout.addLayout(top_row)

        # خط جداکننده محو
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: rgba(255, 255, 255, 0.04);")
        layout.addWidget(div)

        # متریک‌های سخت‌افزار
        self.cpu_bar = self._create_bar_row("پردازنده (CPU):", "#6366F1")
        self.gpu_bar = self._create_bar_row("کارت گرافیک (GPU):", "#38BDF8")
        self.ram_bar = self._create_bar_row("حافظه رم (RAM):", "#F59E0B")

        layout.addLayout(self.cpu_bar["layout"])
        layout.addLayout(self.gpu_bar["layout"])
        layout.addLayout(self.ram_bar["layout"])

        # وضعیت خودکار خلبان هوشمند
        self.lbl_auto_pilot = QLabel("⚡ پایشگر هوشمند: فعال (تشخیص خودکار رندر و توقف عدم تعامل)")
        self.lbl_auto_pilot.setStyleSheet("font-size: 10px; color: #64748B; padding-top: 2px;")
        layout.addWidget(self.lbl_auto_pilot)

    def _create_bar_row(self, title: str, accent_color: str) -> dict:
        row = QHBoxLayout()
        row.setSpacing(6)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 11px; color: #94A3B8; min-width: 95px;")
        row.addWidget(lbl_t)

        pb = QProgressBar()
        pb.setRange(0, 100)
        pb.setFixedHeight(4)
        pb.setTextVisible(False)
        pb.setStyleSheet(f"""
            QProgressBar {{
                background-color: #161F30;
                border-radius: 2px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {accent_color};
                border-radius: 2px;
            }}
        """)
        row.addWidget(pb, stretch=1)

        lbl_val = QLabel("۰٪")
        lbl_val.setStyleSheet("font-family: 'Segoe UI'; font-size: 11px; font-weight: 700; color: #F8FAFC; min-width: 32px; text-align: left;")
        row.addWidget(lbl_val)

        return {"layout": row, "bar": pb, "val": lbl_val}

    def update_metrics(self, data: dict):
        app = data.get("active_app", "برنامه عمومی")
        self.lbl_app_name.setText(f"🎬 {app}")

        state = data.get("state", "idle")
        is_rendering = data.get("is_rendering", False)

        if state == "editing":
            self.lbl_status_pill.setText("● تدوین فعال")
            self.lbl_status_pill.setStyleSheet("color: #10B981; background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); border-radius: 10px; padding: 2px 8px; font-weight: 800;")
        elif state == "processing" or is_rendering:
            self.lbl_status_pill.setText("⚡ رندر / پردازش فعال")
            self.lbl_status_pill.setStyleSheet("color: #38BDF8; background: rgba(56,189,248,0.15); border: 1px solid rgba(56,189,248,0.3); border-radius: 10px; padding: 2px 8px; font-weight: 800;")
        elif state == "outside_editing":
            self.lbl_status_pill.setText("○ سایر برنامه‌ها")
            self.lbl_status_pill.setStyleSheet("color: #F59E0B; background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3); border-radius: 10px; padding: 2px 8px; font-weight: 700;")
        else:
            idle_s = data.get("idle_seconds", 0)
            self.lbl_status_pill.setText(f"⏳ بدون تعامل ({to_persian_numbers(idle_s)}s)")
            self.lbl_status_pill.setStyleSheet("color: #94A3B8; background: #161F30; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 2px 8px;")

        cpu = int(data.get("cpu_percent", 0))
        self.cpu_bar["bar"].setValue(cpu)
        self.cpu_bar["val"].setText(f"{to_persian_numbers(cpu)}٪")

        gpu = int(data.get("gpu_percent", 0))
        self.gpu_bar["bar"].setValue(gpu)
        self.gpu_bar["val"].setText(f"{to_persian_numbers(gpu)}٪")

        ram = int(data.get("ram_percent", 0))
        self.ram_bar["bar"].setValue(ram)
        self.ram_bar["val"].setText(f"{to_persian_numbers(ram)}٪")