# ==================================================
# FILE: time_tracking/system_monitor.py
# ==================================================
import sys
import os
import time
import ctypes
import platform
import subprocess
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


def get_hardware_specifications() -> dict:
    """شناسایی خودکار و Cross-Platform مدل CPU، GPU و حجم کل RAM"""
    specs = {
        "cpu_name": "پردازنده سیستم",
        "gpu_name": "کارت گرافیک",
        "ram_total_str": "حافظه رم"
    }

    # ۱. محاسبه حجم کل رم
    try:
        total_ram_gb = round(psutil.virtual_memory().total / (1024 ** 3))
        specs["ram_total_str"] = f"{total_ram_gb} GB RAM"
    except Exception:
        specs["ram_total_str"] = "RAM"

    # ۲. شناسایی نام و مدل پردازنده (CPU)
    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_raw = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            winreg.CloseKey(key)
            specs["cpu_name"] = cpu_raw.strip().replace("Processor", "").replace("(R)", "").replace("(TM)", "").strip()
        elif sys.platform == "darwin":
            cmd = ["sysctl", "-n", "machdep.cpu.brand_string"]
            cpu_raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            specs["cpu_name"] = cpu_raw
        else:
            specs["cpu_name"] = platform.processor() or "CPU"
    except Exception:
        specs["cpu_name"] = platform.processor() or "CPU"

    # تمیزکاری نام CPU برای نمایش فشرده در تایل
    if "Intel" in specs["cpu_name"]:
        specs["cpu_name"] = specs["cpu_name"].replace("Intel Core", "Core").strip()
    elif "AMD" in specs["cpu_name"]:
        specs["cpu_name"] = specs["cpu_name"].replace("AMD Ryzen", "Ryzen").strip()

    # ۳. شناسایی نام و مدل کارت گرافیک (GPU)
    try:
        if sys.platform == "win32":
            # استفاده از دستور سبک و بدون پنجره wmic/powershell
            cmd = "powershell -NoProfile -Command \"Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name\""
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(
                cmd, 
                startupinfo=startupinfo, 
                stderr=subprocess.DEVNULL, 
                shell=False
            ).decode("utf-8", errors="ignore").strip().splitlines()

            # ترجیح کارت‌های مجزا (NVIDIA / AMD) نسبت به گرافیک آنبورد اینتل
            gpus = [g.strip() for g in output if g.strip()]
            if gpus:
                discrete_gpus = [g for g in gpus if "NVIDIA" in g or "Radeon" in g or "RTX" in g or "GTX" in g or "AMD" in g]
                target_gpu = discrete_gpus[0] if discrete_gpus else gpus[0]
                # کوتاه‌سازی نام تجاری برای تناسب باکس
                specs["gpu_name"] = target_gpu.replace("NVIDIA GeForce", "").replace("AMD Radeon", "Radeon").strip()
        elif sys.platform == "darwin":
            cmd = ["system_profiler", "SPDisplaysDataType"]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
            for line in output.splitlines():
                if "Chipset Model:" in line:
                    specs["gpu_name"] = line.split(":", 1)[1].strip()
                    break
        else:
            specs["gpu_name"] = "GPU"
    except Exception:
        specs["gpu_name"] = "GPU"

    return specs


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
        # شناسایی یک‌باره نام قطعات سخت‌افزار در زمان استارت
        self.hardware_specs = get_hardware_specifications()

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

                is_rendering = (cpu_pct >= 40.0 or gpu_pct >= 35.0)

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
                    "is_supporting": is_supporting,
                    "hardware_specs": self.hardware_specs
                }

                self.metrics_updated.emit(payload)

            except Exception:
                pass

            time.sleep(self.check_interval_sec)

    def stop(self):
        self._is_running = False
        self.wait(1000)