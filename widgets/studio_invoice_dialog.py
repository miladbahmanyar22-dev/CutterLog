# ==================================================
# FILE: widgets/studio_invoice_dialog.py
# ==================================================
import os
import hmac
import hashlib
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
import jdatetime

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QWidget, 
    QGridLayout, QFileDialog, QSizePolicy, QCheckBox, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, QSize, QPoint, QRectF
from PySide6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QRegion
)

from database.models import Client
from database.db_manager import db
from core.settings_manager import SettingsManager
from core.project_controller import ProjectController
from core.finance_controller import FinanceController
from core.persian_utils import (
    format_toman, to_persian_numbers, gregorian_to_jalali, 
    parse_jalali_text, normalize_to_english_digits
)
from core.icon_provider import IconProvider
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog


class StudioInvoiceImageExporter:
    """موتور رندر با رزولوشن بسیار بالا جهت حفظ وضوح کامل متون هنگام زوم"""
    @staticmethod
    def export_widget_to_image(target_widget: QWidget, output_path: str, scale_factor: float = 3.5) -> bool:
        painter = None
        try:
            if not target_widget:
                return False

            target_widget.adjustSize()
            target_width = target_widget.width()
            target_height = target_widget.height()

            img_w = int(target_width * scale_factor)
            img_h = int(target_height * scale_factor)

            image = QImage(img_w, img_h, QImage.Format.Format_ARGB32_Premultiplied)
            image.setDevicePixelRatio(scale_factor)
            image.fill(QColor("#080C14"))

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            target_widget.render(
                painter, 
                QPoint(0, 0), 
                QRegion(), 
                QWidget.RenderFlag.DrawWindowBackground | QWidget.RenderFlag.DrawChildren
            )
            painter.end()
            painter = None

            out_path_obj = Path(output_path)
            out_path_obj.parent.mkdir(parents=True, exist_ok=True)

            final_path_str = str(out_path_obj.resolve())
            if not final_path_str.lower().endswith(".png"):
                final_path_str += ".png"

            return image.save(final_path_str, "PNG")
        except Exception:
            if painter is not None and painter.isActive():
                painter.end()
            traceback.print_exc()
            return False


