# ==================================================
# FILE: time_tracking/system_monitor.py
# ==================================================
import sys
import os
import time
import ctypes
from ctypes import wintypes
from typing import Dict, Any, Optional, Tuple, List
import psutil
from PySide6.QtCore import QThread, Signal

if sys.platform == "win32":
    import winreg

# -------------------------------------------------------------------------
# ساختارها و APIهای Win32 Native
# -------------------------------------------------------------------------

class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD)
    ]

    def to_uint64(self) -> int:
        return (self.dwHighDateTime << 32) | self.dwLowDateTime


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]

    def __init__(self):
        super().__init__()
        self.dwLength = ctypes.sizeof(self)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint)
    ]


kernel32 = None
user32 = None
pdh = None

if sys.platform == "win32":
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
    except Exception:
        pass

    try:
        pdh = ctypes.WinDLL("pdh", use_last_error=True)
    except Exception:
        pass


CORE_NLE_PROCESSES = {
    "adobe premiere pro.exe": "Premiere Pro",
    "premiere.exe": "Premiere Pro",
    "davinci resolve.exe": "DaVinci Resolve",
    "resolve.exe": "DaVinci Resolve",
    "afterfx.exe": "After Effects",
    "edius.exe": "EDIUS",
    "final cut pro": "Final Cut Pro"
}

SUPPORTING_PROCESSES = {
    "photoshop.exe": "Photoshop",
    "illustrator.exe": "Illustrator",
    "audition.exe": "Audition",
    "cubase.exe": "Cubase",
    "fl64.exe": "FL Studio"
}


# =========================================================================
# ۱. مانیتور پردازنده (CPU Monitor) با GetSystemTimes
# =========================================================================
class Win32CpuMonitor:
    def __init__(self):
        self._prev_idle: int = 0
        self._prev_kernel: int = 0
        self._prev_user: int = 0
        self._initialized = False

        self.cpu_name = "Processor"
        self.physical_cores = psutil.cpu_count(logical=False) or 4
        self.logical_processors = psutil.cpu_count(logical=True) or 8
        self._detect_cpu_specs()
        self._sample_initial_times()

    def _detect_cpu_specs(self):
        try:
            if sys.platform == "win32":
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                cpu_raw = winreg.QueryValueEx(key, "ProcessorNameString")[0]
                winreg.CloseKey(key)
                name = cpu_raw.strip().replace("Processor", "").replace("(R)", "").replace("(TM)", "").strip()
                if "Intel" in name:
                    name = name.replace("Intel Core", "Core").strip()
                elif "AMD" in name:
                    name = name.replace("AMD Ryzen", "Ryzen").strip()
                self.cpu_name = name
        except Exception:
            pass

    def _sample_initial_times(self):
        if not kernel32:
            return
        idle = FILETIME()
        kernel = FILETIME()
        user = FILETIME()
        if kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            self._prev_idle = idle.to_uint64()
            self._prev_kernel = kernel.to_uint64()
            self._prev_user = user.to_uint64()
            self._initialized = True

    def get_cpu_metrics(self) -> Tuple[float, float, str]:
        cpu_usage = 0.0
        current_freq_ghz = 0.0

        if kernel32 and self._initialized:
            idle = FILETIME()
            kernel = FILETIME()
            user = FILETIME()
            if kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                cur_idle = idle.to_uint64()
                cur_kernel = kernel.to_uint64()
                cur_user = user.to_uint64()

                delta_idle = cur_idle - self._prev_idle
                delta_kernel = cur_kernel - self._prev_kernel
                delta_user = cur_user - self._prev_user

                total_sys = delta_kernel + delta_user
                if total_sys > 0:
                    idle_ratio = delta_idle / total_sys
                    cpu_usage = max(0.0, min(100.0, (1.0 - idle_ratio) * 100.0))

                self._prev_idle = cur_idle
                self._prev_kernel = cur_kernel
                self._prev_user = cur_user
        else:
            cpu_usage = psutil.cpu_percent(interval=None)

        try:
            freq = psutil.cpu_freq()
            if freq and getattr(freq, "current", 0) > 0:
                current_freq_ghz = round(freq.current / 1000.0, 2)
        except Exception:
            pass

        freq_str = f"{current_freq_ghz:.2f} GHz" if current_freq_ghz > 0 else "N/A"
        return round(cpu_usage, 1), current_freq_ghz, freq_str


