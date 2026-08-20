# ==================================================
# FILE: main.py
# ==================================================
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from config import get_asset_path
from core.font_manager import FontManager
from core.app_setup import initialize_application
from views.main_window import MainWindow


def bootstrap_app():
    if sys.platform == "win32":
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    
    # ----------------------------------------------------
    # تنظیم آیکون سراسری برنامه برای نوار عنوان و تسک‌بار
    # ----------------------------------------------------
    icon_path = get_asset_path("assets/icons/icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path.resolve())))

    # راه‌اندازی زیرساخت‌های پایه (دیتابیس، پوشه‌ها، تنظیمات)
    initialize_application()

    # اعمال فونت و تم
    app_font = FontManager.get_font(size=10, weight=QFont.Weight.Normal)
    app.setFont(app_font)

    qss_paths = [
        get_asset_path("styles/dark_theme.qss"),
        Path(__file__).resolve().parent / "styles" / "dark_theme.qss",
        Path("styles/dark_theme.qss"),
    ]
    
    for qss_p in qss_paths:
        try:
            if qss_p.exists():
                with open(str(qss_p.resolve()), "r", encoding="utf-8") as f:
                    app.setStyleSheet(f.read())
                break
        except Exception as e:
            print(f"QSS load notice for {qss_p}: {e}")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    bootstrap_app()