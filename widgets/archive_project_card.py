# ==================================================
# FILE: widgets/archive_project_card.py
# ==================================================
from pathlib import Path
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer

from core.persian_utils import format_toman, gregorian_to_jalali, to_persian_numbers
from core.project_controller import ProjectController
from widgets.base_card import BaseProjectCard
from widgets.status_badge import StatusPillBadge, StatusType
from widgets.project_details_dialog import ProjectDetailsDialog
from widgets.project_passport_dialog import ProjectPassportDialog
from widgets.new_transaction_dialog import NewTransactionDialog
from widgets.project_timeline import NewRevisionDialog
from widgets.project_media_explorer_dialog import ProjectMediaExplorerDialog
from widgets.studio_dialog_base import StudioConfirmDialog
from core.icon_provider import IconProvider
from core.signals import global_signals


class ArchiveProjectCard(BaseProjectCard):
    """
    کارت فشرده و متراکم آرشیو با نمایش کامل عناوین فارسی
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
        
        # افزایش ارتفاع به ۱۸۸ پیکسل جهت جلوگیری از برش خطوط
        self.setFixedHeight(188)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_layout.setContentsMargins(12, 10, 12, 10)
        self.card_layout.setSpacing(6)
        
        self.init_archive_content()

    def init_archive_content(self):
        # ۱. هدر: بج‌ها + منوی گزینه‌ها
        self.status_badge = StatusPillBadge(
            label="تکمیل شده",
            status_type=StatusType.COMPLETED,
            custom_symbol="✓"
        )
        self.header_tags_layout.addWidget(self.status_badge)

        rev_count = self.project.get("revisions_count", 0)
        if rev_count > 0:
            rev_badge = QLabel(f"{to_persian_numbers(rev_count)} دور")
            rev_badge.setFixedHeight(22)
            rev_badge.setStyleSheet("""
                font-family: 'Vazirmatn';
                background-color: rgba(99, 102, 241, 0.10);
                color: #818CF8;
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 5px;
                padding: 0 5px;
                font-size: 10px;
                font-weight: 600;
            """)
            self.header_tags_layout.addWidget(rev_badge)

        rem_amount = self.project.get("remaining_amount", 0)
        is_settled = self.project.get("is_settled", False)
        fin_text = "✓ تسویه" if is_settled else f"مانده: {format_toman(rem_amount)}"
        fin_color = "#10B981" if is_settled else "#F59E0B"
        
        settled_badge = QLabel(fin_text)
        settled_badge.setFixedHeight(22)
        settled_badge.setStyleSheet(f"""
            font-family: 'Vazirmatn';
            background-color: {fin_color}18;
            color: {fin_color};
            border: 1px solid {fin_color}33;
            border-radius: 5px;
            padding: 0 6px;
            font-size: 10px;
            font-weight: 700;
        """)
        self.header_tags_layout.addWidget(settled_badge)
        self.header_tags_layout.addStretch()

        btn_more = QPushButton("⋮")
        btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_more.setFixedSize(20, 20)
        btn_more.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8F909D;
                border: none;
                font-size: 14px;
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

        # ۲. عنوان و نام استودیو
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 3, 0, 2)

        couple_name = self.project.get("couple_names") or self.project.get("title", "پروژه بدون نام")
        lbl_title = QLabel(couple_name)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #F8FAFC; border: none; background: transparent; padding: 1px 0;")
        title_box.addWidget(lbl_title)

        client_name = self.project.get("client_name") or "بدون استودیو"
        lbl_client = QLabel(f"استودیو: {client_name}")
        lbl_client.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #94A3B8; font-weight: 500; border: none; background: transparent;")
        title_box.addWidget(lbl_client)

        self.card_layout.addLayout(title_box)

        # ۳. کادر مشخصات مالی و تاریخ‌ها
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #0F1420;
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 6px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 4, 8, 4)
        info_layout.setSpacing(6)

        fee_str = format_toman(self.project.get("total_fee", 0))
        comp_str = gregorian_to_jalali(self.project.get("completed_at")) or "-"

        lbl_fee = QLabel(f"کل: <b>{fee_str}</b>")
        lbl_fee.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #94A3B8;")
        info_layout.addWidget(lbl_fee)

        info_layout.addStretch()

        lbl_comp = QLabel(f"تحویل: <b style='color:#10B981;'>{comp_str}</b>")
        lbl_comp.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10px; color: #94A3B8;")
        info_layout.addWidget(lbl_comp)

        self.card_layout.addWidget(info_frame)

        # ۴. نوار دکمه‌های عملیاتی
        foot_row = QHBoxLayout()
        foot_row.setContentsMargins(0, 2, 0, 0)
        foot_row.setSpacing(4)

        has_path = bool(self.project.get("primary_path") and Path(self.project.get("primary_path")).exists())
        drive_color = "#10B981" if has_path else "#EF4444"

        btn_folder = QPushButton("پوشه")
        btn_folder.setIcon(IconProvider.get_icon("folder", drive_color, size=11))
        btn_folder.setIconSize(QSize(11, 11))
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor if has_path else Qt.CursorShape.ForbiddenCursor)
        btn_folder.setStyleSheet(f"""
            QPushButton {{
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #F8FAFC;
                border: 1px solid {drive_color}33;
                border-radius: 5px;
                padding: 3px 6px;
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {drive_color};
                background-color: #1E283D;
            }}
        """)
        btn_folder.clicked.connect(self._open_folder)
        foot_row.addWidget(btn_folder)

        btn_passport = QPushButton("شناسنامه")
        btn_passport.setIcon(IconProvider.get_icon("check", "#10B981", size=11))
        btn_passport.setIconSize(QSize(11, 11))
        btn_passport.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_passport.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(16, 185, 129, 0.10);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 5px;
                padding: 3px 6px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #10B981;
                color: #FFFFFF;
            }
        """)
        btn_passport.clicked.connect(self._open_passport)
        foot_row.addWidget(btn_passport)

        btn_new_rev = QPushButton("+ اصلاحیه")
        btn_new_rev.setIcon(IconProvider.get_icon("revision", "#F59E0B", size=11))
        btn_new_rev.setIconSize(QSize(11, 11))
        btn_new_rev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_rev.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(245, 158, 11, 0.10);
                color: #F59E0B;
                border: 1px solid rgba(245, 158, 11, 0.25);
                border-radius: 5px;
                padding: 3px 6px;
                font-size: 10px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F59E0B;
                color: #000000;
            }
        """)
        btn_new_rev.clicked.connect(self._open_new_revision)
        foot_row.addWidget(btn_new_rev)

        if rem_amount > 0:
            btn_pay = QPushButton("واریزی")
            btn_pay.setIcon(IconProvider.get_icon("dollar", "#10B981", size=11))
            btn_pay.setIconSize(QSize(11, 11))
            btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pay.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: #161F30;
                    color: #10B981;
                    border: 1px solid rgba(16, 185, 129, 0.25);
                    border-radius: 5px;
                    padding: 3px 6px;
                    font-size: 10px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #10B981;
                    color: #FFFFFF;
                }
            """)
            btn_pay.clicked.connect(self._open_payment)
            foot_row.addWidget(btn_pay)

        foot_row.addStretch()

        btn_view = QPushButton("پرونده ←")
        btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_view.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: transparent;
                color: #6366F1;
                border: none;
                font-size: 10.5px;
                font-weight: 700;
                padding: 2px 2px;
            }
            QPushButton:hover { color: #818CF8; }
        """)
        btn_view.clicked.connect(self._open_details)
        foot_row.addWidget(btn_view)

        self.card_layout.addLayout(foot_row)
        self.clicked.connect(lambda _: self._open_details())

    def _show_context_menu(self, parent_btn: QPushButton):
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        act_unarchive = menu.addAction("بازگردانی به پروژه‌های فعال 🔄")
        act_delete = menu.addAction("حذف کامل پروژه 🗑️")

        action = menu.exec(parent_btn.mapToGlobal(parent_btn.rect().bottomLeft()))
        if action == act_unarchive:
            self._unarchive_project()
        elif action == act_delete:
            self._delete_project()

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

    def _open_new_revision(self):
        diag = NewRevisionDialog(self.project_id, self.window())
        diag.exec()

    def _open_payment(self):
        proj_id = self.project_id
        win = self.window()
        QTimer.singleShot(0, lambda: NewTransactionDialog(proj_id, win).exec())

    def _open_passport(self):
        proj_id = self.project_id
        win = self.window()
        QTimer.singleShot(0, lambda: ProjectPassportDialog(proj_id, win).exec())

    def _open_details(self):
        proj_id = self.project_id
        win = self.window()
        QTimer.singleShot(0, lambda: ProjectDetailsDialog(proj_id, win).exec())

    def _open_folder(self):
        path_str = self.project.get("primary_path")
        if not path_str or not Path(path_str).exists():
            global_signals.show_toast.emit("مسیر پوشه مشخص نشده یا هارد متصل نیست", "error")
            return
        
        couple_name = self.project.get("couple_names") or self.project.get("title", "پروژه")
        win = self.window()
        diag = ProjectMediaExplorerDialog(folder_path=path_str, project_title=couple_name, parent=win)
        diag.exec()