# =========================================================================
# ۲. مانیتور حافظه رم (Memory Monitor) با GlobalMemoryStatusEx
# =========================================================================
class Win32MemoryMonitor:
    def get_memory_metrics(self) -> Dict[str, Any]:
        if kernel32:
            status = MEMORYSTATUSEX()
            if kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                total_bytes = status.ullTotalPhys
                avail_bytes = status.ullAvailPhys
                used_bytes = total_bytes - avail_bytes

                total_gb = round(total_bytes / (1024 ** 3), 1)
                used_gb = round(used_bytes / (1024 ** 3), 1)
                avail_gb = round(avail_bytes / (1024 ** 3), 1)
                usage_pct = round((used_bytes / total_bytes) * 100.0, 1) if total_bytes > 0 else 0.0

                return {
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "avail_gb": avail_gb,
                    "percent": usage_pct
                }

        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024 ** 3), 1),
            "used_gb": round((mem.total - mem.available) / (1024 ** 3), 1),
            "avail_gb": round(mem.available / (1024 ** 3), 1),
            "percent": round(mem.percent, 1)
        }


# =========================================================================
# ۳. مانیتور کارت گرافیک (GPU Engine & VRAM Monitor)
# =========================================================================
class NativeGpuMonitor:
    def __init__(self):
        self.gpu_name: str = "Graphics"
        self.vram_total_gb: float = 0.0
        self.has_dedicated_gpu: bool = False
        self._pdh_query = None
        self._counter_handles: Dict[str, Any] = {}
        self._has_pdh_engine_counters = False
        self._nvml_initialized = False
        self._nvml_handle = None
        self._nvml_dll = None

        self._init_hardware_info()
        self._init_nvml_fallback()
        self._init_pdh_counters()

    def _init_hardware_info(self):
        if sys.platform != "win32":
            return
        try:
            base_key = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_key) as k:
                sub_count = winreg.QueryInfoKey(k)[0]
                for i in range(sub_count):
                    try:
                        sub_name = winreg.EnumKey(k, i)
                        if not sub_name.isdigit():
                            continue
                        with winreg.OpenKey(k, sub_name) as dev_key:
                            name = winreg.QueryValueEx(dev_key, "DriverDesc")[0]
                            if "NVIDIA" in name or "AMD" in name or "Radeon" in name or "Intel" in name:
                                self.gpu_name = name.replace("NVIDIA GeForce ", "").replace("NVIDIA ", "").replace("AMD Radeon ", "").strip()
                                try:
                                    vram_raw = winreg.QueryValueEx(dev_key, "HardwareInformation.qwMemorySize")[0]
                                    if vram_raw > 0:
                                        self.vram_total_gb = round(vram_raw / (1024 ** 3), 1)
                                        self.has_dedicated_gpu = True
                                        break
                                except Exception:
                                    pass
                    except Exception:
                        continue
        except Exception:
            pass

    def _init_nvml_fallback(self):
        if sys.platform != "win32":
            return
        try:
            nvml = ctypes.CDLL("nvml.dll")
            if nvml.nvmlInit_v2() == 0:
                handle = ctypes.c_void_p()
                if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) == 0:
                    self._nvml_handle = handle
                    self._nvml_dll = nvml
                    self._nvml_initialized = True
        except Exception:
            self._nvml_initialized = False

    def _init_pdh_counters(self):
        if not pdh:
            return
        try:
            self._pdh_query = ctypes.c_void_p()
            status = pdh.PdhOpenQueryW(None, 0, ctypes.byref(self._pdh_query))
            if status != 0:
                self._pdh_query = None
                return

            self._engine_counter_names = {
                "3d": r"\GPU Engine(*engtype_3D*)\Utilization Percentage",
                "encode": r"\GPU Engine(*engtype_VideoEncode*)\Utilization Percentage",
                "decode": r"\GPU Engine(*engtype_VideoDecode*)\Utilization Percentage",
                "copy": r"\GPU Engine(*engtype_Copy*)\Utilization Percentage",
                "compute": r"\GPU Engine(*engtype_Compute*)\Utilization Percentage",
            }

            for eng, path in self._engine_counter_names.items():
                h_counter = ctypes.c_void_p()
                res = pdh.PdhAddCounterW(self._pdh_query, path, 0, ctypes.byref(h_counter))
                if res == 0:
                    self._counter_handles[eng] = h_counter

            if self._counter_handles:
                pdh.PdhCollectQueryData(self._pdh_query)
                self._has_pdh_engine_counters = True
        except Exception:
            self._has_pdh_engine_counters = False

    def get_gpu_metrics(self) -> Dict[str, Any]:
        metrics = {
            "gpu_name": self.gpu_name,
            "overall_pct": 0.0,
            "engine_3d": "N/A",
            "engine_encode": "N/A",
            "engine_decode": "N/A",
            "engine_copy": "N/A",
            "engine_compute": "N/A",
            "vram_used_gb": 0.0,
            "vram_total_gb": self.vram_total_gb,
            "vram_percent": 0.0,
            "temperature_c": "N/A"
        }

        if self._nvml_initialized and self._nvml_dll and self._nvml_handle:
            try:
                class c_nvmlMemory_t(ctypes.Structure):
                    _fields_ = [
                        ("total", ctypes.c_ulonglong),
                        ("free", ctypes.c_ulonglong),
                        ("used", ctypes.c_ulonglong)
                    ]

                class c_nvmlUtilization_t(ctypes.Structure):
                    _fields_ = [
                        ("gpu", ctypes.c_uint),
                        ("memory", ctypes.c_uint)
                    ]

                mem_info = c_nvmlMemory_t()
                if self._nvml_dll.nvmlDeviceGetMemoryInfo(self._nvml_handle, ctypes.byref(mem_info)) == 0:
                    metrics["vram_total_gb"] = round(mem_info.total / (1024 ** 3), 1)
                    metrics["vram_used_gb"] = round(mem_info.used / (1024 ** 3), 1)
                    if mem_info.total > 0:
                        metrics["vram_percent"] = round((mem_info.used / mem_info.total) * 100.0, 1)

                util_info = c_nvmlUtilization_t()
                if self._nvml_dll.nvmlDeviceGetUtilizationRates(self._nvml_handle, ctypes.byref(util_info)) == 0:
                    metrics["overall_pct"] = float(util_info.gpu)

                temp = ctypes.c_uint()
                if self._nvml_dll.nvmlDeviceGetTemperature(self._nvml_handle, 0, ctypes.byref(temp)) == 0:
                    metrics["temperature_c"] = f"{temp.value}°C"
            except Exception:
                pass

        if pdh and self._has_pdh_engine_counters and self._pdh_query:
            try:
                pdh.PdhCollectQueryData(self._pdh_query)

                class PDH_FMT_COUNTERVALUE(ctypes.Structure):
                    _fields_ = [
                        ("CStatus", wintypes.DWORD),
                        ("doubleValue", ctypes.c_double)
                    ]

                max_engine = 0.0
                for eng_key, h_counter in self._counter_handles.items():
                    val = PDH_FMT_COUNTERVALUE()
                    status = pdh.PdhGetFormattedCounterValue(h_counter, 0x00000200, None, ctypes.byref(val))
                    if status == 0 and val.CStatus == 0:
                        v = max(0.0, min(100.0, val.doubleValue))
                        metrics[f"engine_{eng_key}"] = f"{v:.1f}%"
                        if v > max_engine:
                            max_engine = v

                if metrics["overall_pct"] == 0.0 and max_engine > 0:
                    metrics["overall_pct"] = round(max_engine, 1)
            except Exception:
                pass

        if metrics["overall_pct"] == 0.0 and metrics["engine_3d"] != "N/A":
            try:
                metrics["overall_pct"] = float(metrics["engine_3d"].replace("%", ""))
            except Exception:
                pass

        return metrics

    def close(self):
        if pdh and self._pdh_query:
            try:
                pdh.PdhCloseQuery(self._pdh_query)
            except Exception:
                pass
            self._pdh_query = None


