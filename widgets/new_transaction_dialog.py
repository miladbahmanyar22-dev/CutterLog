# ==================================================
# FILE: widgets/new_transaction_dialog.py
# ==================================================
from datetime import datetime
from typing import Optional
import jdatetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QComboBox, 
    QFrame, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QSize
from sqlalchemy import select

from database.db_manager import db
from database.models import Project, Transaction, Client, PaymentTypeEnum
from core.project_controller import ProjectController
from core.finance_controller import FinanceController
from core.persian_utils import normalize_to_english_digits, format_toman, to_persian_numbers
from core.icon_provider import IconProvider
from core.signals import global_signals
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog


class NewTransactionDialog(StudioBaseDialog):
    """دیالوگ مدرن استودیو برای ثبت واریزی و تسویه مالی همراه با کد رهگیری"""
    def __init__(self, target_project_id: Optional[int] = None, target_client_id: Optional[int] = None, parent=None):
        super().__init__(parent=parent)
        self.target_project_id = target_project_id
        self.target_client_id = target_client_id
        self.suggested_amount = 0

        self.setFixedWidth(560)
        self.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                color: #94A3B8;
                font-size: 12px;
                font-weight: 500;
            }
            QLineEdit, QComboBox {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 8px 12px;
                color: #F8FAFC;
                font-size: 12.5px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #6366F1;
                background-color: #1A2438;
            }
            QRadioButton {
                font-family: 'Vazirmatn';
                color: #F8FAFC;
                font-size: 12px;
                font-weight: 600;
            }
        """)
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "ثبت واریزی و تسویه مالی", 
            "تسویه هوشمند کل بدهی استودیو (FIFO) یا پروژه مشخص", 
            icon_name="dollar", 
            icon_color="#10B981"
        )

        # ۱. نحوه تسویه
        mode_box = QHBoxLayout()
        self.rb_studio = QRadioButton("تسویه خودکار کل بدهی استودیو (پیشنهادی)")
        self.rb_project = QRadioButton("تسویه یک پروژه مشخص")
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.rb_studio, 1)
        self.btn_group.addButton(self.rb_project, 2)
        
        if self.target_project_id:
            self.rb_project.setChecked(True)
        else:
            self.rb_studio.setChecked(True)

        self.rb_studio.toggled.connect(self._on_mode_changed)
        mode_box.addWidget(self.rb_studio)
        mode_box.addWidget(self.rb_project)
        self.container_layout.addLayout(mode_box)

        # فیلد انتخاب استودیو
        self.lbl_select_client = QLabel("انتخاب استودیو / کارفرما:")
        self.combo_client = QComboBox()
        self.combo_client.setFixedHeight(36)
        self.combo_client.currentIndexChanged.connect(self._update_balance_info)
        self.container_layout.addWidget(self.lbl_select_client)
        self.container_layout.addWidget(self.combo_client)

        # فیلد انتخاب پروژه
        self.lbl_select_project = QLabel("انتخاب پروژه (صرفاً پروژه‌های تحویل‌شده بدهکار):")
        self.combo_project = QComboBox()
        self.combo_project.setFixedHeight(36)
        self.combo_project.currentIndexChanged.connect(self._update_balance_info)
        self.container_layout.addWidget(self.lbl_select_project)
        self.container_layout.addWidget(self.combo_project)

        # ۲. کادر وضعیت حساب
        self.balance_frame = QFrame()
        self.balance_frame.setStyleSheet("""
            QFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)
        b_lay = QHBoxLayout(self.balance_frame)
        b_lay.setContentsMargins(12, 8, 12, 8)
        b_lay.setSpacing(10)

        self.lbl_balance_info = QLabel("در حال بارگذاری...")
        self.lbl_balance_info.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #F8FAFC;")
        b_lay.addWidget(self.lbl_balance_info, stretch=1)

        self.btn_use_suggested = QPushButton("جایگذاری کل مبلغ ⚡")
        self.btn_use_suggested.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_use_suggested.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(99, 102, 241, 0.15);
                color: #818CF8;
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #6366F1;
                color: #FFFFFF;
            }
        """)
        self.btn_use_suggested.clicked.connect(self._fill_suggested_amount)
        b_lay.addWidget(self.btn_use_suggested)

        self.container_layout.addWidget(self.balance_frame)

        # ۳. فیلد مبلغ
        self.container_layout.addWidget(QLabel("مبلغ واریزی این تراکنش (تومان):"))
        self.input_amount = QLineEdit()
        self.input_amount.setFixedHeight(36)
        self.input_amount.setPlaceholderText("مبلغ را به تومان وارد کنید...")
        self.input_amount.textChanged.connect(self._on_amount_changed)
        self.container_layout.addWidget(self.input_amount)

        self.lbl_amount_preview = QLabel("")
        self.lbl_amount_preview.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 600; padding-right: 2px;")
        self.container_layout.addWidget(self.lbl_amount_preview)

        # ۴. نوع پرداخت و کد پیگیری
        row_type_code = QHBoxLayout()
        row_type_code.setSpacing(10)

        col_type = QVBoxLayout()
        col_type.setSpacing(4)
        col_type.addWidget(QLabel("نوع پرداخت:"))
        self.combo_type = QComboBox()
        self.combo_type.setFixedHeight(36)
        self.combo_type.addItem("واریزی مرحله‌ای", PaymentTypeEnum.STAGE_PAYMENT)
        self.combo_type.addItem("پیش‌پرداخت اولیه", PaymentTypeEnum.PREPAYMENT)
        self.combo_type.addItem("تسویه نهایی حساب", PaymentTypeEnum.FINAL_SETTLEMENT)
        col_type.addWidget(self.combo_type)
        row_type_code.addLayout(col_type, stretch=1)

        col_code = QVBoxLayout()
        col_code.setSpacing(4)
        col_code.addWidget(QLabel("شماره پیگیری / ارجاع بانکی (اختیاری):"))
        self.input_tracking = QLineEdit()
        self.input_tracking.setFixedHeight(36)
        self.input_tracking.setPlaceholderText("مثال: 984521 / ۴ رقم آخر کارت")
        col_code.addWidget(self.input_tracking)
        row_type_code.addLayout(col_code, stretch=1)

        self.container_layout.addLayout(row_type_code)

        # ۵. تاریخ و توضیحات
        row_date_note = QHBoxLayout()
        row_date_note.setSpacing(10)

        col_date = QVBoxLayout()
        col_date.setSpacing(4)
        col_date.addWidget(QLabel("تاریخ ثبت واریز:"))
        self.input_date = QLineEdit()
        self.input_date.setFixedHeight(36)
        today_j = jdatetime.date.today().strftime("%Y/%m/%d")
        self.input_date.setText(to_persian_numbers(today_j))
        col_date.addWidget(self.input_date)
        row_date_note.addLayout(col_date, stretch=1)

        col_note = QVBoxLayout()
        col_note.setSpacing(4)
        col_note.addWidget(QLabel("توضیحات واریز (اختیاری):"))
        self.input_note = QLineEdit()
        self.input_note.setFixedHeight(36)
        self.input_note.setPlaceholderText("مثال: واریز کارت به کارت / تسویه حساب")
        col_note.addWidget(self.input_note)
        row_date_note.addLayout(col_note, stretch=2)

        self.container_layout.addLayout(row_date_note)

        # ۶. دکمه‌های اقدام
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_submit = QPushButton("ثبت و اعمال دریافت وجه")
        self.btn_submit.setFixedHeight(38)
        self.btn_submit.setIcon(IconProvider.get_icon("save", "#FFFFFF", size=14))
        self.btn_submit.setIconSize(QSize(14, 14))
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 12.5px;
                font-weight: 700;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        self.btn_submit.clicked.connect(self._submit)
        btn_layout.addWidget(self.btn_submit, stretch=2)

        self.btn_cancel = QPushButton("انصراف")
        self.btn_cancel.setFixedHeight(38)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
                padding: 0 14px;
            }
            QPushButton:hover { background-color: #1E283D; color: #F8FAFC; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_layout)

        self._load_clients()
        self._load_projects()
        self._on_mode_changed()

    def _on_mode_changed(self):
        is_studio_mode = self.rb_studio.isChecked()
        self.lbl_select_client.setVisible(is_studio_mode)
        self.combo_client.setVisible(is_studio_mode)
        
        self.lbl_select_project.setVisible(not is_studio_mode)
        self.combo_project.setVisible(not is_studio_mode)
        
        self._update_balance_info()

    def _load_clients(self):
        self.combo_client.clear()
        with db.get_session() as session:
            clients = session.scalars(select(Client).order_by(Client.company, Client.full_name)).all()
            for idx, c in enumerate(clients):
                display = c.company or c.full_name
                self.combo_client.addItem(display, c.id)
                if self.target_client_id and c.id == self.target_client_id:
                    self.combo_client.setCurrentIndex(idx)

    def _load_projects(self):
        self.combo_project.clear()
        all_projects = ProjectController.get_all_projects() + ProjectController.get_archived_projects()
        seen = set()
        
        for p in all_projects:
            if p.id in seen:
                continue
            
            if FinanceController.is_project_eligible_for_finance(p):
                fin = ProjectController.get_project_financial_summary(p)
                if fin["remaining"] > 0 or (self.target_project_id and p.id == self.target_project_id):
                    seen.add(p.id)
                    client_name = p.client.company if (p.client and p.client.company) else (p.client.full_name if p.client else "بدون استودیو")
                    p_num = f"{p.project_number:03d}" if p.project_number else f"{p.id:03d}"
                    rem_str = f" [مانده: {format_toman(fin['remaining'])}]" if fin['remaining'] > 0 else " [تسویه کامل]"
                    
                    self.combo_project.addItem(f"{to_persian_numbers(p_num)} — {p.couple_names} ({client_name}){rem_str}", (p.id, p.client_id))
                    
                    if self.target_project_id and p.id == self.target_project_id:
                        self.combo_project.setCurrentIndex(self.combo_project.count() - 1)

    def _update_balance_info(self):
        if self.rb_studio.isChecked():
            client_id = self.combo_client.currentData()
            if not client_id:
                return
            summary = FinanceController.get_studio_debt_summary(client_id)
            self.suggested_amount = summary["total_remaining"]

            if self.suggested_amount == 0:
                self.lbl_balance_info.setText("وضعیت حساب استودیو: <b style='color:#10B981;'>تسویه کامل (مانده کل: ۰ تومان) ✓</b>")
                self.btn_use_suggested.setEnabled(False)
            else:
                unsettled_cnt = len(summary["unsettled_projects"])
                self.lbl_balance_info.setText(
                    f"کل طلب استودیو: <b style='color:#F59E0B;'>{format_toman(self.suggested_amount)}</b> "
                    f"({to_persian_numbers(unsettled_cnt)} پروژه بدهکار)"
                )
                self.btn_use_suggested.setEnabled(True)
        else:
            proj_data = self.combo_project.currentData()
            if not proj_data:
                self.lbl_balance_info.setText("هیچ پروژه بدهکاری برای تسویه یافت نشد.")
                self.btn_use_suggested.setEnabled(False)
                return
            project_id, _ = proj_data
            project = ProjectController.get_project_by_id(project_id)
            if project:
                fin = ProjectController.get_project_financial_summary(project)
                self.suggested_amount = fin["remaining"]
                if self.suggested_amount == 0:
                    self.lbl_balance_info.setText("وضعیت این پروژه: <b style='color:#10B981;'>تسویه کامل ✓</b>")
                    self.btn_use_suggested.setEnabled(False)
                else:
                    self.lbl_balance_info.setText(
                        f"مانده بدهی این پروژه: <b style='color:#F59E0B;'>{format_toman(self.suggested_amount)}</b>"
                    )
                    self.btn_use_suggested.setEnabled(True)

    def _fill_suggested_amount(self):
        if self.suggested_amount > 0:
            self.input_amount.setText(str(self.suggested_amount))

    def _on_amount_changed(self, text: str):
        clean_digits = normalize_to_english_digits(text)
        if clean_digits.isdigit() and int(clean_digits) > 0:
            val = int(clean_digits)
            self.lbl_amount_preview.setText(f"معادل: {format_toman(val)}")
        else:
            self.lbl_amount_preview.setText("")

    def _submit(self):
        amount_clean = normalize_to_english_digits(self.input_amount.text())
        if not amount_clean.isdigit() or int(amount_clean) <= 0:
            StudioConfirmDialog.ask(self, "خطا در ثبت واریزی", "لطفاً مبلغ واریزی معتبری وارد کنید.", icon_name="alert")
            return

        amount = int(amount_clean)
        pay_type = self.combo_type.currentData()
        tracking = self.input_tracking.text().strip()
        note = self.input_note.text().strip()

        if self.rb_studio.isChecked():
            client_id = self.combo_client.currentData()
            if not client_id:
                StudioConfirmDialog.ask(self, "خطا", "استودیویی انتخاب نشده است.", icon_name="alert")
                return

            FinanceController.allocate_client_payment(
                client_id=client_id,
                total_amount=amount,
                payment_type=pay_type,
                notes=note,
                tracking_code=tracking
            )
            global_signals.transaction_recorded.emit(0)
            global_signals.client_balance_updated.emit(client_id)
            self.accept()
        else:
            proj_data = self.combo_project.currentData()
            if not proj_data:
                StudioConfirmDialog.ask(self, "خطا", "پروژه‌ای انتخاب نشده است.", icon_name="alert")
                return
            project_id, client_id = proj_data

            with db.get_session() as session:
                trx = Transaction(
                    project_id=project_id,
                    client_id=client_id,
                    amount=amount,
                    payment_type=pay_type,
                    notes=note,
                    tracking_code=tracking or None,
                    paid_at=datetime.utcnow()
                )
                session.add(trx)
                ProjectController.log_event(
                    session, project_id, "TRANSACTION_ADDED", 
                    f"دریافت مبلغ {format_toman(amount)}", 
                    f"شماره پیگیری: {tracking or '-'} | {note or 'واریز ثبت شد.'}"
                )
                session.commit()
                trx_id = trx.id

            global_signals.transaction_recorded.emit(trx_id)
            global_signals.project_updated.emit(project_id)
            if client_id:
                global_signals.client_balance_updated.emit(client_id)
            self.accept()