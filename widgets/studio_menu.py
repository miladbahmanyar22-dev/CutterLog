# ==================================================
# FILE: widgets/studio_menu.py
# ==================================================
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon, QAction


class StudioMenu(QMenu):
    """
    منوی استاندارد، سبک و راست‌چین استودیو با استایل دارک سرمه‌ای و متالیک.
    کاملاً هماهنگ با پردازش رویدادهای QAction برای عملکرد ۱۰۰٪ تضمینی کلیک‌ها.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.setStyleSheet("""
            QMenu {
                background-color: #121826;
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 8px;
                padding: 5px 4px;
            }

            QMenu::item {
                background-color: transparent;
                color: #F1F5F9;
                font-family: 'Vazirmatn';
                font-size: 11px;
                font-weight: 600;
                padding: 7px 14px 7px 24px;
                border-radius: 5px;
                margin: 2px 2px;
            }

            QMenu::item:selected {
                background-color: #1E283D;
                color: #FFFFFF;
            }

            QMenu::item:disabled {
                color: #475569;
                background-color: transparent;
            }

            QMenu::separator {
                height: 1px;
                background-color: rgba(255, 255, 255, 0.07);
                margin: 4px 6px;
            }

            QMenu::icon {
                padding-right: 4px;
            }
        """)

    def show_beside_button(self, anchor_btn):
        """نمایش منو دقیقاً زیر دکمه احضارکننده و بازگرداندن اکشن انتخاب‌شده"""
        point = anchor_btn.mapToGlobal(QPoint(0, anchor_btn.height() + 2))
        return self.exec(point)