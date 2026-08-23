# ==================================================
# FILE: config.py
# ==================================================
import sys
import os
import subprocess
from pathlib import Path

APP_NAME = "CutterLog"
APP_VERSION = "1.0.3"

# ----------------------------------------------------
# 1. مدیریت مسیرهای استاندارد ذخیره‌سازی داده (Cross-Platform)
# ----------------------------------------------------
if sys.platform == "win32":
    APP_DATA_DIR = Path.home() / "AppData" / "Roaming" / APP_NAME
elif sys.platform == "darwin":
    APP_DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
else:
    APP_DATA_DIR = Path.home() / ".local" / "share" / APP_NAME

APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DATA_DIR / "cutterlog.db"


# ----------------------------------------------------
# 2. هلپر داینامیک پیدا کردن Assetها
# ----------------------------------------------------
def get_bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def get_asset_path(relative_path: str) -> Path:
    base = get_bundle_dir()
    return base / relative_path


# ----------------------------------------------------
# 3. هلپر استاندارد باز کردن پوشه بدون باز شدن پنجره کنسول سیاه
# ----------------------------------------------------
def open_path_in_os(path_str: str) -> bool:
    if not path_str or not os.path.exists(path_str):
        return False
    try:
        resolved = str(Path(path_str).resolve())
        if sys.platform == "win32":
            os.startfile(resolved)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", resolved], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", resolved], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"Error opening path in OS: {e}")
        return False


# ----------------------------------------------------
# 4. پالت رنگی و استیج‌های پایپ‌لاین
# ----------------------------------------------------
COLORS = {
    "bg_base": "#121826",
    "bg_surface": "#161F30",
    "bg_input": "#242E42",
    "border": "rgba(255, 255, 255, 0.08)",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "accent": "#6366F1",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}

PIPELINE_STAGES = {
    "rough_cut": {"label": "راف‌کات", "color": "#38BDF8"},
    "color_grading": {"label": "اصلاح رنگ و نور", "color": "#C084FC"},
    "audio_vfx": {"label": "صداگذاری و VFX", "color": "#FBBF24"},
    "client_review": {"label": "بازبینی کارفرما", "color": "#FB923C"},
    "final_render": {"label": "رندر نهایی", "color": "#818CF8"},
    "delivered": {"label": "تحویل داده شده", "color": "#34D399"},
}