# =========================================================================
# ۴. مانیتور مصرف اختصاصی خود نرم‌‌افزار CutterLog
# =========================================================================
class CutterLogProcessMonitor:
    def __init__(self):
        self._process = psutil.Process(os.getpid())
        self._process.cpu_percent(interval=None)

    def get_cutterlog_metrics(self) -> Dict[str, Any]:
        try:
            total_cores = psutil.cpu_count(logical=True) or 1
            cpu_pct = self._process.cpu_percent(interval=None) / total_cores
            mem_bytes = self._process.memory_info().rss
            mem_mb = round(mem_bytes / (1024 * 1024), 1)

            return {
                "cpu_percent": round(cpu_pct, 1),
                "ram_mb": mem_mb
            }
        except Exception:
            return {"cpu_percent": 0.0, "ram_mb": 0.0}


# =========================================================================
# ۵. سرویس پس‌زمینه (Sampling پایدار ۵ ثانیه‌ای)
# =========================================================================
def get_windows_idle_seconds() -> float:
    if sys.platform != "win32" or not user32 or not kernel32:
        return 0.0
    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = kernel32.GetTickCount() - lii.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return 0.0


def get_active_window_process_info() -> Tuple[str, str]:
    if sys.platform != "win32" or not user32:
        return "Unknown", "Unknown"
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "Desktop", "explorer.exe"

        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        win_title = buff.value or "Active Window"

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        proc_name = ""
        if pid.value:
            proc = psutil.Process(pid.value)
            proc_name = proc.name().lower()

        return win_title, proc_name
    except Exception:
        return "Unknown", "Unknown"


