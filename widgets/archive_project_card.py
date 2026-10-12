# ==================================================
# FILE: widgets/archive_project_card.py
# ==================================================
from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer

from config import open_path_in_os
from core.persian_utils import format_toman, gregorian_to_jalali, to_persian_numbers, clean_studio_display_name
from core.project_controller import ProjectController
from widgets.base_card import BaseProjectCard
from widgets.status_badge import StatusPillBadge, StatusType
from widgets.project_details_dialog import ProjectDetailsDialog
from widgets.project_passport_dialog import ProjectPassportDialog
from widgets.new_transaction_dialog import NewTransactionDialog
from widgets.project_timeline import NewRevisionDialog
from widgets.studio_dialog_base import StudioConfirmDialog
from widgets.studio_menu import StudioMenu
from core.icon_provider import IconProvider


class ArchiveProjectCard(BaseProjectCard):
    """
    کارت آرشیو بهینه‌شده با دسترسی مستقیم به ثبت اصلاحیه،
    کپسول‌های مینی متنی خالص، باز کردن مستقیم پوشه در سیستم‌عامل و منوی زمینه‌ای لوکس
    """
    def __init__(self, project_data: dict, parent=None):
        project_id = project_data.get("id", 0)
        project_number = project_data.get("project_number", 1)
        
        super().__init__(
            project_id=project_id,
            project_number=project_number,
            parent=parent,
            accent_color="#10B981",
            card_type="archive"
        )
        self.project = project_data
        self.setFixedHeight(186)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.card_layout.setContentsMargins(14, 12, 14, 12)
        self.card_layout.setSpacing(6)
        self.init_archive_content()

    def init_archive_content(self):
        rem_amount = self.project.get("remaining_amount", 0)
        is_settled = self.project.get("is_settled", False)

        border_col = "rgba(16, 185, 129, 0.35)" if is_settled else "rgba(251, 146, 60, 0.40)"
        self.setStyleSheet(f"""
            QFrame#BaseCardFrame {{
                background-color: #0E1322;
                border: 1px solid {border_col};
                border-radius: 10px;
            }}
            QFrame#BaseCardFrame:hover {{
                background-color: #131A2D;
                border-color: #38BDF8;
            }}
        """)

        # ۱. بج کپسولی وضعیت مختومه
        self.status_badge = StatusPillBadge(
            label="مختومه",
            status_type=StatusType.COMPLETED,
            custom_symbol=""
        )
        self.header_tags_layout.addWidget(self.status_badge)

        # ۲. بج وضعیت مالی
        if is_settled or rem_amount <= 0:
            fin_text = "تسویه کامل"
            fin_bg = "rgba(16, 185, 129, 0.16)"
            fin_color = "#34D399"
            fin_border = "rgba(16, 185, 129, 0.35)"
        else:
            fin_text = f"مانده: {format_toman(rem_amount)}"
            fin_bg = "rgba(251, 146, 60, 0.16)"
            fin_color = "#FB923C"
            fin_border = "rgba(251, 146, 60, 0.40)"

        settled_badge = QLabel(fin_text)
        settled_badge.setFixedHeight(22)
        settled_badge.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        settled_badge.setStyleSheet(f"""
            QLabel {{
                font-family: 'Vazirmatn';
                background-color: {fin_bg};
                color: {fin_color};
                border: 1px solid {fin_border};
                border-radius: 5px;
                padding: 0 6px;
                font-size: 9.5px;
                font-weight: 700;
            }}
        """)
        self.header_tags_layout.addWidget(settled_badge)
        self.header_tags_layout.addStretch()

        # منوی ۳ نقطه
        btn_more = QPushButton("⋮")
        btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_more.setFixedSize(22, 22)
        btn_more.setStyleSheet("""
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
        btn_more.clicked.connect(lambda: self._show_context_menu(btn_more))
        self.header_layout.addWidget(btn_more)

        # ۳. عنوان و استودیو
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 2, 0, 2)

        couple_name = self.project.get("couple_names") or self.project.get("title", "پروژه")
        lbl_title = QLabel(couple_name)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14px; font-weight: 900; color: #F8FAFC; border: none; background: transparent;")
        title_box.addWidget(lbl_title)

        raw_client = self.project.get("client_name") or "بدون استودیو"
        client_display = clean_studio_display_name(raw_client)
        
        rev_count = self.project.get("revisions_count", 0)
        rev_info = f"   •   {to_persian_numbers(rev_count)} دور اصلاحیه" if rev_count > 0 else ""
        
        lbl_client = QLabel(f"استودیو: <span style='color:#38BDF8;'>{client_display}</span>{rev_info}")
        lbl_client.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; font-weight: 500; border: none; background: transparent;")
        title_box.addWidget(lbl_client)

        self.card_layout.addLayout(title_box)

        # ۴. کادر خلاصه مالی و تاریخ تحویل
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #0A0E18;
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 6, 10, 6)
        info_layout.setSpacing(8)

        fee_str = format_toman(self.project.get("total_fee", 0))
        comp_str = gregorian_to_jalali(self.project.get("completed_at")) or "-"

        lbl_fee = QLabel(f"کل قرارداد: <b style='color:#F8FAFC;'>{fee_str}</b>")
        lbl_fee.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
        info_layout.addWidget(lbl_fee)

        info_layout.addStretch()

        lbl_comp = QLabel(f"تحویل: <b style='color:#10B981;'>{comp_str}</b>")
        lbl_comp.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #94A3B8;")
        info_layout.addWidget(lbl_comp)

        self.card_layout.addWidget(info_frame)

        # ۵. نوار ابزار پایین (کپسول‌های مینی، متن خالص، بدون آیکون)
        foot_row = QHBoxLayout()
        foot_row.setContentsMargins(0, 2, 0, 0)
        foot_row.setSpacing(6)

        # دکمه شناسنامه
        btn_passport = QPushButton("شناسنامه")
        btn_passport.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_passport.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(16, 185, 129, 0.14);
                color: #34D399;
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 5px;
                padding: 3px 9px;
                font-size: 10.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #10B981;
                color: #FFFFFF;
            }
        """)
        btn_passport.clicked.connect(self._open_passport)
        foot_row.addWidget(btn_passport)

        # دکمه پوشه راش‌ها (باز شدن مستقیم در ویندوز/سیستم‌عامل)
        has_path = bool(self.project.get("primary_path") and Path(self.project.get("primary_path")).exists())
        btn_folder = QPushButton("پوشه راش‌ها")
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor if has_path else Qt.CursorShape.ForbiddenCursor)
        btn_folder.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #141B2D;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 5px;
                padding: 3px 9px;
                font-size: 10.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #F8FAFC;
                border-color: #6366F1;
            }
        """)
        btn_folder.clicked.connect(self._open_folder)
        foot_row.addWidget(btn_folder)

        # دکمه ثبت اصلاحیه (بنفش ارغوانی نئونی)
        btn_add_rev = QPushButton("ثبت اصلاحیه")
        btn_add_rev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_rev.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(192, 132, 252, 0.14);
                color: #C084FC;
                border: 1px solid rgba(192, 132, 252, 0.35);
                border-radius: 5px;
                padding: 3px 9px;
                font-size: 10.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #9333EA;
                border-color: #A855F7;
                color: #FFFFFF;
            }
        """)
        btn_add_rev.clicked.connect(self._open_new_revision)
        foot_row.addWidget(btn_add_rev)

        # دکمه ثبت تسویه (در صورت وجود مانده حساب)
        if rem_amount > 0:
            btn_pay = QPushButton("ثبت تسویه")
            btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pay.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: rgba(251, 146, 60, 0.14);
                    color: #FB923C;
                    border: 1px solid rgba(251, 146, 60, 0.35);
                    border-radius: 5px;
                    padding: 3px 9px;
                    font-size: 10.5px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #EA580C;
                    border-color: #EA580C;
                    color: #FFFFFF;
                }
            """)
            btn_pay.clicked.connect(self._open_payment)
            foot_row.addWidget(btn_pay)

        foot_row.addStretch()

        self.card_layout.addLayout(foot_row)
        
        # کلیک روی کل سطح کارت، دیالوگ جزئیات پرونده را باز می‌کند
        self.clicked.connect(lambda _: self._open_details())

    def _show_context_menu(self, parent_btn: QPushButton):
        menu = StudioMenu(self)

        act_rev = menu.addAction(IconProvider.get_icon("revision", "#C084FC", size=14), "ثبت دور اصلاحیه جدید")
        act_unarchive = menu.addAction(IconProvider.get_icon("refresh", "#10B981", size=14), "بازگردانی به پروژه‌های فعال")
        
        menu.addSeparator()
        act_delete = menu.addAction(IconProvider.get_icon("trash", "#EF4444", size=14), "حذف کامل پروژه")

        action = menu.show_beside_button(parent_btn)
        if action == act_rev:
            self._open_new_revision()
        elif action == act_unarchive:
            self._unarchive_project()
        elif action == act_delete:
            self._delete_project()

    def _open_new_revision(self):
        win = self.window()
        QTimer.singleShot(0, lambda: NewRevisionDialog(self.project_id, win).exec())

    def _unarchive_project(self):
        couple = self.project.get('couple_names') or 'پروژه'
        if StudioConfirmDialog.ask(
            self.window(),
            title="تأیید خروج از آرشیو",
            message=f"آیا می‌خواهید پرونده «{couple}» مجدداً به بخش پروژه‌های فعال بازگردد؟",
            details="پروژه به صفحه اصلی و لیست در حال انجام اضافه خواهد شد.",
            confirm_text="بازگردانی به فعال",
            is_danger=False,
            icon_name="revision"
        ):
            ProjectController.unarchive_project(self.project_id)

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

    def _open_passport(self):
        proj_id = self.project_id
        win = self.window()
        QTimer.singleShot(0, lambda: ProjectPassportDialog(proj_id, win).exec())

    def _open_payment(self):
        proj_id = self.project_id
        win = self.window()
        QTimer.singleShot(0, lambda: NewTransactionDialog(proj_id, win).exec())

    def _open_details(self):
        proj_id = self.project_id
        win = self.window()
        QTimer.singleShot(0, lambda: ProjectDetailsDialog(proj_id, win).exec())

    def _open_folder(self):
        path_str = self.project.get("primary_path")
        if not path_str or not Path(path_str).exists():
            return
        open_path_in_os(path_str)