# ==================================================
# FILE: core/font_manager.py
# ==================================================
import sys
from pathlib import Path
from PySide6.QtGui import QFontDatabase, QFont
from config import get_asset_path, get_bundle_dir


class FontManager:
    FONT_FAMILY = "Vazirmatn"

    @classmethod
    def load_fonts(cls) -> bool:
        """
        اسکن و بارگذاری خودکار تمام وزن‌های فونت وزیرمتن با پشتیبانی کامل
        از حالت Development و پکیج‌های کامپایل‌شده (.app در macOS و .exe در Windows)
        """
        candidate_dirs = [
            get_asset_path("fonts"),
            get_asset_path("assets/fonts"),
            get_asset_path("styles/fonts"),
            get_bundle_dir() / "fonts",
            get_bundle_dir() / "assets" / "fonts",
            Path(__file__).resolve().parent.parent / "fonts",
            Path(__file__).resolve().parent.parent / "assets" / "fonts",
            Path("fonts"),
            Path("assets/fonts"),
        ]

        loaded_any = False
        seen_dirs = set()

        for font_dir in candidate_dirs:
            try:
                resolved_dir = font_dir.resolve()
                if resolved_dir in seen_dirs or not resolved_dir.exists() or not resolved_dir.is_dir():
                    continue
                seen_dirs.add(resolved_dir)

                for font_file in resolved_dir.glob("*.[tT][tT][fF]"):
                    font_id = QFontDatabase.addApplicationFont(str(font_file.resolve()))
                    if font_id != -1:
                        loaded_any = True

                for font_file in resolved_dir.glob("*.[oO][tT][fF]"):
                    font_id = QFontDatabase.addApplicationFont(str(font_file.resolve()))
                    if font_id != -1:
                        loaded_any = True
            except Exception as e:
                print(f"Font scan notice for {font_dir}: {e}")

        return loaded_any

    @classmethod
    def get_font(cls, size: int = 10, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
        """
        دریافت شیء QFont استاندارد با سیستم Fallback مناسب برای هر دو سیستم‌عامل
        """
        font = QFont(cls.FONT_FAMILY, size)
        font.setWeight(weight)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        
        # Fallback برای مک در صورتی که فونت وزیرمتن در دسترس نباشد
        if sys.platform == "darwin":
            font.setStyleHint(QFont.StyleHint.SansSerif)
            
        return font