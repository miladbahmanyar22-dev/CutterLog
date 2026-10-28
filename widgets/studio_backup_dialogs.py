# ==================================================
# FILE: widgets/studio_backup_dialogs.py
# ==================================================
from typing import Dict, Any, List
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QCheckBox, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog
from core.backup_manager import StudioBackupManager
from core.icon_provider import IconProvider
from core.persian_utils import to_persian_numbers


class StudioExportBackupDialog(StudioBaseDialog):
    """
    دیالوگ انتخاب گزینشی اجزای بسته پشتیبان پیش از ذخیره‌سازی
    """
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setFixedWidth(520)
        self.checkboxes: Dict[str, QCheckBox] = {}
        self.selected_sections: List[str] = []
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "تهیه بسته پشتیبان جامع استودیو",
            "بخش‌های مورد نظر را برای بسته‌بندی در فایل پشتیبان انتخاب کنید",
            icon_name="save",
            icon_color="#10B981"
        )

        sel_row = QHBoxLayout()
        sel_row.setSpacing(8)
        lbl_hint = QLabel("انتخاب بخش‌ها:")
        lbl_hint.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: #8F909D;")
        sel_row.addWidget(lbl_hint)
        sel_row.addStretch()

        btn_all = QPushButton("انتخاب همه")
        btn_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_all.setStyleSheet("background: transparent; color: #818CF8; border: none; font-size: 11px; font-weight: 700;")
        btn_all.clicked.connect(self._select_all)
        sel_row.addWidget(btn_all)

        btn_none = QPushButton("عدم انتخاب")
        btn_none.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_none.setStyleSheet("background: transparent; color: #94A3B8; border: none; font-size: 11px;")
        btn_none.clicked.connect(self._deselect_all)
        sel_row.addWidget(btn_none)
        self.container_layout.addLayout(sel_row)

        chk_path = IconProvider.get_checkbox_checked_icon_path()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background-color: #121826; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(14, 12, 14, 12)
        c_lay.setSpacing(10)

        for sec_key, sec_title, sec_desc in StudioBackupManager.BACKUP_SECTIONS:
            item_frame = QFrame()
            item_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: #161F30;
                    border: 1px solid rgba(255, 255, 255, 0.04);
                    border-radius: 6px;
                }}
                QFrame:hover {{ border-color: rgba(99, 102, 241, 0.4); }}
                QCheckBox {{
                    font-family: 'Vazirmatn';
                    font-size: 12px;
                    font-weight: 700;
                    color: #F8FAFC;
                    spacing: 8px;
                    background: transparent;
                    border: none;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    background-color: #242E42;
                    border: 1.5px solid rgba(255, 255, 255, 0.22);
                    border-radius: 4px;
                }}
                QCheckBox::indicator:hover {{
                    border-color: #818CF8;
                    background-color: #2D3952;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #6366F1;
                    border: 1.5px solid #818CF8;
                    image: url("{chk_path}");
                }}
            """)
            i_lay = QVBoxLayout(item_frame)
            i_lay.setContentsMargins(10, 8, 10, 8)
            i_lay.setSpacing(2)

            cb = QCheckBox(sec_title)
            cb.setChecked(True)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            i_lay.addWidget(cb)

            lbl_d = QLabel(sec_desc)
            lbl_d.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #94A3B8; border: none; background: transparent; padding-right: 26px;")
            i_lay.addWidget(lbl_d)

            c_lay.addWidget(item_frame)
            self.checkboxes[sec_key] = cb

        scroll.setWidget(container)
        self.container_layout.addWidget(scroll, stretch=1)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_confirm = QPushButton("تأیید و ذخیره بسته (.clpbackup)")
        btn_confirm.setFixedHeight(38)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 700;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_confirm.clicked.connect(self._confirm)
        btn_box.addWidget(btn_confirm, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #1E283D; color: #F8FAFC; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)

    def _confirm(self):
        self.selected_sections = [k for k, cb in self.checkboxes.items() if cb.isChecked()]
        if not self.selected_sections:
            StudioConfirmDialog.ask(self, "خطا", "لطفاً حداقل یک بخش را برای پشتیبان‌گیری انتخاب کنید.", icon_name="alert")
            return
        self.accept()


class StudioImportBackupDialog(StudioBaseDialog):
    """
    دیالوگ بررسی، آنالیز متادیتا و بازیابی گزینشی از فایل پشتیبان
    """
    def __init__(self, manifest_info: Dict[str, Any], parent=None):
        super().__init__(parent=parent)
        self.manifest_info = manifest_info
        self.setFixedWidth(540)
        self.checkboxes: Dict[str, QCheckBox] = {}
        self.selected_sections: List[str] = []
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "آنالیز و بازیابی فایل پشتیبان",
            "محتوای موجود در بسته پشتیبان بررسی شد؛ بخش‌های مدنظر را اعمال کنید",
            icon_name="revision",
            icon_color="#F59E0B"
        )

        meta_card = QFrame()
        meta_card.setStyleSheet("background-color: #141B2B; border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 8px;")
        m_lay = QVBoxLayout(meta_card)
        m_lay.setContentsMargins(14, 10, 14, 10)
        m_lay.setSpacing(4)

        date_val = self.manifest_info.get("created_at_jalali", "نامشخص")
        ver_val = self.manifest_info.get("app_version", "۱.۶.۵")
        studio_val = self.manifest_info.get("studio_name") or self.manifest_info.get("editor_name") or "استودیو"

        lbl_top = QLabel(f"📦 مبدأ پشتیبان: <b style='color:#F8FAFC;'>{studio_val}</b> | نسخه نرم‌افزار: <b style='color:#818CF8;'>{ver_val}</b>")
        lbl_top.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8; border: none; background: transparent;")
        m_lay.addWidget(lbl_top)

        lbl_date = QLabel(f"📅 تاریخ ایجاد بسته: <b style='color:#10B981;'>{date_val}</b>")
        lbl_date.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8; border: none; background: transparent;")
        m_lay.addWidget(lbl_date)

        self.container_layout.addWidget(meta_card)

        chk_path = IconProvider.get_checkbox_checked_icon_path()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background-color: #121826; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(14, 12, 14, 12)
        c_lay.setSpacing(10)

        available_keys = set(self.manifest_info.get("available_sections", []))

        for sec_key, sec_title, sec_desc in StudioBackupManager.BACKUP_SECTIONS:
            is_avail = (sec_key in available_keys)

            item_frame = QFrame()
            border_c = "rgba(255, 255, 255, 0.04)" if is_avail else "rgba(255, 255, 255, 0.02)"
            bg_c = "#161F30" if is_avail else "#0E131F"
            item_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_c};
                    border: 1px solid {border_c};
                    border-radius: 6px;
                }}
                QCheckBox {{
                    font-family: 'Vazirmatn';
                    font-size: 12px;
                    font-weight: 700;
                    spacing: 8px;
                    background: transparent;
                    border: none;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    background-color: #242E42;
                    border: 1.5px solid rgba(255, 255, 255, 0.22);
                    border-radius: 4px;
                }}
                QCheckBox::indicator:hover {{
                    border-color: #818CF8;
                    background-color: #2D3952;
                }}
                QCheckBox::indicator:checked {{
                    background-color: #6366F1;
                    border: 1.5px solid #818CF8;
                    image: url("{chk_path}");
                }}
                QCheckBox::indicator:disabled {{
                    background-color: #0E131F;
                    border-color: rgba(255, 255, 255, 0.08);
                }}
            """)
            
            i_lay = QVBoxLayout(item_frame)
            i_lay.setContentsMargins(10, 8, 10, 8)
            i_lay.setSpacing(2)

            cb = QCheckBox(sec_title)
            cb.setChecked(is_avail)
            cb.setEnabled(is_avail)
            cb.setCursor(Qt.CursorShape.PointingHandCursor if is_avail else Qt.CursorShape.ForbiddenCursor)
            
            text_col = "#F8FAFC" if is_avail else "#475569"
            avail_tag = "" if is_avail else " (در این فایل موجود نیست)"
            cb.setText(f"{sec_title}{avail_tag}")
            cb.setStyleSheet(f"color: {text_col};")
            i_lay.addWidget(cb)

            lbl_d = QLabel(sec_desc)
            desc_col = "#94A3B8" if is_avail else "#334155"
            lbl_d.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 10.5px; color: {desc_col}; border: none; background: transparent; padding-right: 26px;")
            i_lay.addWidget(lbl_d)

            c_lay.addWidget(item_frame)
            if is_avail:
                self.checkboxes[sec_key] = cb

        scroll.setWidget(container)
        self.container_layout.addWidget(scroll, stretch=1)

        lbl_warn = QLabel("⚠️ توجه: پیش از جایگزینی داده‌ها، نقطه بازگشت اضطراری خودکار از اطلاعات جاری ذخیره خواهد شد.")
        lbl_warn.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #F59E0B; padding: 0 4px;")
        self.container_layout.addWidget(lbl_warn)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_confirm = QPushButton("تأیید و اجرای بازیابی")
        btn_confirm.setFixedHeight(38)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #F59E0B;
                color: #000000;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 800;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #FBBF24; }
        """)
        btn_confirm.clicked.connect(self._confirm)
        btn_box.addWidget(btn_confirm, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #1E283D; color: #F8FAFC; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _confirm(self):
        self.selected_sections = [k for k, cb in self.checkboxes.items() if cb.isChecked()]
        if not self.selected_sections:
            StudioConfirmDialog.ask(self, "خطا", "لطفاً حداقل یک بخش معتبر را برای بازیابی انتخاب کنید.", icon_name="alert")
            return
        self.accept()