class StudioInvoiceDialog(StudioBaseDialog):
    def __init__(self, client_id: int, initial_project_id: Optional[int] = None, parent=None):
        super().__init__(parent=parent)
        self.client_id = client_id
        self.initial_project_id = initial_project_id
        self.setMinimumSize(980, 750)
        self.resize(1040, 860)

        self.include_carry_over = True
        self.selected_project_ids: Set[int] = set()

        self._load_client_data()
        self.settings = SettingsManager.load_settings()
        self.init_ui()
        self._populate_initial_scope()
        self._on_scope_changed()

    def _load_client_data(self):
        with db.get_session() as session:
            client = session.get(Client, self.client_id)
            if not client:
                self.client_name = "استودیو"
                self.manager_name = ""
                self.client_phone = "-"
                self.client_notes = ""
                return
            self.client_name = client.company or client.full_name
            self.manager_name = client.full_name if client.company else ""
            self.client_phone = client.phone or "-"
            self.client_notes = client.notes or ""

    def _make_clean_label(self, text: str, style: str = "") -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background: transparent !important; border: none !important; outline: none !important; {style}")
        return lbl

    def _clear_layout_recursive(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            else:
                sub_layout = item.layout()
                if sub_layout is not None:
                    self._clear_layout_recursive(sub_layout)

    def init_ui(self):
        today_str = gregorian_to_jalali(datetime.now())

        self.build_header(
            f"صدور صورت‌حساب رسمی: {self.client_name}", 
            f"تنظیم اقلام فاکتور، تفکیک پروژه‌ها و گزارش مانده بدهی معوق | تاریخ: {today_str}",
            icon_name="dollar", 
            icon_color="#10B981"
        )

        control_bar = QFrame()
        control_bar.setStyleSheet("""
            QFrame {
                background-color: #121826;
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 8px;
            }
            QLabel {
                font-family: 'Vazirmatn';
                color: #94A3B8;
                font-size: 11.5px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
            QComboBox, QLineEdit {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 4px 10px;
                color: #F8FAFC;
                font-size: 11.5px;
            }
            QComboBox:focus, QLineEdit:focus {
                border-color: #6366F1;
            }
            QCheckBox {
                font-family: 'Vazirmatn';
                font-size: 11px;
                color: #F8FAFC;
                background: transparent;
                border: none;
            }
        """)
        c_bar_layout = QHBoxLayout(control_bar)
        c_bar_layout.setContentsMargins(14, 8, 14, 8)
        c_bar_layout.setSpacing(10)

        c_bar_layout.addWidget(QLabel("دامنه صورت‌حساب:"))
        self.combo_scope = QComboBox()
        self.combo_scope.addItem("فقط پروژه‌های تسویه‌نشده و باز (پیشنهادی)", "unsettled_only")
        self.combo_scope.addItem("تک‌پروژه مشخص", "single_project")
        self.combo_scope.addItem("پروژه‌های این ماه (شمسی)", "this_month")
        self.combo_scope.addItem("پروژه‌های سال جاری", "this_year")
        self.combo_scope.addItem("بازه زمانی دلخواه...", "custom_range")
        self.combo_scope.addItem("صورت‌حساب کل حساب (تمام ادوار)", "all_projects")
        self.combo_scope.currentIndexChanged.connect(self._on_scope_changed)
        c_bar_layout.addWidget(self.combo_scope)

        self.combo_single_proj = QComboBox()
        self.combo_single_proj.setVisible(False)
        self.combo_single_proj.currentIndexChanged.connect(self._on_single_proj_selected)
        c_bar_layout.addWidget(self.combo_single_proj)

        self.custom_date_widget = QWidget()
        self.custom_date_widget.setStyleSheet("background: transparent;")
        cd_lay = QHBoxLayout(self.custom_date_widget)
        cd_lay.setContentsMargins(0, 0, 0, 0)
        cd_lay.setSpacing(6)

        cd_lay.addWidget(QLabel("از:"))
        self.inp_start_date = QLineEdit()
        self.inp_start_date.setFixedWidth(82)
        self.inp_start_date.setPlaceholderText("۱۴۰۵/۰۱/۰۱")
        self.inp_start_date.textChanged.connect(self._on_custom_dates_changed)
        cd_lay.addWidget(self.inp_start_date)

        cd_lay.addWidget(QLabel("تا:"))
        self.inp_end_date = QLineEdit()
        self.inp_end_date.setFixedWidth(82)
        self.inp_end_date.setPlaceholderText("۱۴۰۵/۱۲/۲۹")
        self.inp_end_date.textChanged.connect(self._on_custom_dates_changed)
        cd_lay.addWidget(self.inp_end_date)

        self.custom_date_widget.setVisible(False)
        c_bar_layout.addWidget(self.custom_date_widget)

        self.chk_carry_over = QCheckBox("نمایش مانده معوق از پروژه‌های قبلی")
        self.chk_carry_over.setChecked(True)
        self.chk_carry_over.toggled.connect(self._on_carry_over_toggled)
        c_bar_layout.addWidget(self.chk_carry_over)

        c_bar_layout.addStretch()
        self.container_layout.addWidget(control_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        scroll_outer_container = QWidget()
        scroll_outer_container.setStyleSheet("background: transparent;")
        outer_layout = QHBoxLayout(scroll_outer_container)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        self.invoice_content_widget = QWidget()
        self.invoice_content_widget.setObjectName("InvoicePaperCanvas")
        self.invoice_content_widget.setFixedWidth(960)
        self.invoice_content_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.invoice_content_widget.setStyleSheet("""
            QWidget#InvoicePaperCanvas {
                background-color: #0F1420;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        self.c_lay = QVBoxLayout(self.invoice_content_widget)
        self.c_lay.setContentsMargins(28, 24, 28, 24)
        self.c_lay.setSpacing(14)

        outer_layout.addWidget(self.invoice_content_widget)
        scroll.setWidget(scroll_outer_container)
        self.container_layout.addWidget(scroll, stretch=1)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        btn_export = QPushButton("خروجی باکیفیت تصویر فاکتور رسمی (PNG)")
        btn_export.setIcon(IconProvider.get_icon("save", "#FFFFFF", size=14))
        btn_export.setIconSize(QSize(14, 14))
        btn_export.setFixedHeight(40)
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
                font-weight: 800;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_export.clicked.connect(self._export_image)
        action_bar.addWidget(btn_export, stretch=2)

        btn_close = QPushButton("بستن")
        btn_close.setFixedHeight(40)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 0 18px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; border-color: #6366F1; }
        """)
        btn_close.clicked.connect(self.accept)
        action_bar.addWidget(btn_close, stretch=1)

        self.container_layout.addLayout(action_bar)

    def _populate_initial_scope(self):
        full_summary = FinanceController.get_studio_debt_summary(self.client_id)
        all_projs = full_summary.get("all_projects", [])

        self.combo_single_proj.blockSignals(True)
        self.combo_single_proj.clear()
        for p in all_projs:
            self.combo_single_proj.addItem(f"{p['title']} (کد: {to_persian_numbers(p['project_number'])})", p["id"])
        self.combo_single_proj.blockSignals(False)

        if self.initial_project_id:
            idx = self.combo_single_proj.findData(self.initial_project_id)
            if idx >= 0:
                self.combo_scope.setCurrentIndex(1)
                self.combo_single_proj.setCurrentIndex(idx)
                self.selected_project_ids = {self.initial_project_id}
                return

        self.combo_scope.setCurrentIndex(0)
        self.selected_project_ids = {p["id"] for p in full_summary.get("unsettled_projects", [])}

    def _on_scope_changed(self):
        mode = self.combo_scope.currentData()
        full_summary = FinanceController.get_studio_debt_summary(self.client_id)
        all_projs = full_summary.get("all_projects", [])

        self.custom_date_widget.setVisible(mode == "custom_range")

        if mode == "single_project":
            self.combo_single_proj.setVisible(True)
            self.chk_carry_over.setEnabled(True)
            sel_pid = self.combo_single_proj.currentData()
            self.selected_project_ids = {sel_pid} if sel_pid else set()
        elif mode == "unsettled_only":
            self.combo_single_proj.setVisible(False)
            self.chk_carry_over.setEnabled(True)
            self.selected_project_ids = {p["id"] for p in full_summary.get("unsettled_projects", [])}
        elif mode == "this_month":
            self.combo_single_proj.setVisible(False)
            self.chk_carry_over.setEnabled(True)
            start_g, end_g = FinanceController.get_date_range_bounds("this_month")
            self.selected_project_ids = {
                p["id"] for p in all_projs 
                if (p.get("created_at") and start_g <= p["created_at"] <= end_g)
            }
        elif mode == "this_year":
            self.combo_single_proj.setVisible(False)
            self.chk_carry_over.setEnabled(True)
            start_g, end_g = FinanceController.get_date_range_bounds("this_year")
            self.selected_project_ids = {
                p["id"] for p in all_projs 
                if (p.get("created_at") and start_g <= p["created_at"] <= end_g)
            }
        elif mode == "custom_range":
            self.combo_single_proj.setVisible(False)
            self.chk_carry_over.setEnabled(True)
            self._filter_custom_dates(all_projs)
            return
        else:  # all_projects
            self.combo_single_proj.setVisible(False)
            self.chk_carry_over.setEnabled(False)
            self.selected_project_ids = {p["id"] for p in all_projs}

        self._refresh_invoice_calculation()

    def _on_custom_dates_changed(self):
        full_summary = FinanceController.get_studio_debt_summary(self.client_id)
        all_projs = full_summary.get("all_projects", [])
        self._filter_custom_dates(all_projs)

    def _filter_custom_dates(self, all_projs: List[dict]):
        s_date = parse_jalali_text(self.inp_start_date.text().strip())
        e_date = parse_jalali_text(self.inp_end_date.text().strip())

        start_dt = datetime.combine(s_date.togregorian(), datetime.min.time()) if s_date else None
        end_dt = datetime.combine(e_date.togregorian(), datetime.max.time()) if e_date else None

        filtered = set()
        for p in all_projs:
            p_dt = p.get("created_at")
            if not p_dt:
                continue
            if start_dt and p_dt < start_dt:
                continue
            if end_dt and p_dt > end_dt:
                continue
            filtered.add(p["id"])

        self.selected_project_ids = filtered
        self._refresh_invoice_calculation()

    def _on_single_proj_selected(self):
        if self.combo_scope.currentData() == "single_project":
            pid = self.combo_single_proj.currentData()
            if pid:
                self.selected_project_ids = {pid}
                self._refresh_invoice_calculation()

    def _on_carry_over_toggled(self, checked: bool):
        self.include_carry_over = checked
        self._refresh_invoice_calculation()

    def _refresh_invoice_calculation(self):
        summary = FinanceController.get_studio_debt_summary(
            self.client_id, 
            included_project_ids=list(self.selected_project_ids)
        )
        self._render_canvas_content(summary)

    def _render_canvas_content(self, summary: Dict[str, Any]):
        self._clear_layout_recursive(self.c_lay)

        today_str = gregorian_to_jalali(datetime.now())
        studio_brand = self.settings.get("studio_name", "").strip()
        editor_str = self.settings.get("editor_name", "").strip()

        # ۱. سربرگ سازمانی فاکتور
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #141B2B; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 10px;")
        h_box = QHBoxLayout(header_card)
        h_box.setContentsMargins(22, 16, 22, 16)
        h_box.setSpacing(18)
        h_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        logo_path = self.settings.get("studio_logo_path", "")
        if logo_path and Path(logo_path).exists():
            try:
                logo_lbl = QLabel()
                logo_lbl.setFixedSize(72, 72)
                logo_lbl.setScaledContents(True)
                logo_lbl.setStyleSheet("background: transparent; border: none; border-radius: 8px;")
                logo_lbl.setPixmap(QPixmap(logo_path))
                h_box.addWidget(logo_lbl)
            except Exception:
                pass

        studio_info = QVBoxLayout()
        studio_info.setSpacing(3)
        if not studio_brand or studio_brand.lower() == editor_str.lower():
            primary_header_title = "صورت‌حساب رسمی خدمات تدوین و پس‌تولید"
            secondary_header_title = f"تدوین‌گر و تصحیح‌کننده رنگ: {editor_str}" if editor_str else "خدمات تخصصی تدوین و پس‌تولید ویدیو"
        else:
            primary_header_title = studio_brand
            secondary_header_title = f"مدیریت تدوین و پس‌تولید: {editor_str}" if editor_str else "خدمات تخصصی تدوین و تصحیح رنگ ویدیو"

        studio_info.addWidget(self._make_clean_label(primary_header_title, "font-family: 'Vazirmatn'; font-size: 16px; font-weight: 900; color: #F8FAFC;"))
        studio_info.addWidget(self._make_clean_label(secondary_header_title, "font-family: 'Vazirmatn'; font-size: 11.5px; color: #818CF8; font-weight: 600;"))
        
        studio_phone = self.settings.get("phone", "")
        if studio_phone:
            studio_info.addWidget(self._make_clean_label(f"تلفن هماهنگی: {to_persian_numbers(studio_phone)}", "font-family: 'Vazirmatn'; font-size: 10.5px; color: #64748B;"))
        h_box.addLayout(studio_info, stretch=1)

        meta_box = QFrame()
        meta_box.setStyleSheet("background-color: #101624; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px;")
        m_lay = QVBoxLayout(meta_box)
        m_lay.setContentsMargins(14, 10, 14, 10)
        m_lay.setSpacing(4)
        m_lay.setAlignment(Qt.AlignmentFlag.AlignRight)

        safe_doc_num = f"INV-{datetime.now().strftime('%y%m')}-{self.client_id:03d}"
        m_lay.addWidget(self._make_clean_label(f"شماره سند: <b style='color:#F8FAFC;'>{safe_doc_num}</b>", "font-family: 'Segoe UI', 'Vazirmatn'; font-size: 11.5px; color: #94A3B8;"))
        m_lay.addWidget(self._make_clean_label(f"تاریخ صدور: <b style='color:#F8FAFC;'>{today_str}</b>", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8;"))
        
        tot_rem = summary.get("total_remaining", 0)
        if self.include_carry_over:
            tot_rem += summary.get("prior_unsettled_debt", 0)

        is_fully_settled = (tot_rem == 0)
        tag_color = "#10B981" if is_fully_settled else "#F59E0B"
        tag_text = "تسویه کامل (بدون بدهی) ✓" if is_fully_settled else "دارای مانده بدهی معوق"
        status_tag = self._make_clean_label(tag_text, f"font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 800; color: {tag_color}; padding-top: 2px;")
        m_lay.addWidget(status_tag)

        h_box.addWidget(meta_box)
        self.c_lay.addWidget(header_card)

        # ۲. مشخصات طرفین
        parties_frame = QFrame()
        parties_frame.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px;")
        p_grid = QGridLayout(parties_frame)
        p_grid.setContentsMargins(18, 12, 18, 12)
        p_grid.setHorizontalSpacing(24)
        p_grid.setVerticalSpacing(6)

        p_grid.addWidget(self._make_clean_label("طرف اول (تدوین‌گر / مجری پس‌تولید):", "font-family: 'Vazirmatn'; font-size: 11px; font-weight: bold; color: #818CF8;"), 0, 0)
        p_grid.addWidget(self._make_clean_label(editor_str or studio_brand or "تدوین‌گر", "font-family: 'Vazirmatn'; font-size: 12px; font-weight: bold; color: #F8FAFC;"), 1, 0)
        if studio_phone:
            p_grid.addWidget(self._make_clean_label(f"تلفن: {to_persian_numbers(studio_phone)}", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;"), 2, 0)

        p_grid.addWidget(self._make_clean_label("طرف دوم (کارفرما / استودیو):", "font-family: 'Vazirmatn'; font-size: 11px; font-weight: bold; color: #818CF8;"), 0, 1)
        client_desc = f"{self.client_name}" + (f" (مدیریت: {self.manager_name})" if self.manager_name else "")
        p_grid.addWidget(self._make_clean_label(client_desc, "font-family: 'Vazirmatn'; font-size: 12px; font-weight: bold; color: #F8FAFC;"), 1, 1)
        client_phone_display = to_persian_numbers(self.client_phone) if (self.client_phone and self.client_phone != "-") else "ثبت‌نشده"
        p_grid.addWidget(self._make_clean_label(f"شماره تماس: {client_phone_display}", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;"), 2, 1)

        p_grid.setColumnStretch(0, 1)
        p_grid.setColumnStretch(1, 1)
        self.c_lay.addWidget(parties_frame)

        # ۳. جدول اقلام سفارشات
        self.c_lay.addWidget(self._make_clean_label("شرح خدمات تدوین و وضعیت تسویه اقلام:", "font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #38BDF8; margin-top: 4px;"))

        table_card = QFrame()
        table_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        t_grid = QGridLayout(table_card)
        t_grid.setContentsMargins(14, 12, 14, 12)
        t_grid.setHorizontalSpacing(10)
        t_grid.setVerticalSpacing(4)

        mode = self.combo_scope.currentData()
        all_projs = summary.get("all_projects", [])

        if mode == "all_projects":
            display_projects = all_projs
        else:
            display_projects = [p for p in all_projs if p["id"] in self.selected_project_ids]

        headers = [
            ("ردیف", Qt.AlignmentFlag.AlignCenter),
            ("عنوان پروژه و کد پرونده", Qt.AlignmentFlag.AlignCenter),
            ("تاریخ مراسم", Qt.AlignmentFlag.AlignCenter),
            ("شرح خدمات تدوین و پکیج", Qt.AlignmentFlag.AlignCenter),
            ("مبلغ توافق‌شده", Qt.AlignmentFlag.AlignCenter),
            ("دریافتی", Qt.AlignmentFlag.AlignCenter),
            ("مانده", Qt.AlignmentFlag.AlignCenter)
        ]

        th_bg = QFrame()
        th_bg.setFixedHeight(34)
        th_bg.setStyleSheet("background-color: #161F30; border-radius: 6px;")
        t_grid.addWidget(th_bg, 0, 0, 1, 7)

        for col_idx, (h_title, align) in enumerate(headers):
            th_lbl = self._make_clean_label(h_title, "font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; color: #818CF8;")
            th_lbl.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
            t_grid.addWidget(th_lbl, 0, col_idx)

        t_grid.setColumnStretch(0, 4)   # ردیف
        t_grid.setColumnStretch(1, 26)  # پروژه
        t_grid.setColumnStretch(2, 12)  # تاریخ
        t_grid.setColumnStretch(3, 24)  # شرح
        t_grid.setColumnStretch(4, 12)  # قرارداد
        t_grid.setColumnStretch(5, 11)  # دریافتی
        t_grid.setColumnStretch(6, 11)  # مانده

        if not display_projects:
            lbl_empty = self._make_clean_label(
                "هیچ پروژه معوق یا مطابق بازه زمانی انتخابی یافت نشد (تمامی حساب‌ها تسویه می‌باشند).",
                "font-family: 'Vazirmatn'; font-size: 12px; color: #10B981; padding: 18px 0;"
            )
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            t_grid.addWidget(lbl_empty, 1, 0, 1, 7)
        else:
            for idx, p_summary in enumerate(display_projects):
                row_idx = idx + 1
                row_bg_color = "rgba(255, 255, 255, 0.02)" if idx % 2 == 1 else "transparent"
                row_frame = QFrame()
                row_frame.setStyleSheet(f"background-color: {row_bg_color}; border-radius: 5px;")
                t_grid.addWidget(row_frame, row_idx, 0, 1, 7)

                p_num = f"{p_summary.get('project_number', idx + 1):03d}"
                event_date_val = p_summary.get("created_at")
                event_str = gregorian_to_jalali(event_date_val) if event_date_val else "-"

                service_text = p_summary.get("service_description") or "تدوین پکیج مراسم"

                rem_val = p_summary.get("remaining", 0)
                rem_color = "#F59E0B" if rem_val > 0 else "#10B981"
                rem_text = format_toman(rem_val) if rem_val > 0 else "تسویه ✓"

                lbl_r1 = self._make_clean_label(to_persian_numbers(row_idx), "font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; padding: 4px 0;")
                lbl_r1.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r1, row_idx, 0)

                lbl_p_name = self._make_clean_label(f"<b>{p_summary.get('title', '-')}</b> (#{to_persian_numbers(p_num)})", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #F8FAFC; padding: 4px 0;")
                lbl_p_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_p_name, row_idx, 1)

                lbl_r3 = self._make_clean_label(event_str, "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; padding: 4px 0;")
                lbl_r3.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r3, row_idx, 2)

                lbl_r4 = self._make_clean_label(service_text, "font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600; color: #38BDF8; padding: 4px 0;")
                lbl_r4.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r4, row_idx, 3)

                lbl_r5 = self._make_clean_label(format_toman(p_summary.get("total_fee", 0)), "font-family: 'Vazirmatn'; font-size: 11px; color: #F8FAFC; padding: 4px 0;")
                lbl_r5.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r5, row_idx, 4)

                lbl_r6 = self._make_clean_label(format_toman(p_summary.get("total_paid", 0)), "font-family: 'Vazirmatn'; font-size: 11px; color: #10B981; padding: 4px 0;")
                lbl_r6.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r6, row_idx, 5)

                lbl_r7 = self._make_clean_label(rem_text, f"font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: {rem_color}; padding: 4px 0;")
                lbl_r7.setAlignment(Qt.AlignmentFlag.AlignCenter)
                t_grid.addWidget(lbl_r7, row_idx, 6)

        self.c_lay.addWidget(table_card)

        # ۴. پنل متقارن مشخصات بانکی، مهر رسمی و کادر بازطراحی‌شده محاسبات مالی
        bottom_panel = QHBoxLayout()
        bottom_panel.setSpacing(14)

        bank_plate = QFrame()
        bank_plate.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        bp_lay = QVBoxLayout(bank_plate)
        bp_lay.setContentsMargins(16, 12, 16, 12)
        bp_lay.setSpacing(8)

        bp_lay.addWidget(self._make_clean_label("اطلاعات واریز و تسویه حساب شتاب:", "font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #818CF8;"))

        raw_card = (self.settings.get("card_number") or "").replace(" ", "").replace("-", "").strip()
        card_number_clean = raw_card if raw_card else "ثبت‌نشده در تنظیمات"

        raw_iban = (self.settings.get("iban") or "").replace(" ", "").replace("-", "").strip()
        iban_clean = raw_iban if raw_iban else "ثبت‌نشده در تنظیمات"

        # کادر شماره کارت: عنوان در راست قفل و عدد در چپ قفل
        card_box_item = QFrame()
        card_box_item.setFixedHeight(36)
        card_box_item.setStyleSheet("background-color: #0E131F; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px;")
        cbi_lay = QHBoxLayout(card_box_item)
        cbi_lay.setContentsMargins(14, 0, 14, 0)
        cbi_lay.setSpacing(10)
        cbi_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_c_tag = self._make_clean_label("شماره کارت جهت واریز:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8;")
        cbi_lay.addWidget(lbl_c_tag)
        cbi_lay.addStretch()

        lbl_c_num = self._make_clean_label(card_number_clean, "font-family: 'Segoe UI', monospace; font-size: 14px; font-weight: 800; color: #FBBF24; letter-spacing: 0.5px;")
        lbl_c_num.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cbi_lay.addWidget(lbl_c_num)
        bp_lay.addWidget(card_box_item)

        # کادر شماره شبا: عنوان در راست قفل و عدد در چپ قفل
        iban_box_item = QFrame()
        iban_box_item.setFixedHeight(36)
        iban_box_item.setStyleSheet("background-color: #0E131F; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px;")
        ibi_lay = QHBoxLayout(iban_box_item)
        ibi_lay.setContentsMargins(14, 0, 14, 0)
        ibi_lay.setSpacing(10)
        ibi_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_i_tag = self._make_clean_label("شماره شبا حساب:", "font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8;")
        ibi_lay.addWidget(lbl_i_tag)
        ibi_lay.addStretch()

        lbl_ib = self._make_clean_label(iban_clean, "font-family: 'Segoe UI', monospace; font-size: 12.5px; font-weight: 700; color: #CBD5E1; letter-spacing: 0.5px;")
        lbl_ib.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        ibi_lay.addWidget(lbl_ib)
        bp_lay.addWidget(iban_box_item)

        # ردیف تعهدات حقوقی هم‌تراز (Justified) به همراه پلاک درشت مهر و امضا
        legal_and_seal_row = QHBoxLayout()
        legal_and_seal_row.setSpacing(14)
        legal_and_seal_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_legal_clause = QLabel(
            "«کلیه حقوق مادی و معنوی، سورس پروژه‌های تدوین و راش‌های خام تا زمان تسویه نهایی حساب متعلق به تدوین‌گر می‌باشد. "
            "پس از تسویه کامل این صورت‌حساب، مجوز استفاده و تحویل مستر به استودیو واگذار گردیده و به دلیل محدودیت فضای هارد، "
            "نگهداری راش‌ها و آرشیو پروژه پس از ۷ روز از تاریخ تحویل، به کلی از تعهد تدوین‌گر خارج خواهد بود.»"
        )
        lbl_legal_clause.setWordWrap(True)
        lbl_legal_clause.setAlignment(Qt.AlignmentFlag.AlignJustify)
        lbl_legal_clause.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 10px;
                color: #94A3B8;
                line-height: 1.68;
                font-weight: 500;
                background: transparent;
                border: none;
            }
        """)
        legal_and_seal_row.addWidget(lbl_legal_clause, stretch=1)

        sign_path = self.settings.get("studio_signature_path", "")
        if sign_path and Path(sign_path).exists():
            try:
                sign_wrapper_col = QVBoxLayout()
                sign_wrapper_col.setSpacing(3)
                sign_wrapper_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

                lbl_sign_outer_title = self._make_clean_label(
                    "مهر و امضای تدوین‌گر", 
                    "font-family: 'Vazirmatn'; font-size: 9.5px; font-weight: 700; color: #818CF8;"
                )
                lbl_sign_outer_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                sign_wrapper_col.addWidget(lbl_sign_outer_title)

                sign_plate = QFrame()
                sign_plate.setFixedSize(185, 82)
                sign_plate.setStyleSheet("background-color: #0E131F; border: 1px dashed rgba(99, 102, 241, 0.45); border-radius: 8px;")
                sp_lay = QVBoxLayout(sign_plate)
                sp_lay.setContentsMargins(6, 6, 6, 6)
                sp_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

                s_img = QLabel()
                s_img.setStyleSheet("background: transparent !important; border: none !important;")
                s_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                s_img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                
                orig_sign_pix = QPixmap(sign_path)
                s_img.setPixmap(orig_sign_pix.scaled(170, 70, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                sp_lay.addWidget(s_img)

                sign_wrapper_col.addWidget(sign_plate)
                legal_and_seal_row.addLayout(sign_wrapper_col)
            except Exception:
                pass

        bp_lay.addLayout(legal_and_seal_row)
        bottom_panel.addWidget(bank_plate, stretch=3)

        # =========================================================================
        # بازطراحی کادر محاسبات مالی: کادر تسویه بزرگ و کشیده به همراه عدد بزرگ وسط‌چین
        # =========================================================================
        calc_box = QFrame()
        calc_box.setStyleSheet("""
            QFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)
        calc_lay = QVBoxLayout(calc_box)
        calc_lay.setContentsMargins(14, 12, 14, 12)
        calc_lay.setSpacing(6)

        # هدر بالای کارت محاسبات
        calc_top_header = QHBoxLayout()
        calc_top_header.setContentsMargins(2, 0, 2, 0)
        calc_top_header.setSpacing(6)
        
        lbl_calc_head = self._make_clean_label("صورت‌وضعیت و جمع کل فاکتور:", "font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #818CF8;")
        calc_top_header.addWidget(lbl_calc_head)
        calc_top_header.addStretch()

        tot_fee = summary.get("total_fee", 0)
        tot_paid = summary.get("total_paid", 0)
        current_rem = summary.get("total_remaining", 0)
        prior_debt = summary.get("prior_unsettled_debt", 0)
        final_payable = current_rem + (prior_debt if self.include_carry_over else 0)

        paid_ratio_pct = int((tot_paid / tot_fee) * 100) if tot_fee > 0 else 100
        lbl_pct_tag = self._make_clean_label(
            f"{to_persian_numbers(paid_ratio_pct)}٪ وصول",
            "font-family: 'Vazirmatn'; font-size: 9.5px; font-weight: 700; color: #10B981; "
            "background-color: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.25); "
            "border-radius: 4px; padding: 1px 6px;"
        )
        calc_top_header.addWidget(lbl_pct_tag)
        calc_lay.addLayout(calc_top_header)

        # ردیف ۱: ارزش اقلام انتخابی
        f_row_frame = QFrame()
        f_row_frame.setFixedHeight(28)
        f_row_frame.setStyleSheet("background-color: #0E131F; border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 5px;")
        fr_lay = QHBoxLayout(f_row_frame)
        fr_lay.setContentsMargins(10, 0, 10, 0)
        fr_lay.addWidget(self._make_clean_label("ارزش اقلام انتخابی:", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;"))
        fr_lay.addStretch()
        fr_lay.addWidget(self._make_clean_label(format_toman(tot_fee), "font-family: 'Segoe UI', 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: #F8FAFC;"))
        calc_lay.addWidget(f_row_frame)

        # ردیف ۲: دریافتی اقلام انتخابی
        p_row_frame = QFrame()
        p_row_frame.setFixedHeight(28)
        p_row_frame.setStyleSheet("background-color: #0E131F; border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 5px;")
        pr_lay = QHBoxLayout(p_row_frame)
        pr_lay.setContentsMargins(10, 0, 10, 0)
        pr_lay.addWidget(self._make_clean_label("دریافتی اقلام انتخابی:", "font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;"))
        pr_lay.addStretch()
        pr_lay.addWidget(self._make_clean_label(format_toman(tot_paid), "font-family: 'Segoe UI', 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: #10B981;"))
        calc_lay.addWidget(p_row_frame)

        # ردیف ۳ (در صورت وجود): مانده بدهی قبلی
        if self.include_carry_over and prior_debt > 0:
            d_row_frame = QFrame()
            d_row_frame.setFixedHeight(28)
            d_row_frame.setStyleSheet("background-color: #0E131F; border: 1px solid rgba(251, 146, 60, 0.2); border-radius: 5px;")
            dr_lay = QHBoxLayout(d_row_frame)
            dr_lay.setContentsMargins(10, 0, 10, 0)
            dr_lay.addWidget(self._make_clean_label("مانده بدهی از پروژه‌های قبلی:", "font-family: 'Vazirmatn'; font-size: 11px; color: #FB923C;"))
            dr_lay.addStretch()
            dr_lay.addWidget(self._make_clean_label(format_toman(prior_debt), "font-family: 'Segoe UI', 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #FB923C;"))
            calc_lay.addWidget(d_row_frame)

        # کادر برجسته، گسترده و کشیده مبلغ نهایی (پرکننده تمام ارتفاع خالی با عدد بزرگ در مرکز)
        final_box = QFrame()
        final_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if final_payable > 0:
            final_box_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E1610, stop:1 #17110C)"
            final_box_border = "rgba(245, 158, 11, 0.55)"
            status_text = "مانده قابل پرداخت"
            status_color = "#F59E0B"
            rem_col = "#FBBF24"
        else:
            final_box_bg = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0B1C1A, stop:1 #0A1715)"
            final_box_border = "rgba(16, 185, 129, 0.55)"
            status_text = "تسویه کامل شده ✓"
            status_color = "#10B981"
            rem_col = "#34D399"

        final_box.setStyleSheet(f"""
            QFrame {{
                background: {final_box_bg};
                border: 1.5px solid {final_box_border};
                border-radius: 8px;
            }}
        """)
        fb_lay = QVBoxLayout(final_box)
        fb_lay.setContentsMargins(14, 8, 14, 10)
        fb_lay.setSpacing(4)

        # نوار بالای کادر تسویه: عنوان در راست و وضعیت در چپ
        fb_top = QHBoxLayout()
        fb_top.setContentsMargins(0, 0, 0, 0)
        fb_top.addWidget(self._make_clean_label("مبلغ نهایی قابل تسویه:", "font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: #CBD5E1;"))
        fb_top.addStretch()
        fb_top.addWidget(self._make_clean_label(status_text, f"font-family: 'Vazirmatn'; font-size: 10px; font-weight: 800; color: {status_color};"))
        fb_lay.addLayout(fb_top)

        # بخش اصلی مرکز کادر: مبلغ به صورت درشت، بزرگ و کاملاً وسط‌چین
        lbl_rem_amount = self._make_clean_label(
            format_toman(final_payable), 
            f"font-family: 'Vazirmatn'; font-size: 22px; font-weight: 900; color: {rem_col};"
        )
        lbl_rem_amount.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fb_lay.addWidget(lbl_rem_amount, stretch=1)

        calc_lay.addWidget(final_box, stretch=1)

        bottom_panel.addWidget(calc_box, stretch=2)
        self.c_lay.addLayout(bottom_panel)

        # ۵. نوار اصالت سند و هش رمزنگاری‌شده ضدجعل
        raw_hash_source = f"{self.client_id}:{safe_doc_num}:{final_payable}:{today_str}"
        secret_key = b"CutterLogProStudioMasterKey_2026"
        computed_hash = hmac.new(secret_key, raw_hash_source.encode("utf-8"), hashlib.sha256).hexdigest()[:16].upper()
        formatted_hash_seal = f"CLP-{computed_hash[:4]}-{computed_hash[4:8]}-{computed_hash[8:12]}"

        software_badge = QFrame()
        software_badge.setFixedHeight(36)
        software_badge.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #0B0E17, stop:0.5 #121828, stop:1 #0B0E17);
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 8px;
            }
        """)
        sb_lay = QHBoxLayout(software_badge)
        sb_lay.setContentsMargins(16, 0, 16, 0)
        sb_lay.setSpacing(10)
        sb_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_verified = QLabel("VERIFIED INVOICE")
        lbl_verified.setStyleSheet("""
            font-family: 'Segoe UI', sans-serif;
            font-size: 8.5px;
            font-weight: 900;
            color: #10B981;
            background-color: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.25);
            border-radius: 4px;
            padding: 2px 6px;
            letter-spacing: 0.5px;
        """)
        sb_lay.addWidget(lbl_verified)

        logo_icon = QLabel()
        logo_icon.setPixmap(IconProvider.get_pixmap("clp_brand_mark", "#818CF8", size=14))
        logo_icon.setStyleSheet("background: transparent; border: none;")
        sb_lay.addWidget(logo_icon)

        lbl_promo = self._make_clean_label(
            "تولیدشده توسط سامانه مدیریت پایپ‌لاین تدوین CutterLog Pro",
            "font-family: 'Vazirmatn'; font-size: 11px; font-weight: 700; color: #F8FAFC;"
        )
        sb_lay.addWidget(lbl_promo)

        sb_lay.addStretch()

        lbl_crypto_seal = QLabel(f"SEAL: {formatted_hash_seal}")
        lbl_crypto_seal.setToolTip("شناسه هش اصالت فاکتور جهت جلوگیری از جعل سند")
        lbl_crypto_seal.setStyleSheet("""
            font-family: 'Segoe UI', monospace;
            font-size: 9px;
            font-weight: 800;
            color: #A5B4FC;
            background: rgba(99, 102, 241, 0.16);
            border: 1px solid rgba(99, 102, 241, 0.35);
            border-radius: 4px;
            padding: 2px 7px;
            letter-spacing: 0.8px;
        """)
        sb_lay.addWidget(lbl_crypto_seal)

        lbl_promo_en = self._make_clean_label(
            "Official Post-Production Workflow & Ledger",
            "font-family: 'Segoe UI', sans-serif; font-size: 9.5px; font-weight: 600; color: #818CF8; letter-spacing: 0.3px;"
        )
        sb_lay.addWidget(lbl_promo_en)

        self.c_lay.addWidget(software_badge)

    def _export_image(self):
        def _to_english_numbers(num_str: str) -> str:
            fa_nums = '۰۱۲۳۴۵۶۷۸۹'
            en_nums = '0123456789'
            trans = str.maketrans(fa_nums, en_nums)
            return num_str.translate(trans)

        shamsi_raw = gregorian_to_jalali(datetime.now())
        shamsi_en_date = _to_english_numbers(shamsi_raw).replace('/', '-')

        default_filename = f"Billing Statement - {shamsi_en_date}.png"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "ذخیره تصویر فاکتور رسمی استودیو",
            default_filename,
            "PNG Image (*.png)"
        )
        if not file_path:
            return

        try:
            success = StudioInvoiceImageExporter.export_widget_to_image(self.invoice_content_widget, file_path, scale_factor=3.5)
            if success:
                StudioConfirmDialog.ask(
                    self, 
                    title="موفقیت", 
                    message="تصویر فاکتور رسمی با بالاترین کیفیت ذخیره شد.", 
                    details=f"مسیر ذخیره:\n{file_path}", 
                    confirm_text="متوجه شدم", 
                    icon_name="check"
                )
            else:
                StudioConfirmDialog.ask(
                    self, 
                    title="خطا", 
                    message="خطا در ذخیره تصویر فاکتور.", 
                    is_danger=True, 
                    icon_name="alert"
                )
        except Exception as err:
            StudioConfirmDialog.ask(
                self, 
                title="خطا", 
                message=f"خطای سیستمی رخ داد:\n{err}", 
                is_danger=True, 
                icon_name="alert"
            )