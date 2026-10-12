# ==================================================
# FILE: widgets/project_card.py
# ==================================================
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer

from config import open_path_in_os
from core.persian_utils import format_toman, gregorian_to_jalali, to_persian_numbers, clean_studio_display_name
from core.project_controller import ProjectController
from core.finance_controller import FinanceController
from core.nle_messenger_helper import NleLauncherHelper
from widgets.base_card import BaseProjectCard
from widgets.status_badge import StatusPillBadge, StatusType
from widgets.project_details_dialog import ProjectDetailsDialog
from widgets.edit_project_dialog import EditProjectDialog
from widgets.new_transaction_dialog import NewTransactionDialog
from widgets.project_timeline import NewRevisionDialog
from widgets.dynamic_clip_bar import DynamicClipOverviewBar
from widgets.studio_share_dialog import StudioShareDialog
from widgets.quick_messenger_popup import QuickMessengerMiniPopup
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog
from widgets.studio_menu import StudioMenu
from core.signals import global_signals
from core.icon_provider import IconProvider


def get_persian_nle_name(file_path: str) -> str:
    """تشخیص نرم‌افزار تدوین و بازگردانی نام ۱۰۰٪ فارسی"""
    if not file_path:
        return "پروژه تدوین"
    p = Path(file_path)
    ext = p.suffix.replace(".", "").upper()
    nle_names = {
        "PRPROJ": "پریمیر",
        "DRP": "داوینچی",
        "AEP": "افتر افکت",
        "FCPXML": "فاینال کات",
        "XML": "تایم‌لاین XML",
        "EDL": "فایل EDL",
        "PSD": "فتوشاپ",
        "SESX": "آدیشن",
        "CPR": "کیوبیس"
    }
    return nle_names.get(ext, f"پروژه {ext}")


