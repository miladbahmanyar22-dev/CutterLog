# ==================================================
# FILE: time_tracking/system_monitor.py
# ==================================================
import sys
import time
import ctypes
import psutil
from PySide6.QtCore import QThread, Signal

# نرم‌افزارهای اصلی تدوین
CORE_NLE_PROCESSES = {
    "adobe premiere pro.exe": "Premiere Pro",
    "premiere.exe": "Premiere Pro",
    "davinci resolve.exe": "DaVinci Resolve",
    "resolve.exe": "DaVinci Resolve",
    "afterfx.exe": "After Effects",
    "edius.exe": "EDIUS",
    "final cut pro": "Final Cut Pro"
}

# نرم‌افزارهای کمکی و مجاز
SUPPORTING_PROCESSES = {
    "photoshop.exe": "Photoshop",
    "illustrator.exe": "Illustrator",
    "audition.exe": "Audition",
    "cubase.exe": "Cubase",
    "fl64.exe": "FL Studio"
}


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint)
    ]


def get_windows_idle_seconds() -> float:
    if sys.platform != "win32":
        return 0.0
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return 0.0


def get_active_window_process_info() -> tuple[str, str]:
    if sys.platform != "win32":
        return "Unknown", "Unknown"
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return "Desktop", "explorer.exe"

        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        win_title = buff.value or "Active Window"

        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        proc_name = ""
        if pid.value:
            proc = psutil.Process(pid.value)
            proc_name = proc.name().lower()

        return win_title, proc_name
    except Exception:
        return "Unknown", "Unknown"


class SystemActivityMonitorThread(QThread):
    metrics_updated = Signal(dict)

    def __init__(self, check_interval_sec: float = 1.0, parent=None):
        super().__init__(parent)
        self.check_interval_sec = check_interval_sec
        self._is_running = True

    def run(self):
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

        while self._is_running:
            try:
                idle_sec = get_windows_idle_seconds()
                win_title, proc_name = get_active_window_process_info()

                active_app_label = "برنامه متفرقه"
                is_core_nle = False
                is_supporting = False

                for exe_key, friendly_name in CORE_NLE_PROCESSES.items():
                    if exe_key in proc_name:
                        active_app_label = friendly_name
                        is_core_nle = True
                        break

                if not is_core_nle:
                    for exe_key, friendly_name in SUPPORTING_PROCESSES.items():
                        if exe_key in proc_name:
                            active_app_label = friendly_name
                            is_supporting = True
                            break

                cpu_pct = psutil.cpu_percent(interval=None)
                ram_pct = psutil.virtual_memory().percent
                gpu_pct = min(100.0, cpu_pct * 0.85) if cpu_pct > 65 else min(100.0, cpu_pct * 0.4)

                # تشخیص هوشمند رندر
                is_rendering = (cpu_pct >= 40.0 or gpu_pct >= 35.0)

                # ماشین وضعیت کاری (Context-Aware State Machine)
                if is_rendering:
                    current_state = "processing"
                elif is_core_nle:
                    current_state = "editing" if idle_sec <= 60 else "idle"
                elif is_supporting:
                    current_state = "supporting" if idle_sec <= 45 else "idle"
                else:
                    current_state = "away" if idle_sec > 45 else "distraction"

                payload = {
                    "active_app": active_app_label,
                    "window_title": win_title,
                    "state": current_state,
                    "idle_seconds": int(idle_sec),
                    "cpu_percent": float(cpu_pct),
                    "gpu_percent": float(gpu_pct),
                    "ram_percent": float(ram_pct),
                    "is_rendering": is_rendering,
                    "is_core_nle": is_core_nle,
                    "is_supporting": is_supporting
                }

                self.metrics_updated.emit(payload)

            except Exception:
                pass

            time.sleep(self.check_interval_sec)

    def stop(self):
        self._is_running = False
        self.wait(1000)