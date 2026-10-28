# ==================================================
# FILE: widgets/project_card_mini.py
# ==================================================
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSizePolicy, QFrame, QWidget
)
from PySide6.QtCore import Qt, QTimer

from config import open_path_in_os
from core.persian_utils import (
    format_toman, gregorian_to_jalali, to_persian_numbers, clean_studio_display_name
)
from core.signals import global_signals
from core.project_controller import ProjectController
from core.nle_messenger_helper import NleLauncherHelper, ClientMessengerHelper
from core.icon_provider import IconProvider
from widgets.base_card import BaseProjectCard
from widgets.status_badge import StatusPillBadge, StatusType
from widgets.project_details_dialog import ProjectDetailsDialog
from widgets.edit_project_dialog import EditProjectDialog
from widgets.new_transaction_dialog import NewTransactionDialog
from widgets.project_timeline import NewRevisionDialog
from widgets.dynamic_clip_bar import DynamicClipOverviewBar
from widgets.studio_dialog_base import StudioConfirmDialog
from widgets.studio_menu import StudioMenu
from time_tracking.timer_engine import TimeTrackingEngine


def get_persian_nle_short_label(file_path: str) -> str:
    """تشخیص نرم‌افزار تدوین با برچسب کوتاه و کاملاً فارسی"""
    if not file_path:
        return "تدوین"
    p = Path(file_path)
    ext = p.suffix.replace(".", "").upper()
    nle_names = {
        "PRPROJ": "پریمیر",
        "DRP": "داوینچی",
        "AEP": "افتر افکت",
        "FCPXML": "فاینال کات",
        "XML": "XML",
        "EDL": "EDL",
        "PSD": "فتوشاپ"
    }
    return nle_names.get(ext, ext[:6])


