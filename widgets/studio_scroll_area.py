# ==================================================
# FILE: widgets/studio_scroll_area.py
# ==================================================
from PySide6.QtWidgets import QScrollArea, QFrame, QWidget
from PySide6.QtCore import Qt


class StudioScrollArea(QScrollArea):
    """
    کامپوننت اسکرول استاندارد، فریم‌لس و یکپارچه استودیو
    دارای پشتیبانی خودکار از حالت RTL، پس‌زمینه شفاف و اسکرول‌بار هماهنگ
    """
    def __init__(self, parent=None, horizontal_scroll: bool = False):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

        if not horizontal_scroll:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def set_content_widget(self, widget: QWidget):
        """تنظیم ویجت محتوا همراه با شفاف‌سازی پس‌زمینه"""
        widget.setStyleSheet("background: transparent;")
        self.setWidget(widget)