# ==================================================
# FILE: widgets/new_project_dialog.py
# ==================================================
from datetime import datetime
from typing import Optional
import jdatetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, QFileDialog, 
    QMessageBox, QCheckBox, QGridLayout, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QSize
from sqlalchemy import select

from database.db_manager import db
from database.models import Client, Project, ProjectClipItem, DriveLocation, StageEnum, WorkflowStatusEnum
from core.settings_manager import SettingsManager
from core.icon_provider import IconProvider
from core.signals import global_signals
from core.persian_utils import (
    format_toman, number_to_persian_words,
    parse_jalali_text, get_persian_date_readable, get_deadline_relative_text,
    to_persian_numbers
)
from widgets.studio_dialog_base import StudioBaseDialog
from widgets.custom_inputs import CurrencyLineEdit


class NewProjectDialog(StudioBaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("ثبت پروژه جدید تدوین مراسم")
        self.setMinimumWidth(500)
        self.resize(580, 680)
        self.clip_checkboxes = []
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "ثبت پروژه جدید تدوین مراسم",
            "مشخصات قرارداد، تاریخ‌ها و کلیپ‌های مراسم را وارد کنید",
            icon_name="rings",
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

        # گرید فیلدهای فرم
        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(14)
        form_grid.setVerticalSpacing(8)

        # نام عروس و داماد
        form_grid.addWidget(QLabel("نام عروس و داماد:"), 0, 0)
        self.input_couple = QLineEdit()
        self.input_couple.setFixedHeight(36)
        self.input_couple.setPlaceholderText("مثال: سارا و امیرحسین")
        self.input_couple.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0 12px; font-size: 12.5px; color: #F8FAFC;")
        form_grid.addWidget(self.input_couple, 0, 1)

        # استودیو / کارفرما
        form_grid.addWidget(QLabel("استودیو / آتلیه:"), 1, 0)
        self.combo_client = QComboBox()
        self.combo_client.setFixedHeight(36)
        self.combo_client.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0 12px; font-size: 12.5px; color: #F8FAFC;")
        self._load_clients()
        form_grid.addWidget(self.combo_client, 1, 1)

        # مبلغ قرارداد
        form_grid.addWidget(QLabel("مبلغ کل توافق‌شده:"), 2, 0)
        fee_col = QVBoxLayout()
        fee_col.setSpacing(3)

        settings = SettingsManager.load_settings()
        quick_amounts = settings.get("quick_amounts", {})

        if quick_amounts:
            amounts_box = QHBoxLayout()
            amounts_box.setSpacing(6)
            for name, val in quick_amounts.items():
                btn_amt = QPushButton(f"💰 {name}")
                btn_amt.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_amt.setStyleSheet("""
                    QPushButton {
                        font-family: 'Vazirmatn';
                        background-color: rgba(16, 185, 129, 0.12);
                        color: #10B981;
                        border: 1px solid rgba(16, 185, 129, 0.25);
                        border-radius: 10px;
                        padding: 2px 8px;
                        font-size: 10.5px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #10B981;
                        color: #FFFFFF;
                    }
                """)
                btn_amt.clicked.connect(lambda _, v=val: self.input_fee.set_amount(v))
                amounts_box.addWidget(btn_amt)
            amounts_box.addStretch()
            fee_col.addLayout(amounts_box)

        self.input_fee = CurrencyLineEdit()
        self.input_fee.setFixedHeight(36)
        self.input_fee.setPlaceholderText("مبلغ را به تومان وارد کنید (مثال: ۱۵,۰۰۰,۰۰۰)...")
        self.input_fee.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0 12px; font-size: 12.5px; color: #F8FAFC;")
        self.input_fee.amountChanged.connect(self._on_amount_changed)
        fee_col.addWidget(self.input_fee)

        self.lbl_fee_words = QLabel("")
        self.lbl_fee_words.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #10B981; font-weight: 600; padding: 1px 4px; border: none;")
        fee_col.addWidget(self.lbl_fee_words)
        form_grid.addLayout(fee_col, 2, 1)

        # تاریخ مراسم
        form_grid.addWidget(QLabel("تاریخ روز مراسم:"), 3, 0)
        event_col = QVBoxLayout()
        event_col.setSpacing(3)

        self.input_event_date = QLineEdit()
        self.input_event_date.setFixedHeight(36)
        self.input_event_date.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0 12px; font-size: 12.5px; color: #F8FAFC;")
        today_j = jdatetime.date.today().strftime("%Y/%m/%d")
        self.input_event_date.setText(today_j)
        self.input_event_date.textChanged.connect(self._on_event_date_changed)
        event_col.addWidget(self.input_event_date)

        self.lbl_event_date_readable = QLabel("")
        self.lbl_event_date_readable.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #818CF8; font-weight: 600; padding: 1px 4px; border: none;")
        event_col.addWidget(self.lbl_event_date_readable)
        form_grid.addLayout(event_col, 3, 1)

        # مهلت تحویل (ددلاین)
        form_grid.addWidget(QLabel("مهلت تحویل (ددلاین):"), 4, 0)
        deadline_col = QVBoxLayout()
        deadline_col.setSpacing(3)

        self.input_deadline = QLineEdit()
        self.input_deadline.setFixedHeight(36)
        self.input_deadline.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0 12px; font-size: 12.5px; color: #F8FAFC;")
        self.input_deadline.setPlaceholderText("مثال: 1405/06/15")
        self.input_deadline.textChanged.connect(self._on_deadline_changed)
        deadline_col.addWidget(self.input_deadline)

        self.lbl_deadline_relative = QLabel("")
        self.lbl_deadline_relative.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #F59E0B; font-weight: 600; padding: 1px 4px; border: none;")
        deadline_col.addWidget(self.lbl_deadline_relative)
        form_grid.addLayout(deadline_col, 4, 1)

        # مسیر پوشه هارد راش‌ها
        form_grid.addWidget(QLabel("پوشه راش‌ها روی هارد:"), 5, 0)
        path_box = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setFixedHeight(36)
        self.input_path.setPlaceholderText("مسیر پوشه انتخاب نشده است...")
        self.input_path.setReadOnly(True)
        self.input_path.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0 12px; font-size: 11.5px; color: #94A3B8;")
        path_box.addWidget(self.input_path)

        btn_browse = QPushButton("انتخاب پوشه...")
        btn_browse.setFixedHeight(36)
        btn_browse.setIcon(IconProvider.get_icon("folder", "#94A3B8", size=13))
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #1E283D;
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 0 12px;
                font-size: 11.5px;
                font-weight: 500;
            }
            QPushButton:hover {
                border-color: #6366F1;
                background-color: #242E42;
            }
        """)
        btn_browse.clicked.connect(self._browse_folder)
        path_box.addWidget(btn_browse)
        form_grid.addLayout(path_box, 5, 1)

        # فایل پروژه تدوین (NLE)
        form_grid.addWidget(QLabel("فایل پروژه تدوین (NLE):"), 6, 0)
        nle_box = QHBoxLayout()
        self.input_nle_path = QLineEdit()
        self.input_nle_path.setFixedHeight(36)
        self.input_nle_path.setPlaceholderText("فایل پروژه .prproj یا .drp (اختیاری)...")
        self.input_nle_path.setReadOnly(True)
        self.input_nle_path.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 0 12px; font-size: 11.5px; color: #94A3B8;")
        nle_box.addWidget(self.input_nle_path)

        btn_browse_nle = QPushButton("انتخاب فایل NLE...")
        btn_browse_nle.setFixedHeight(36)
        btn_browse_nle.setIcon(IconProvider.get_icon("nle_launch", "#818CF8", size=13))
        btn_browse_nle.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_nle.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #1E283D;
                color: #F8FAFC;
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 8px;
                padding: 0 12px;
                font-size: 11.5px;
                font-weight: 500;
            }
            QPushButton:hover {
                border-color: #6366F1;
                background-color: #242E42;
            }
        """)
        btn_browse_nle.clicked.connect(self._browse_nle_file)
        nle_box.addWidget(btn_browse_nle)
        form_grid.addLayout(nle_box, 6, 1)

        form_layout.addLayout(form_grid)

        # چک‌لیست کلیپ‌ها
        clips_section_header = QVBoxLayout()
        clips_section_header.setSpacing(4)

        lbl_clips_title = QLabel("کلیپ‌های سفارش داده شده این پروژه:")
        lbl_clips_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 700; color: #F8FAFC; border: none;")
        clips_section_header.addWidget(lbl_clips_title)

        packages = settings.get("packages", {})
        if packages:
            capsule_row = QHBoxLayout()
            capsule_row.setSpacing(6)
            capsule_row.addWidget(QLabel("<span style='font-size:11px; color:#818CF8; font-weight:600;'>پکیج‌های سریع:</span>"))

            for pkg_name, pkg_clips in packages.items():
                btn_pkg = QPushButton(f"⚡ {pkg_name}")
                btn_pkg.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_pkg.setStyleSheet("""
                    QPushButton {
                        font-family: 'Vazirmatn';
                        background-color: rgba(99, 102, 241, 0.12);
                        color: #818CF8;
                        border: 1px solid rgba(99, 102, 241, 0.25);
                        border-radius: 10px;
                        padding: 2px 8px;
                        font-size: 10.5px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background-color: #6366F1;
                        color: #FFFFFF;
                    }
                """)
                btn_pkg.clicked.connect(lambda _, c_list=pkg_clips: self._apply_package(c_list))
                capsule_row.addWidget(btn_pkg)

            capsule_row.addStretch()
            clips_section_header.addLayout(capsule_row)

        form_layout.addLayout(clips_section_header)

        clips_frame = QWidget()
        clips_frame.setStyleSheet("""
            QWidget {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QCheckBox {
                font-family: 'Vazirmatn';
                color: #F8FAFC;
                font-size: 11.5px;
                spacing: 8px;
                background: transparent;
                border: none;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #242E42;
                border: 1.5px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
            }
            QCheckBox::indicator:hover {
                border-color: #6366F1;
                background-color: #2D3952;
            }
            QCheckBox::indicator:checked {
                background-color: #6366F1;
                border-color: #6366F1;
                image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'%3E%3C/polyline%3E%3C/svg%3E");
            }
        """)
        clips_layout = QGridLayout(clips_frame)
        clips_layout.setContentsMargins(10, 8, 10, 8)
        clips_layout.setHorizontalSpacing(14)
        clips_layout.setVerticalSpacing(6)

        available_clips = settings.get("custom_clips", [])
        for i, clip_name in enumerate(available_clips):
            cb = QCheckBox(clip_name)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            row = i // 2
            col = i % 2
            clips_layout.addWidget(cb, row, col)
            self.clip_checkboxes.append((cb, clip_name))

        form_layout.addWidget(clips_frame)

        scroll.setWidget(container)
        self.container_layout.addWidget(scroll, stretch=1)

        # دکمه‌های اقدام
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_submit = QPushButton("ثبت و شروع پایپ‌لاین تدوین")
        self.btn_submit.setFixedHeight(38)
        self.btn_submit.setIcon(IconProvider.get_icon("save", "#FFFFFF", size=14))
        self.btn_submit.setProperty("class", "PrimaryButton")
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 12.5px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        self.btn_submit.clicked.connect(self._submit)
        btn_layout.addWidget(self.btn_submit, stretch=2)
        
        self.btn_cancel = QPushButton("انصراف")
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #1A2234;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #242E42; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_layout)
        self._on_event_date_changed(self.input_event_date.text())

    def _on_amount_changed(self, amount: int):
        if amount > 0:
            self.lbl_fee_words.setText(number_to_persian_words(amount))
        else:
            self.lbl_fee_words.setText("")

    def _on_event_date_changed(self, text_val: str):
        j_date = parse_jalali_text(text_val)
        if j_date:
            self.lbl_event_date_readable.setText(get_persian_date_readable(j_date))
        else:
            self.lbl_event_date_readable.setText("")

    def _on_deadline_changed(self, text_val: str):
        j_date = parse_jalali_text(text_val)
        if j_date:
            self.lbl_deadline_relative.setText(get_deadline_relative_text(j_date))
        else:
            self.lbl_deadline_relative.setText("")

    def _apply_package(self, package_clips: list):
        for cb, name in self.clip_checkboxes:
            cb.setChecked(name in package_clips)

    def _load_clients(self):
        self.combo_client.clear()
        with db.get_session() as session:
            clients = session.scalars(select(Client).order_by(Client.created_at.desc())).all()
            for c in clients:
                display_name = c.company if c.company else c.full_name
                if c.company and c.full_name and c.company != c.full_name:
                    display_name += f" (مدیریت: {c.full_name})"
                self.combo_client.addItem(display_name, c.id)

    def _browse_folder(self):
        settings = SettingsManager.load_settings()
        default_dir = settings.get("default_drive_path", "")
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه راش‌ها", default_dir)
        if folder:
            self.input_path.setText(folder)

    def _browse_nle_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل پروژه Premiere یا DaVinci", "",
            "NLE Projects (*.prproj *.drp);;Premiere Pro (*.prproj);;DaVinci Resolve (*.drp);;All Files (*.*)"
        )
        if file_path:
            self.input_nle_path.setText(file_path)

    def _submit(self):
        couple = self.input_couple.text().strip()
        if not couple:
            QMessageBox.warning(self, "خطا", "نام عروس و داماد نمی‌تواند خالی باشد.")
            return

        client_id = self.combo_client.currentData()
        if not client_id:
            QMessageBox.warning(self, "خطا", "لطفاً یک استودیو انتخاب کنید.")
            return

        fee = self.input_fee.get_amount()

        event_j = parse_jalali_text(self.input_event_date.text())
        event_dt = datetime.combine(event_j.togregorian(), datetime.min.time()) if event_j else None

        deadline_j = parse_jalali_text(self.input_deadline.text())
        deadline_dt = datetime.combine(deadline_j.togregorian(), datetime.min.time()) if deadline_j else None

        path = self.input_path.text().strip()
        nle_path = self.input_nle_path.text().strip() or None

        selected_clips = [name for cb, name in self.clip_checkboxes if cb.isChecked()]
        if not selected_clips:
            selected_clips = ["فیلم کامل مراسم (Long Cut)"]

        with db.get_session() as session:
            next_pnum = db.get_next_project_number(session)

            proj = Project(
                project_number=next_pnum,
                title=f"پروژه {couple}",
                couple_names=couple,
                client_id=client_id,
                base_fee=fee,
                total_fee=fee,
                event_date=event_dt,
                deadline=deadline_dt,
                current_stage=StageEnum.ROUGH_CUT,
                workflow_status=WorkflowStatusEnum.EDITING,
                is_archived=False,
                nle_project_path=nle_path
            )
            session.add(proj)
            session.flush()

            for c_name in selected_clips:
                session.add(ProjectClipItem(project_id=proj.id, clip_name=c_name))

            if path:
                session.add(DriveLocation(
                    project_id=proj.id,
                    drive_label="هارد اصلی پروژه",
                    absolute_path=path,
                    is_primary=True
                ))

            session.commit()
            proj_id = proj.id
            proj_num = proj.project_number

        global_signals.project_created.emit({
            "id": proj_id,
            "project_number": proj_num,
            "title": f"پروژه {couple}"
        })
        self.accept()