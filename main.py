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

# استایل شیشه‌ای دودی با نور ملایم نیلی و کادر نئونی محو
GLOBAL_QMENU_STYLE = """
QMenu {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #161F32, stop:0.5 #111726, stop:1 #0D121F);
    border: 1px solid rgba(129, 140, 248, 0.45);
    border-top: 1px solid rgba(165, 180, 252, 0.65);
    border-radius: 10px;
    padding: 6px 4px;
    font-family: 'Vazirmatn';
}

QMenu::item {
    background-color: transparent;
    color: #F1F5F9;
    font-family: 'Vazirmatn';
    font-size: 11.5px;
    font-weight: 600;
    padding: 8px 18px 8px 18px;
    border-radius: 6px;
    margin: 2px 4px;
}

QMenu::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366F1, stop:1 #4F46E5);
    color: #FFFFFF;
    border: 1px solid rgba(255, 255, 255, 0.15);
}

QMenu::item:disabled {
    color: #475569;
    background-color: transparent;
}

QMenu::separator {
    height: 1px;
    background-color: rgba(255, 255, 255, 0.08);
    margin: 5px 8px;
}

QMenu::icon {
    padding-left: 8px;
}
"""


def bootstrap_app():
    if sys.platform == "win32":
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    
    # تنظیم آیکون سراسری برنامه برای نوار عنوان و تسک‌بار
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
    
    loaded_qss = ""
    for qss_p in qss_paths:
        try:
            if qss_p.exists():
                with open(str(qss_p.resolve()), "r", encoding="utf-8") as f:
                    loaded_qss = f.read()
                break
        except Exception as e:
            print(f"QSS load notice for {qss_p}: {e}")

    # ادغام با استایل اختصاصی QMenu
    app.setStyleSheet(loaded_qss + "\n" + GLOBAL_QMENU_STYLE)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    bootstrap_app()