class ProjectCardMini(BaseProjectCard):
    """
    کارت مینیاتوری پیشخوان (Cockpit Action Card)
    دارای پایش بصری پررنگ ددلاین‌های بحرانی و تاخیرخورده
    """
    def __init__(self, project_data: dict, parent=None):
        project_id = project_data.get("id", 0)
        project_number = project_data.get("project_number", project_id)
        
        super().__init__(
            project_id=project_id,
            project_number=project_number,
            parent=parent,
            accent_color="#818CF8",
            card_type="dashboard"
        )
        self.project_data = project_data
        self.is_overdue = False
        self.is_critical_deadline = False
        self.days_remaining = None
        
        self.setFixedHeight(178)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.init_mini_content()

    def init_mini_content(self):
        active_rev_title = self.project_data.get("active_revision_title")
        progress_val = self.project_data.get("progress_pct", 0)
        c_cnt = self.project_data.get("completed_clips", 0)
        t_cnt = self.project_data.get("total_clips", 0)
        status_info = self.project_data.get("status_info", {})
        status_key = status_info.get("key", "")

        # ۱. آنالیز دقیق روزهای باقیمانده تا ددلاین
        self.is_overdue = False
        self.is_critical_deadline = False
        self.days_remaining = None
        
        deadline_dt = self.project_data.get("deadline")
        dead_str = "ثبت‌نشده"
        deadline_badge_text = ""
        
        if deadline_dt:
            dead_str = gregorian_to_jalali(deadline_dt)
            now_dt = datetime.utcnow().date()
            p_dead_date = deadline_dt.date() if isinstance(deadline_dt, datetime) else deadline_dt
            delta_days = (p_dead_date - now_dt).days
            self.days_remaining = delta_days

            if progress_val < 100:
                if delta_days < 0:
                    self.is_overdue = True
                    overdue_days = abs(delta_days)
                    deadline_badge_text = f"⚠️ {to_persian_numbers(overdue_days)} روز تاخیر"
                elif delta_days == 0:
                    self.is_critical_deadline = True
                    deadline_badge_text = "⏳ سررسید امروز!"
                elif delta_days <= 2:
                    self.is_critical_deadline = True
                    deadline_badge_text = f"⏳ {to_persian_numbers(delta_days)} روز مانده"

        # ۲. استایل پس‌زمینه و حاشیه بر اساس اولویت ددلاین
        if self.is_overdue:
            bg_color = "#160F1A"
            border_css = "1.5px solid rgba(239, 68, 68, 0.65)"
            hover_border = "#EF4444"
        elif self.is_critical_deadline:
            bg_color = "#15131E"
            border_css = "1.5px solid rgba(245, 158, 11, 0.55)"
            hover_border = "#F59E0B"
        elif active_rev_title:
            bg_color = "#131224"
            border_css = "1px solid rgba(249, 115, 22, 0.40)"
            hover_border = "#FB923C"
        elif progress_val >= 100:
            bg_color = "#0B151C"
            border_css = "1px solid rgba(16, 185, 129, 0.40)"
            hover_border = "#34D399"
        else:
            bg_color = "#0E1322"
            border_css = "1px solid rgba(255, 255, 255, 0.06)"
            hover_border = "rgba(99, 102, 241, 0.55)"

        self.setStyleSheet(f"""
            QFrame#BaseCardFrame {{
                background-color: {bg_color};
                border: {border_css};
                border-radius: 11px;
            }}
            QFrame#BaseCardFrame:hover {{
                background-color: #12182B;
                border: 1.5px solid {hover_border};
            }}
        """)

        # ۳. بج وضعیت روند تدوین
        if self.is_overdue or self.is_critical_deadline:
            # کپسول ددلاین بحرانی جایگزین وضعیت عادی می‌شود
            badge_bg = "rgba(239, 68, 68, 0.18)" if self.is_overdue else "rgba(245, 158, 11, 0.18)"
            badge_col = "#F87171" if self.is_overdue else "#FBBF24"
            badge_border = "rgba(239, 68, 68, 0.45)" if self.is_overdue else "rgba(245, 158, 11, 0.40)"
            
            lbl_deadline_status = QLabel(deadline_badge_text)
            lbl_deadline_status.setFixedHeight(22)
            lbl_deadline_status.setStyleSheet(f"""
                QLabel {{
                    font-family: 'Vazirmatn';
                    font-size: 10px;
                    font-weight: 800;
                    color: {badge_col};
                    background-color: {badge_bg};
                    border: 1px solid {badge_border};
                    border-radius: 5px;
                    padding: 0 8px;
                }}
            """)
            self.header_tags_layout.addWidget(lbl_deadline_status)
        else:
            if active_rev_title:
                rev_prog = self.project_data.get("rev_progress_pct", 0)
                status_text = f"اصلاحیه: {to_persian_numbers(rev_prog)}٪"
                status_type = StatusType.WARNING
            elif status_key == "under_review":
                status_text = "منتظر بازبینی"
                status_type = StatusType.PENDING
            elif progress_val >= 100 or (t_cnt > 0 and c_cnt == t_cnt):
                status_text = "آماده تحویل"
                status_type = StatusType.COMPLETED
            elif c_cnt == 0:
                status_text = "در انتظار شروع"
                status_type = StatusType.NEUTRAL
            else:
                status_text = f"پیشرفت: {to_persian_numbers(progress_val)}٪"
                status_type = StatusType.ACTIVE

            self.status_badge = StatusPillBadge(
                label=status_text, 
                status_type=status_type, 
                custom_symbol=""
            )
            self.header_tags_layout.addWidget(self.status_badge)

        # ۴. بج وضعیت مالی
        rem_amount = self.project_data.get("remaining_amount", 0)
        total_fee = self.project_data.get("total_fee", 0)
        is_settled = (rem_amount == 0 and total_fee > 0) or self.project_data.get("is_settled", False)

        if is_settled:
            fin_text = "تسویه ✓"
            fin_bg = "rgba(16, 185, 129, 0.14)"
            fin_color = "#34D399"
            fin_border = "rgba(16, 185, 129, 0.30)"
        elif rem_amount > 0:
            fin_text = f"مانده: {format_toman(rem_amount)}"
            fin_bg = "rgba(251, 146, 60, 0.14)"
            fin_color = "#FB923C"
            fin_border = "rgba(251, 146, 60, 0.35)"
        else:
            fin_text = "بدون مبلغ"
            fin_bg = "rgba(255, 255, 255, 0.04)"
            fin_color = "#64748B"
            fin_border = "rgba(255, 255, 255, 0.06)"

        self.badge_fin = QLabel(fin_text)
        self.badge_fin.setFixedHeight(22)
        self.badge_fin.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.badge_fin.setStyleSheet(f"""
            QLabel {{
                font-family: 'Vazirmatn';
                font-size: 10px;
                font-weight: 700;
                color: {fin_color};
                background-color: {fin_bg};
                border: 1px solid {fin_border};
                border-radius: 5px;
                padding: 0 7px;
            }}
        """)
        self.header_tags_layout.addWidget(self.badge_fin)
        self.header_tags_layout.addStretch()

        # دکمه منوی سه نقطه
        btn_menu = QPushButton("⋮")
        btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_menu.setFixedSize(22, 22)
        btn_menu.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8F909D;
                border: none;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #F8FAFC;
                background-color: rgba(255, 255, 255, 0.08);
                border-radius: 4px;
            }
        """)
        btn_menu.clicked.connect(lambda: self._show_context_menu(btn_menu))
        self.header_layout.addWidget(btn_menu)

        # ۵. نام پروژه و استودیو
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_box.setContentsMargins(0, 2, 0, 2)

        couple_name = self.project_data.get("couple_names") or self.project_data.get("title", "پروژه")
        self.lbl_title = QLabel(couple_name)
        self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        title_box.addWidget(self.lbl_title)

        raw_client = self.project_data.get("client_name") or "بدون استودیو"
        client_display = clean_studio_display_name(raw_client)
        self.lbl_studio = QLabel(f"استودیو: <span style='color:#38BDF8;'>{client_display}</span>")
        self.lbl_studio.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #94A3B8; border: none; background: transparent;")
        title_box.addWidget(self.lbl_studio)

        self.card_layout.addLayout(title_box)

        # ۶. نوار پیشرفت کلیپ‌ها
        clips_data = self.project_data.get("clips_list", [])
        self.clip_bar = DynamicClipOverviewBar(clips_data=clips_data, parent=self)
        self.clip_bar.setFixedHeight(8)
        self.card_layout.addWidget(self.clip_bar)

        # ۷. خط متادیتا با نمایش رنگی ددلاین
        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 2, 0, 2)
        meta_row.setSpacing(8)

        if self.is_overdue:
            dead_color_css = "#F87171"
            dead_icon = "⚠️"
        elif self.is_critical_deadline:
            dead_color_css = "#FBBF24"
            dead_icon = "⏳"
        else:
            dead_color_css = "#818CF8"
            dead_icon = "📅"

        self.lbl_deadline = QLabel(f"{dead_icon} موعد: <b style='color:{dead_color_css};'>{to_persian_numbers(dead_str)}</b>")
        self.lbl_deadline.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #94A3B8; border: none; background: transparent;")
        meta_row.addWidget(self.lbl_deadline)

        meta_row.addStretch()

        rem_clips_cnt = max(0, t_cnt - c_cnt)
        rem_clips_text = "کلیپ‌ها کامل شد ✓" if rem_clips_cnt == 0 and t_cnt > 0 else f"{to_persian_numbers(rem_clips_cnt)} کلیپ باقیمانده"
        self.lbl_clips_rem = QLabel(rem_clips_text)
        self.lbl_clips_rem.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10px; color: #64748B; border: none; background: transparent;")
        meta_row.addWidget(self.lbl_clips_rem)

        self.card_layout.addLayout(meta_row)

        # ۸. نوار ابزار فوتر
        dock_row = QHBoxLayout()
        dock_row.setContentsMargins(0, 2, 0, 0)
        dock_row.setSpacing(6)
        dock_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # دکمه نرم‌افزار NLE
        nle_path = self.project_data.get("nle_project_path", "")
        persian_nle = get_persian_nle_short_label(nle_path)
        has_nle = bool(nle_path and Path(nle_path).exists())

        self.btn_nle = QPushButton(persian_nle)
        self.btn_nle.setFixedHeight(26)
        self.btn_nle.setCursor(Qt.CursorShape.PointingHandCursor if has_nle else Qt.CursorShape.ForbiddenCursor)
        self.btn_nle.setToolTip(f"اجرای مستقیم در {persian_nle}\n{nle_path}" if has_nle else "فایل تدوین متصل نشده است")
        self.btn_nle.setStyleSheet(f"""
            QPushButton {{
                font-family: 'Vazirmatn';
                font-size: 10.5px;
                font-weight: 700;
                color: {'#C7D2FE' if has_nle else '#475569'};
                background-color: {'rgba(99, 102, 241, 0.16)' if has_nle else 'rgba(255, 255, 255, 0.03)'};
                border: 1px solid {'rgba(99, 102, 241, 0.38)' if has_nle else 'rgba(255, 255, 255, 0.06)'};
                border-radius: 5px;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background-color: #6366F1;
                color: #FFFFFF;
                border-color: #818CF8;
            }}
        """)
        self.btn_nle.clicked.connect(self._launch_nle)
        dock_row.addWidget(self.btn_nle)

        # دکمه پوشه راش‌ها
        primary_path = self.project_data.get("primary_path", "")
        has_folder = bool(primary_path and Path(primary_path).exists())

        self.btn_folder = QPushButton("پوشه راش‌ها")
        self.btn_folder.setFixedHeight(26)
        self.btn_folder.setCursor(Qt.CursorShape.PointingHandCursor if has_folder else Qt.CursorShape.ForbiddenCursor)
        self.btn_folder.setToolTip(f"باز کردن پوشه راش‌ها:\n{primary_path}" if has_folder else "پوشه هارد متصل نیست")
        self.btn_folder.setStyleSheet(f"""
            QPushButton {{
                font-family: 'Vazirmatn';
                font-size: 10.5px;
                font-weight: 600;
                color: {'#E2E8F0' if has_folder else '#475569'};
                background-color: #141B2D;
                border: 1px solid {'rgba(255, 255, 255, 0.10)' if has_folder else 'rgba(255, 255, 255, 0.04)'};
                border-radius: 5px;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                border-color: #38BDF8;
                color: #FFFFFF;
                background-color: #1A243D;
            }}
        """)
        self.btn_folder.clicked.connect(self._open_folder)
        dock_row.addWidget(self.btn_folder)

        dock_row.addStretch()

        # دکمه شروع کار
        self.btn_work = QPushButton("شروع کار")
        self.btn_work.setFixedHeight(26)
        self.btn_work.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_work.setToolTip("انتخاب پروژه در تایم‌ترکینگ و شروع زمان تدوین")
        
        # استایل دکمه کار: در حالت تاخیر/بحرانی به رنگ تاکیدی گرم درمی‌آید
        if self.is_overdue or self.is_critical_deadline:
            work_grad = "stop:0 #F59E0B, stop:1 #D97706"
            work_hover = "stop:0 #FBBF24, stop:1 #F59E0B"
            work_border = "#FCD34D"
        else:
            work_grad = "stop:0 #10B981, stop:1 #059669"
            work_hover = "stop:0 #34D399, stop:1 #10B981"
            work_border = "#6EE7B7"

        self.btn_work.setStyleSheet(f"""
            QPushButton {{
                font-family: 'Vazirmatn';
                font-size: 10.5px;
                font-weight: 800;
                color: #FFFFFF;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, {work_grad});
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, {work_hover});
                border-color: {work_border};
            }}
        """)
        self.btn_work.clicked.connect(self._start_timer_session)
        dock_row.addWidget(self.btn_work)

        self.card_layout.addLayout(dock_row)

        # کلیک روی بدنه کارت
        self.clicked.connect(lambda _: self._open_details())

    def _show_context_menu(self, anchor_btn: QPushButton):
        menu = StudioMenu(self)

        t_cnt = self.project_data.get("total_clips", 0)
        c_cnt = self.project_data.get("completed_clips", 0)
        prog_val = self.project_data.get("progress_pct", 0)
        status_info = self.project_data.get("status_info", {})
        status_key = status_info.get("key", "")

        act_deliver = None
        if (prog_val >= 100 or (t_cnt > 0 and c_cnt == t_cnt)) and (status_key != "under_review"):
            act_deliver = menu.addAction(IconProvider.get_icon("check", "#06B6D4", size=14), "تحویل رسمی به استودیو")

        act_pay = menu.addAction(IconProvider.get_icon("dollar", "#10B981", size=14), "ثبت واریزی و تسویه مالی")
        act_rev = menu.addAction(IconProvider.get_icon("revision", "#F97316", size=14), "ثبت دور اصلاحیه جدید")
        act_edit = menu.addAction(IconProvider.get_icon("edit", "#818CF8", size=14), "ویرایش مشخصات پروژه")
        act_copy_msg = menu.addAction(IconProvider.get_icon("message", "#38BDF8", size=14), "کپی متن وضعیت برای استودیو")

        menu.addSeparator()
        act_delete = menu.addAction(IconProvider.get_icon("trash", "#EF4444", size=14), "حذف پرونده پروژه")

        action = menu.show_beside_button(anchor_btn)

        if act_deliver and action == act_deliver:
            self._mark_as_delivered()
        elif action == act_pay:
            self._open_payment()
        elif action == act_rev:
            self._open_new_revision()
        elif action == act_edit:
            self._open_edit_dialog()
        elif action == act_copy_msg:
            self._copy_client_message()
        elif action == act_delete:
            self._delete_project()

    def _launch_nle(self):
        nle_path = self.project_data.get("nle_project_path", "")
        success, message = NleLauncherHelper.launch_project(nle_path)
        if success:
            global_signals.show_toast.emit(message, "success")
        else:
            global_signals.show_toast.emit(message, "error")

    def _open_folder(self):
        path_str = self.project_data.get("primary_path")
        if not path_str or not Path(path_str).exists():
            global_signals.show_toast.emit("مسیر پوشه راش‌ها متصل نیست.", "error")
            return
        open_path_in_os(path_str)

    def _start_timer_session(self):
        engine = TimeTrackingEngine.instance()
        engine.select_context(self.project_id, None)
        global_signals.navigate_to_page.emit(6)

    def _open_details(self):
        win = self.window()
        QTimer.singleShot(0, lambda: ProjectDetailsDialog(self.project_id, win).exec())

    def _open_edit_dialog(self):
        diag = EditProjectDialog(self.project_id, self.window())
        diag.exec()

    def _open_payment(self):
        diag = NewTransactionDialog(self.project_id, parent=self.window())
        diag.exec()

    def _open_new_revision(self):
        diag = NewRevisionDialog(self.project_id, self.window())
        diag.exec()

    def _copy_client_message(self):
        msg = ClientMessengerHelper.generate_client_message(self.project_data)
        if ClientMessengerHelper.copy_message_to_clipboard(msg):
            global_signals.show_toast.emit("متن آخرین وضعیت پروژه در کلیپ‌بورد کپی شد.", "success")

    def _mark_as_delivered(self):
        couple = self.project_data.get("couple_names") or self.project_data.get("title") or "پروژه"
        fee = self.project_data.get("total_fee", 0)
        
        if StudioConfirmDialog.ask(
            self.window(),
            title="تأیید تحویل به استودیو",
            message=f"آیا فایل‌های پروژه «{couple}» آماده تحویل به استودیو است؟",
            details=f"با ثبت تحویل، مبلغ {format_toman(fee)} وارد دفتر مالی شده و شمارش معکوس بازبینی آغاز می‌گردد.",
            confirm_text="تأیید تحویل و ثبت در مالی",
            is_danger=False,
            icon_name="check"
        ):
            if ProjectController.mark_as_delivered(self.project_id):
                client_id = None
                p = ProjectController.get_project_by_id(self.project_id)
                if p:
                    client_id = p.client_id
                
                global_signals.transaction_recorded.emit(0)
                if client_id:
                    global_signals.client_balance_updated.emit(client_id)
                global_signals.show_toast.emit(f"پروژه «{couple}» با موفقیت تحویل شد.", "success")

    def _delete_project(self):
        couple = self.project_data.get('couple_names') or 'پروژه'
        if StudioConfirmDialog.ask(
            self.window(),
            title="حذف کامل پروژه",
            message=f"آیا از حذف کامل پرونده «{couple}» اطمینان دارید؟",
            details="تمام کلیپ‌ها، دوره‌های اصلاحیه، لاگ‌ها و تراکنش‌های مالی این پروژه حذف خواهند شد.",
            confirm_text="حذف دائمی",
            is_danger=True,
            icon_name="trash"
        ):
            ProjectController.delete_project(self.project_id)