class ArchiveConfirmDialog(StudioBaseDialog):
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setFixedWidth(450)
        self.init_ui()

    def init_ui(self):
        project = ProjectController.get_project_by_id(self.project_id)
        fin = ProjectController.get_project_financial_summary(project)

        self.build_header("انتقال پرونده به آرشیو", "مختومه‌سازی و بایگانی پروژه نهایی", icon_name="archive", icon_color="#10B981")

        desc_card = QFrame()
        desc_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;")
        card_lay = QVBoxLayout(desc_card)
        card_lay.setContentsMargins(14, 12, 14, 12)
        card_lay.setSpacing(6)

        lbl_proj = QLabel(f"پروژه: <b style='color:#F8FAFC;'>{project.couple_names}</b>")
        lbl_proj.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8;")
        card_lay.addWidget(lbl_proj)

        lbl_status = QLabel("وضعیت تدوین: <b style='color:#10B981;'>کلیپ‌ها تکمیل و تحویل داده شده ✓</b>")
        lbl_status.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8;")
        card_lay.addWidget(lbl_status)

        lbl_fin = QLabel(f"وضعیت حساب: <b style='color:{fin['status_color']};'>{fin['status_label']}</b>")
        lbl_fin.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8;")
        card_lay.addWidget(lbl_fin)
        self.container_layout.addWidget(desc_card)

        note = QLabel("توجه: پرونده به بخش آرشیو منتقل می‌شود اما پیگیری مطالبات مالی و ثبت اصلاحیه همچنان فعال خواهد بود.")
        note.setWordWrap(True)
        note.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B;")
        self.container_layout.addWidget(note)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_confirm = QPushButton("تأیید و انتقال به آرشیو")
        btn_confirm.setFixedHeight(36)
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #10B981;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #059669; }
        """)
        btn_confirm.clicked.connect(self._confirm)
        btn_box.addWidget(btn_confirm, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(36)
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
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _confirm(self):
        ProjectController.archive_project(self.project_id)
        self.accept()


class ProjectCard(BaseProjectCard):
    def __init__(self, project_data: dict, parent=None):
        project_id = project_data.get("id", 0)
        project_number = project_data.get("project_number", 1)
        
        super().__init__(
            project_id=project_id,
            project_number=project_number,
            parent=parent,
            accent_color="#818CF8",
            card_type="project"
        )
        self.project = project_data
        self.is_overdue = False
        self.setFixedHeight(236)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.init_card_content()

    def _apply_base_styles(self):
        self._apply_card_theme()

    def _apply_card_theme(self):
        if self.is_overdue:
            self.setStyleSheet("""
                QFrame#BaseCardFrame {
                    background-color: #14111E;
                    border: 1.5px solid rgba(239, 68, 68, 0.40);
                    border-radius: 12px;
                }
                QFrame#BaseCardFrame:hover {
                    border-color: #EF4444;
                    background-color: #181324;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#BaseCardFrame {
                    background-color: #0E1322;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 12px;
                }
                QFrame#BaseCardFrame:hover {
                    background-color: #12182B;
                    border: 1px solid rgba(99, 102, 241, 0.45);
                }
            """)

    def init_card_content(self):
        active_rev = self.project.get("active_revision_title")
        prog_val = self.project.get("progress_pct", 0)
        c_cnt = self.project.get("completed_clips", 0)
        t_cnt = self.project.get("total_clips", 0)

        self.is_overdue = False
        deadline_dt = self.project.get("deadline")
        if deadline_dt:
            now_dt = datetime.utcnow()
            if isinstance(deadline_dt, datetime) and (deadline_dt.date() - now_dt.date()).days < 0 and prog_val < 100:
                self.is_overdue = True

        self._apply_card_theme()

        # وضعیت و بج کپسولی
        if self.is_overdue:
            status_text = "ددلاین گذشته ⚠️"
            status_type = StatusType.DANGER
            status_symbol = "!"
        elif active_rev:
            prog_val = self.project.get("rev_progress_pct", 0)
            status_text = f"اصلاحیه: {to_persian_numbers(prog_val)}٪"
            status_type = StatusType.WARNING
            status_symbol = "●"
        else:
            status_info = self.project.get("status_info", {})
            status_key = status_info.get("key", "")
            if status_key == "under_review":
                status_text = "تحویل شد / منتظر بازبینی"
                status_type = StatusType.PENDING
                status_symbol = "⏳"
            elif prog_val >= 100 or (t_cnt > 0 and c_cnt == t_cnt):
                status_text = "آماده تحویل ✓"
                status_type = StatusType.COMPLETED
                status_symbol = "✓"
            elif c_cnt == 0:
                status_text = "در انتظار شروع"
                status_type = StatusType.NEUTRAL
                status_symbol = "○"
            else:
                status_text = f"پیشرفت: {to_persian_numbers(prog_val)}٪"
                status_type = StatusType.ACTIVE
                status_symbol = "●"

        self.status_badge = StatusPillBadge(label=status_text, status_type=status_type, custom_symbol=status_symbol)
        self.header_tags_layout.addWidget(self.status_badge)

        # بج وضعیت مالی
        rem_amount = self.project.get("remaining_amount", 0)
        is_settled = (rem_amount == 0) and (self.project.get("total_fee", 0) > 0)
        
        if is_settled:
            fin_label = "تسویه کامل ✓"
            fin_bg = "rgba(16, 185, 129, 0.16)"
            fin_color = "#34D399"
            fin_border = "rgba(16, 185, 129, 0.35)"
        else:
            fin_label = f"مانده: {format_toman(rem_amount)}"
            fin_bg = "rgba(251, 146, 60, 0.16)"
            fin_color = "#FB923C"
            fin_border = "rgba(251, 146, 60, 0.40)"
        
        badge_fin = QLabel(fin_label)
        badge_fin.setFixedHeight(24)
        badge_fin.setStyleSheet(f"""
            QLabel {{
                font-family: 'Vazirmatn';
                background-color: {fin_bg};
                color: {fin_color};
                border: 1px solid {fin_border};
                border-radius: 6px;
                padding: 0 10px;
                font-size: 11px;
                font-weight: 800;
            }}
        """)
        self.header_tags_layout.addWidget(badge_fin)
        self.header_tags_layout.addStretch()

        btn_more = QPushButton("⋮")
        btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_more.setFixedSize(24, 24)
        btn_more.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8F909D;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #F8FAFC;
                background-color: rgba(255, 255, 255, 0.08);
                border-radius: 4px;
            }
        """)
        btn_more.clicked.connect(lambda: self._show_context_menu(btn_more))
        self.header_layout.addWidget(btn_more)

        # عنوان و استودیو
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 2, 0, 2)
        
        couple_name = self.project.get("couple_names") or self.project.get("title", "پروژه")
        lbl_title = QLabel(couple_name)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14.5px; font-weight: 900; color: #F8FAFC; border: none; background: transparent;")
        title_box.addWidget(lbl_title)

        raw_client = self.project.get("client_name") or "بدون استودیو"
        client_display = clean_studio_display_name(raw_client)
        lbl_client = QLabel(f"استودیو: <span style='color:#38BDF8;'>{client_display}</span>")
        lbl_client.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; font-weight: 600; border: none; background: transparent;")
        title_box.addWidget(lbl_client)

        self.card_layout.addLayout(title_box)

        # نوار داینامیک کلیپ‌ها
        clips_data = self.project.get("clips_list", [])
        self.clip_bar = DynamicClipOverviewBar(clips_data=clips_data, parent=self)
        self.card_layout.addWidget(self.clip_bar)

        # باکس اطلاعات مالی و تاریخ
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #0A0E18;
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 7px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 5, 10, 5)
        info_layout.setSpacing(10)

        fee_str = format_toman(self.project.get("total_fee", 0))
        event_str = gregorian_to_jalali(self.project.get("event_date")) or "-"
        dead_str = gregorian_to_jalali(self.project.get("deadline")) or "-"

        lbl_fee = QLabel(f"قرارداد: <b style='color:#F8FAFC;'>{fee_str}</b>")
        lbl_fee.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
        info_layout.addWidget(lbl_fee)

        info_layout.addStretch()

        lbl_event = QLabel(f"مراسم: <b style='color:#818CF8;'>{event_str}</b>")
        lbl_event.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
        info_layout.addWidget(lbl_event)

        dead_color = "#EF4444" if self.is_overdue else "#FBBF24"
        lbl_dead = QLabel(f"تحویل: <b style='color:{dead_color};'>{dead_str}</b>")
        lbl_dead.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
        info_layout.addWidget(lbl_dead)

        self.card_layout.addWidget(info_frame)

        # نوار ابزار دکمه‌های پایین
        foot_row = QHBoxLayout()
        foot_row.setContentsMargins(0, 2, 0, 0)
        foot_row.setSpacing(6)

        has_path = bool(self.project.get("primary_path") and Path(self.project.get("primary_path")).exists())
        drive_border = "#10B981" if has_path else "#EF4444"

        btn_folder = QPushButton("پوشه راش‌ها")
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor if has_path else Qt.CursorShape.ForbiddenCursor)
        btn_folder.setStyleSheet(f"""
            QPushButton {{
                font-family: 'Vazirmatn';
                background-color: #141B2D;
                color: #F8FAFC;
                border: 1px solid {drive_border}40;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {drive_border};
                background-color: #1A243D;
            }}
        """)
        btn_folder.clicked.connect(self._open_folder)
        foot_row.addWidget(btn_folder)

        # دکمه اجرای NLE
        nle_path = self.project.get("nle_project_path", "")
        persian_nle = get_persian_nle_name(nle_path)
        has_nle_file = bool(nle_path and Path(nle_path).exists())

        btn_nle = QPushButton(persian_nle)
        btn_nle.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nle.setToolTip(f"اجرای پروژه در {persian_nle}\n{nle_path}" if has_nle_file else "فایل پروژه تدوین متصل نشده است")
        btn_nle.setStyleSheet(f"""
            QPushButton {{
                font-family: 'Vazirmatn';
                background-color: #141B2D;
                color: {'#C7D2FE' if has_nle_file else '#64748B'};
                border: 1px solid {'rgba(99, 102, 241, 0.4)' if has_nle_file else 'rgba(255, 255, 255, 0.08)'};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                border-color: #818CF8;
                background-color: #1D253E;
                color: #FFFFFF;
            }}
        """)
        btn_nle.clicked.connect(self._launch_nle_project)
        foot_row.addWidget(btn_nle)

        btn_msg = QPushButton("ارسال پیام")
        btn_msg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_msg.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(56, 189, 248, 0.12);
                color: #38BDF8;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0284C7;
                color: #FFFFFF;
            }
        """)
        btn_msg.clicked.connect(lambda: self._open_fast_messenger_popup(btn_msg))
        foot_row.addWidget(btn_msg)

        btn_add_rev = QPushButton("ثبت اصلاحیه")
        btn_add_rev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_rev.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(249, 115, 22, 0.12);
                color: #FB923C;
                border: 1px solid rgba(249, 115, 22, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #EA580C;
                color: #FFFFFF;
            }
        """)
        btn_add_rev.clicked.connect(self._open_new_revision)
        foot_row.addWidget(btn_add_rev)

        btn_pay = QPushButton("ثبت واریزی")
        btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pay.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(16, 185, 129, 0.12);
                color: #34D399;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #10B981;
                color: #FFFFFF;
            }
        """)
        btn_pay.clicked.connect(self._open_payment)
        foot_row.addWidget(btn_pay)

        foot_row.addStretch()

        btn_details = QPushButton("مشاهده پرونده ←")
        btn_details.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_details.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: transparent;
                color: #818CF8;
                border: none;
                font-size: 11.5px;
                font-weight: 800;
                padding: 4px 4px;
            }
            QPushButton:hover {
                color: #A5B4FC;
            }
        """)
        btn_details.clicked.connect(self._open_details)
        foot_row.addWidget(btn_details)

        self.card_layout.addLayout(foot_row)

    def _show_context_menu(self, parent_btn: QPushButton):
        menu = StudioMenu(self)

        act_nle = menu.addAction(IconProvider.get_icon("nle_launch", "#818CF8", size=14), "اجرای فایل پروژه")
        act_edit = menu.addAction(IconProvider.get_icon("edit", "#818CF8", size=14), "ویرایش مشخصات پروژه")
        act_share = menu.addAction(IconProvider.get_icon("message", "#38BDF8", size=14), "ارسال فاکتور و وضعیت به استودیو")
        act_archive = menu.addAction(IconProvider.get_icon("archive", "#10B981", size=14), "انتقال به آرشیو")
        
        menu.addSeparator()
        act_delete = menu.addAction(IconProvider.get_icon("trash", "#EF4444", size=14), "حذف کامل پروژه")

        action = menu.show_beside_button(parent_btn)
        if action == act_nle:
            self._launch_nle_project()
        elif action == act_edit:
            self._open_edit_dialog()
        elif action == act_share:
            self._open_share_dialog()
        elif action == act_archive:
            self._open_archive_confirm()
        elif action == act_delete:
            self._delete_project()

    def _launch_nle_project(self):
        nle_path = self.project.get("nle_project_path", "")
        success, message = NleLauncherHelper.launch_project(nle_path)
        if success:
            global_signals.show_toast.emit(message, "success")
        else:
            global_signals.show_toast.emit(message, "error")

    def _open_fast_messenger_popup(self, anchor_btn: QWidget):
        popup = QuickMessengerMiniPopup(self.project, self.window())
        popup.show_beside_widget(anchor_btn)

    def _open_edit_dialog(self):
        diag = EditProjectDialog(self.project_id, self.window())
        diag.exec()

    def _open_share_dialog(self):
        diag = StudioShareDialog(self.project_id, self.window())
        diag.exec()

    def _delete_project(self):
        couple = self.project.get('couple_names') or 'پروژه'
        if StudioConfirmDialog.ask(
            self.window(),
            title="حذف کامل پروژه",
            message=f"آیا از حذف کامل پرونده «{couple}» اطمینان دارید؟",
            details="هشدار: تمام کلیپ‌ها، دوره‌های اصلاحیه، لاگ‌ها و تراکنش‌های مالی متصل به این پروژه برای همیشه پاک خواهند شد.",
            confirm_text="حذف دائمی",
            is_danger=True,
            icon_name="trash"
        ):
            ProjectController.delete_project(self.project_id)

    def _open_new_revision(self):
        diag = NewRevisionDialog(self.project_id, self.window())
        diag.exec()

    def _open_archive_confirm(self):
        diag = ArchiveConfirmDialog(self.project_id, self.window())
        diag.exec()

    def _open_details(self):
        win = self.window()
        QTimer.singleShot(0, lambda: ProjectDetailsDialog(self.project_id, win).exec())

    def _open_payment(self):
        win = self.window()
        QTimer.singleShot(0, lambda: NewTransactionDialog(self.project_id, parent=win).exec())

    def _open_folder(self):
        path_str = self.project.get("primary_path")
        if not path_str or not Path(path_str).exists():
            global_signals.show_toast.emit("مسیر پوشه مشخص نشده یا هارد متصل نیست", "error")
            return
        open_path_in_os(path_str)