class SystemActivityMonitorThread(QThread):
    metrics_updated = Signal(dict)

    def __init__(self, check_interval_sec: float = 5.0, parent=None):
        super().__init__(parent)
        self.check_interval_sec = max(3.0, check_interval_sec)
        self._is_running = True

        self.cpu_monitor = Win32CpuMonitor()
        self.mem_monitor = Win32MemoryMonitor()
        self.gpu_monitor = NativeGpuMonitor()
        self.process_monitor = CutterLogProcessMonitor()

    def run(self):
        while self._is_running:
            try:
                start_loop = time.time()

                cpu_usage, _, freq_str = self.cpu_monitor.get_cpu_metrics()
                mem_data = self.mem_monitor.get_memory_metrics()
                gpu_data = self.gpu_monitor.get_gpu_metrics()
                proc_data = self.process_monitor.get_cutterlog_metrics()

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

                gpu_overall = gpu_data.get("overall_pct", 0.0)
                is_rendering = (cpu_usage >= 55.0 or gpu_overall >= 45.0)

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
                    "is_rendering": is_rendering,
                    "is_core_nle": is_core_nle,
                    "is_supporting": is_supporting,

                    # CPU
                    "cpu_percent": cpu_usage,
                    "cpu_name": self.cpu_monitor.cpu_name,
                    "cpu_cores": self.cpu_monitor.physical_cores,
                    "cpu_threads": self.cpu_monitor.logical_processors,
                    "cpu_freq_str": freq_str,

                    # RAM
                    "ram_percent": mem_data["percent"],
                    "ram_used_gb": mem_data["used_gb"],
                    "ram_total_gb": mem_data["total_gb"],
                    "ram_free_gb": mem_data["avail_gb"],

                    # GPU
                    "gpu_name": gpu_data["gpu_name"],
                    "gpu_percent": gpu_overall,
                    "gpu_3d": gpu_data["engine_3d"],
                    "gpu_encode": gpu_data["engine_encode"],
                    "gpu_decode": gpu_data["engine_decode"],
                    "gpu_copy": gpu_data["engine_copy"],
                    "vram_used_gb": gpu_data["vram_used_gb"],
                    "vram_total_gb": gpu_data["vram_total_gb"],
                    "vram_percent": gpu_data["vram_percent"],
                    "gpu_temp": gpu_data["temperature_c"],

                    # CutterLog
                    "cutterlog_cpu_pct": proc_data["cpu_percent"],
                    "cutterlog_ram_mb": proc_data["ram_mb"]
                }

                self.metrics_updated.emit(payload)

                elapsed = time.time() - start_loop
                sleep_time = max(0.5, self.check_interval_sec - elapsed)
                time.sleep(sleep_time)

            except Exception:
                time.sleep(1.0)

        self.gpu_monitor.close()

    def stop(self):
        self._is_running = False
        self.wait(1000)