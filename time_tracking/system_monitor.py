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

# لیست پروسه‌های نرم‌افزارهای اصلی تدوین
CORE_NLE_PROCESSES = {
    "adobe premiere pro.exe": "Premiere Pro",
    "premiere.exe": "Premiere Pro",
    "davinci resolve.exe": "DaVinci Resolve",
    "resolve.exe": "DaVinci Resolve",
    "afterfx.exe": "After Effects",
    "edius.exe": "EDIUS",
    "final cut pro": "Final Cut Pro"
}

# لیست پروسه‌های نرم‌افزارهای کمکی
SUPPORTING_PROCESSES = {
    "photoshop.exe": "Photoshop",
    "illustrator.exe": "Illustrator",
    "audition.exe": "Audition",
    "cubase.exe": "Cubase",
    "fl64.exe": "FL Studio"
}


def get_real_gpu_metrics() -> tuple[float, float, float, str]:
    """
    استخراج دقیق و واقعی درصد لود، VRAM مصرفی، کل VRAM و مدل GPU
    خروجی: (gpu_percent, vram_used_gb, vram_total_gb, gpu_name)
    """
    gpu_util = 0.0
    vram_used = 0.0
    vram_total = 0.0
    gpu_name = ""

    if sys.platform == "win32":
        # روش ۱: استفاده مستقیم و پایدار از nvidia-smi
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cmd = "nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
            output = subprocess.check_output(cmd, startupinfo=startupinfo, stderr=subprocess.DEVNULL, timeout=0.8).decode("utf-8").strip()
            if output:
                line = output.splitlines()[0]
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpu_name = parts[0].replace("NVIDIA GeForce", "").replace("NVIDIA", "").strip()
                    gpu_util = float(parts[1])
                    vram_used = round(float(parts[2]) / 1024.0, 1)
                    vram_total = round(float(parts[3]) / 1024.0, 1)
                    return gpu_util, vram_used, vram_total, gpu_name
        except Exception:
            pass

        # روش ۲: فال‌بک امن به WMI و PowerShell در صورت عدم حضور nvidia-smi
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            cmd = "powershell -NoProfile -Command \"Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json\""
            output = subprocess.check_output(cmd, startupinfo=startupinfo, stderr=subprocess.DEVNULL, timeout=1.0).decode("utf-8").strip()
            if output:
                import json
                data = json.loads(output)
                if isinstance(data, list):
                    item = data[0]
                else:
                    item = data
                gpu_name = item.get("Name", "GPU").replace("NVIDIA GeForce", "").replace("AMD Radeon", "Radeon").strip()
                vram_bytes = int(item.get("AdapterRAM", 0) or 0)
                if vram_bytes > 0:
                    vram_total = round(vram_bytes / (1024 ** 3), 1)
        except Exception:
            pass

    return gpu_util, vram_used, vram_total, gpu_name


def get_hardware_specifications() -> dict:
    specs = {
        "cpu_name": "پردازنده سیستم",
        "cpu_cores": psutil.cpu_count(logical=True) or 8,
        "gpu_name": "کارت گرافیک",
        "vram_total_gb": 0.0,
        "ram_total_gb": 16.0,
    }

    try:
        mem = psutil.virtual_memory()
        specs["ram_total_gb"] = round(mem.total / (1024 ** 3), 1)
    except Exception:
        pass

    try:
        if sys.platform == "win32":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_raw = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            winreg.CloseKey(key)
            specs["cpu_name"] = cpu_raw.strip().replace("Processor", "").replace("(R)", "").replace("(TM)", "").strip()
        elif sys.platform == "darwin":
            cmd = ["sysctl", "-n", "machdep.cpu.brand_string"]
            specs["cpu_name"] = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        else:
            specs["cpu_name"] = platform.processor() or "CPU"
    except Exception:
        specs["cpu_name"] = platform.processor() or "CPU"

    if "Intel" in specs["cpu_name"]:
        specs["cpu_name"] = specs["cpu_name"].replace("Intel Core", "Core").strip()
    elif "AMD" in specs["cpu_name"]:
        specs["cpu_name"] = specs["cpu_name"].replace("AMD Ryzen", "Ryzen").strip()

    _, _, vram_tot, live_gpu = get_real_gpu_metrics()
    if live_gpu:
        specs["gpu_name"] = live_gpu
        specs["vram_total_gb"] = vram_tot

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
    """ترد اختصاصی پایش زمان واقعی سخت‌افزار با نمونه‌برداری پیوسته"""
    metrics_updated = Signal(dict)

    def __init__(self, check_interval_sec: float = 1.5, parent=None):
        super().__init__(parent)
        self.check_interval_sec = check_interval_sec
        self._is_running = True
        self.hardware_specs = get_hardware_specifications()

    def run(self):
        # بارگذاری اولیه شمارنده پردازنده
        psutil.cpu_percent(interval=None)

        while self._is_running:
            try:
                # نمونه‌برداری پایدار ۰.۴ ثانیه‌ای برای محاسبه نرخ واقعی لود CPU
                cpu_pct = psutil.cpu_percent(interval=0.4)

                idle_sec = get_windows_idle_seconds()
                win_title, proc_name = get_active_window_process_info()

                active_app_label = "برنامه عمومی"
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

                # اندازه‌گیری دقیق و واقعی RAM
                vmem = psutil.virtual_memory()
                ram_pct = vmem.percent
                ram_used_gb = round((vmem.total - vmem.available) / (1024 ** 3), 1)
                ram_free_gb = round(vmem.available / (1024 ** 3), 1)

                # اندازه‌گیری دقیق و واقعی GPU
                gpu_pct, vram_used_gb, vram_total_gb, live_gpu_name = get_real_gpu_metrics()
                if live_gpu_name:
                    self.hardware_specs["gpu_name"] = live_gpu_name
                if vram_total_gb > 0:
                    self.hardware_specs["vram_total_gb"] = vram_total_gb

                is_rendering = (cpu_pct >= 45.0 or gpu_pct >= 40.0)

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
                    "ram_percent": float(ram_pct),
                    "ram_used_gb": ram_used_gb,
                    "ram_free_gb": ram_free_gb,
                    "gpu_percent": float(gpu_pct),
                    "vram_used_gb": vram_used_gb,
                    "is_rendering": is_rendering,
                    "is_core_nle": is_core_nle,
                    "is_supporting": is_supporting,
                    "hardware_specs": self.hardware_specs
                }

                self.metrics_updated.emit(payload)

            except Exception:
                pass

            time.sleep(max(0.4, self.check_interval_sec - 0.4))

    def stop(self):
        self._is_running = False
        self.wait(1000)