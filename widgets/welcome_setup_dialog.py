# ================================================== 
# FILE: widgets/welcome_setup_dialog.py 
# ================================================== 
from pathlib import Path
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QSize
from core.settings_manager import SettingsManager
from core.icon_provider import IconProvider
from core.signals import global_signals
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog


class WelcomeSetupDialog(StudioBaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("خوش‌آمدید به CutterLog Pro")
        self.setFixedWidth(520)
        self.settings = SettingsManager.load_settings()
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "راه‌اندازی اولیه استودیو (Setup Wizard)",
            "جهت شخصی‌سازی فاکتورها، شناسنامه و پیام‌ها اطلاعات زیر را وارد کنید.",
            icon_name="clp_brand_mark",
            icon_color="#6366F1"
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)

        # ۱. مشخصات فردی
        form_layout.addWidget(QLabel("نام و نام خانوادگی تدوین‌گر:*"))
        self.input_editor = QLineEdit()
        self.input_editor.setFixedHeight(36)
        self.input_editor.setPlaceholderText("مثال: میلاد بهمنیار")
        self.input_editor.setStyleSheet(self._input_style())
        form_layout.addWidget(self.input_editor)

        # ۲. نام استودیو
        form_layout.addWidget(QLabel("نام برند / استودیوی تدوین:*"))
        self.input_studio = QLineEdit()
        self.input_studio.setFixedHeight(36)
        self.input_studio.setPlaceholderText("مثال: استودیو دیاکو")
        self.input_studio.setStyleSheet(self._input_style())
        form_layout.addWidget(self.input_studio)

        # ۳. شماره تماس
        form_layout.addWidget(QLabel("شماره تماس هماهنگی و پشتیبانی:*"))
        self.input_phone = QLineEdit()
        self.input_phone.setFixedHeight(36)
        self.input_phone.setPlaceholderText("مثال: 09120000000")
        self.input_phone.setStyleSheet(self._input_style())
        form_layout.addWidget(self.input_phone)

        # ۴. شماره کارت بانکی
        form_layout.addWidget(QLabel("شماره کارت بانکی (جهت درج در فاکتور و پیام تسویه):"))
        self.input_card = QLineEdit()
        self.input_card.setFixedHeight(36)
        self.input_card.setPlaceholderText("مثال: 6037-9918-0000-0000")
        self.input_card.setStyleSheet(self._input_style())
        form_layout.addWidget(self.input_card)

        # ۵. پوشه پیش‌فرض هارد راش‌ها
        form_layout.addWidget(QLabel("مسیر پیش‌فرض ذخیره‌سازی راش‌ها و پروژه‌ها:"))
        path_box = QHBoxLayout()
        self.input_drive = QLineEdit()
        self.input_drive.setFixedHeight(36)
        self.input_drive.setReadOnly(True)
        self.input_drive.setPlaceholderText("مسیری انتخاب نشده است...")
        self.input_drive.setStyleSheet(self._input_style())
        path_box.addWidget(self.input_drive)

        btn_browse = QPushButton("انتخاب پوشه...")
        btn_browse.setFixedHeight(36)
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #1E283D;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11.5px;
            }
            QPushButton:hover { background-color: #242E42; border-color: #6366F1; }
        """)
        btn_browse.clicked.connect(self._browse_drive)
        path_box.addWidget(btn_browse)
        form_layout.addLayout(path_box)

        scroll.setWidget(container)
        self.container_layout.addWidget(scroll, stretch=1)

        # دکمه ورود و شروع
        btn_submit = QPushButton("ورود به محیط برنامه و شروع کار")
        btn_submit.setFixedHeight(40)
        btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_submit.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        btn_submit.clicked.connect(self._save_and_start)
        self.container_layout.addWidget(btn_submit)

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-family: 'Vazirmatn';
                font-size: 12px;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """

    def _browse_drive(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه پیش‌فرض راش‌ها")
        if folder:
            self.input_drive.setText(folder)

    def _save_and_start(self):
        editor = self.input_editor.text().strip()
        studio = self.input_studio.text().strip()

        if not editor or not studio:
            StudioConfirmDialog.ask(self, "اطلاعات ناقص", "لطفاً نام تدوین‌گر و نام استودیو را وارد کنید.", icon_name="alert")
            return

        self.settings["editor_name"] = editor
        self.settings["studio_name"] = studio
        self.settings["phone"] = self.input_phone.text().strip()
        self.settings["card_number"] = self.input_card.text().strip()
        self.settings["default_drive_path"] = self.input_drive.text().strip()
        self.settings["is_first_run"] = False

        SettingsManager.save_settings(self.settings)
        global_signals.settings_updated.emit()
        self.accept()