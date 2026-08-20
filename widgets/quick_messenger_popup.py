# ================================================== 
# FILE: widgets/quick_messenger_popup.py 
# ================================================== 
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QLabel, QWidget
from PySide6.QtCore import Qt, QPoint, QSize, QTimer
from core.icon_provider import IconProvider
from core.nle_messenger_helper import ClientMessengerHelper
from core.signals import global_signals


class QuickMessengerMiniPopup(QFrame):
    def __init__(self, project_data: dict, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.project_data = project_data
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        self.setObjectName("QuickMessengerContainer")
        self.setStyleSheet("""
            QFrame#QuickMessengerContainer {
                background-color: #121826;
                border: 1px solid rgba(99, 102, 241, 0.45);
                border-radius: 20px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        # دکمه تلگرام
        btn_tg = QPushButton("تلگرام")
        btn_tg.setIcon(IconProvider.get_icon("telegram", "#38BDF8", size=13))
        btn_tg.setIconSize(QSize(13, 13))
        btn_tg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_tg.setFixedHeight(28)
        btn_tg.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                font-size: 11px;
                font-weight: 700;
                color: #F8FAFC;
                background-color: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 14px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #0284C7;
                color: #FFFFFF;
            }
        """)
        btn_tg.clicked.connect(lambda: self._handle_send("telegram"))
        layout.addWidget(btn_tg)

        # دکمه واتساپ
        btn_wa = QPushButton("واتساپ")
        btn_wa.setIcon(IconProvider.get_icon("whatsapp", "#10B981", size=13))
        btn_wa.setIconSize(QSize(13, 13))
        btn_wa.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_wa.setFixedHeight(28)
        btn_wa.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                font-size: 11px;
                font-weight: 700;
                color: #F8FAFC;
                background-color: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 14px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #059669;
                color: #FFFFFF;
            }
        """)
        btn_wa.clicked.connect(lambda: self._handle_send("whatsapp"))
        layout.addWidget(btn_wa)

    def _handle_send(self, app_type: str):
        msg = ClientMessengerHelper.generate_client_message(self.project_data)
        ClientMessengerHelper.copy_message_to_clipboard(msg)
        ClientMessengerHelper.launch_messenger_app(app_type)
        global_signals.show_toast.emit(f"متن پیام کپی شد و {app_type.capitalize()} اجرا گردید.", "success")
        self.close()

    def show_beside_widget(self, target_widget: QWidget):
        self.adjustSize()
        glob_pos = target_widget.mapToGlobal(QPoint(0, 0))
        # قرارگیری نرم دقیقاً بالای دکمه یا کنار آن
        target_x = glob_pos.x() - (self.width() // 2) + (target_widget.width() // 2)
        target_y = glob_pos.y() - self.height() - 6
        if target_y < 50:
            target_y = glob_pos.y() + target_widget.height() + 6
        self.move(target_x, target_y)
        self.show()