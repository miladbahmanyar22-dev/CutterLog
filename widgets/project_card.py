# ==================================================
# FILE: widgets/project_card.py
# ==================================================
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QMenu, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer

from core.persian_utils import format_toman, gregorian_to_jalali, to_persian_numbers
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
from widgets.project_media_explorer_dialog import ProjectMediaExplorerDialog
from widgets.studio_share_dialog import StudioShareDialog
from widgets.quick_messenger_popup import QuickMessengerMiniPopup
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog
from core.icon_provider import IconProvider
from core.signals import global_signals


def progress_pct_to_words(pct: int, completed_clips: int, total_clips: int) -> str:
    if total_clips == 0:
        return "بدون کلیپ"
    if completed_clips == 0:
        return "شروع نشده"
    if pct >= 100 or completed_clips == total_clips:
        return "تکمیل شده"

    ones = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"]
    teens = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده", "شانزده", "هفده", "هجده", "نوزده"]
    tens = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]

    def _num_to_text(n: int) -> str:
        if n <= 0:
            return "صفر"
        if n < 10:
            return ones[n]
        if n < 20:
            return teens[n - 10]
        if n < 100:
            t = n // 10
            o = n % 10
            if o > 0:
                return f"{tens[t]} و {ones[o]}"
            return tens[t]
        return "صد"

    return f"{_num_to_text(pct)} درصد انجام شده"


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

        btn_confirm = QPushButton("✓ تأیید و انتقال به آرشیو")
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
        self.setFixedHeight(230)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.init_card_content()

    def _apply_card_theme(self):
        """اعمال تم رنگی اختصاصی در صورت تأخیر در تحویل یا تم استاندارد"""
        if self.is_overdue:
            self.setStyleSheet("""
                QFrame#BaseCardFrame {
                    background-color: rgba(239, 68, 68, 0.06);
                    border: 1.5px solid rgba(239, 68, 68, 0.38);
                    border-radius: 12px;
                }
                QFrame#BaseCardFrame:hover {
                    background-color: rgba(239, 68, 68, 0.10);
                    border: 1.5px solid #EF4444;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame#BaseCardFrame {
                    background-color: #121826;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 12px;
                }
                QFrame#BaseCardFrame:hover {
                    background-color: #161F30;
                    border: 1px solid rgba(99, 102, 241, 0.40);
                }
            """)

    def init_card_content(self):
        active_rev = self.project.get("active_revision_title")
        prog_val = self.project.get("progress_pct", 0)
        c_cnt = self.project.get("completed_clips", 0)
        t_cnt = self.project.get("total_clips", 0)

        # ۱. ارزیابی هوشمند عبور از ددلاین (Deadline Overdue)
        self.is_overdue = False
        if self.project.get("deadline"):
            now_dt = datetime.utcnow()
            d_dt = self.project.get("deadline")
            if isinstance(d_dt, datetime) and (d_dt.date() - now_dt.date()).days < 0 and prog_val < 100:
                self.is_overdue = True

        self._apply_card_theme()

        if self.is_overdue:
            status_text = "ددلاین گذشته"
            status_type = StatusType.DANGER
            status_symbol = "!"
        elif active_rev:
            prog_val = self.project.get("rev_progress_pct", 0)
            c_cnt = self.project.get("rev_completed_tasks", 0)
            t_cnt = self.project.get("rev_total_tasks", 0)
            status_text = f"اصلاحیه: {progress_pct_to_words(prog_val, c_cnt, t_cnt)}"
            status_type = StatusType.WARNING
            status_symbol = "●"
        else:
            status_info = self.project.get("status_info", {})
            status_key = status_info.get("key", "")
            
            if status_key == "under_review":
                status_text = status_info.get("label", "تحویل شد / منتظر بازبینی")
                status_type = StatusType.PENDING
                status_symbol = "⏳"
            else:
                status_text = progress_pct_to_words(prog_val, c_cnt, t_cnt)
                if prog_val >= 100 or (t_cnt > 0 and c_cnt == t_cnt):
                    status_type = StatusType.COMPLETED
                    status_symbol = "✓"
                elif c_cnt == 0:
                    status_type = StatusType.NEUTRAL
                    status_symbol = "○"
                else:
                    status_type = StatusType.ACTIVE
                    status_symbol = "●"

        self.status_badge = StatusPillBadge(
            label=status_text,
            status_type=status_type,
            custom_symbol=status_symbol
        )
        self.header_tags_layout.addWidget(self.status_badge)

        rem_amount = self.project.get("remaining_amount", 0)
        is_settled = (rem_amount == 0) and (self.project.get("total_fee", 0) > 0)
        fin_label = "✓ تسویه کامل" if is_settled else f"مانده: {format_toman(rem_amount)}"
        fin_color = "#10B981" if is_settled else "#F59E0B"
        
        badge_fin = QLabel(fin_label)
        badge_fin.setFixedHeight(24)
        badge_fin.setStyleSheet(f"""
            QLabel {{
                font-family: 'Vazirmatn';
                background-color: {fin_color}14;
                color: {fin_color};
                border: 1px solid {fin_color}33;
                border-radius: 6px;
                padding: 0 8px;
                font-size: 11px;
                font-weight: 600;
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
                background-color: rgba(255, 255, 255, 0.06);
                border-radius: 4px;
            }
        """)
        btn_more.clicked.connect(lambda: self._show_context_menu(btn_more))
        self.header_layout.addWidget(btn_more)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 4, 0, 2)
        
        couple_name = self.project.get("couple_names") or self.project.get("title", "پروژه بدون نام")
        lbl_title = QLabel(couple_name)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 15px; font-weight: 800; color: #F8FAFC; border: none; background: transparent; padding: 2px 0;")
        title_box.addWidget(lbl_title)

        client_name = self.project.get("client_name") or "بدون استودیو"
        lbl_client = QLabel(f"استودیو: {client_name}")
        lbl_client.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8; font-weight: 500; border: none; background: transparent;")
        title_box.addWidget(lbl_client)

        self.card_layout.addLayout(title_box)

        if active_rev:
            c_cnt = self.project.get("rev_completed_tasks", 0)
            t_cnt = self.project.get("rev_total_tasks", 0)
            lbl_text = f"تسک‌های اصلاحیه: {to_persian_numbers(c_cnt)} از {to_persian_numbers(t_cnt)}"
            p_color = "#EA580C"
        else:
            c_cnt = self.project.get("completed_clips", 0)
            t_cnt = self.project.get("total_clips", 0)
            lbl_text = f"کلیپ‌های مراسم: {to_persian_numbers(c_cnt)} از {to_persian_numbers(t_cnt)}"
            p_color = "#10B981" if prog_val == 100 else ("#EF4444" if self.is_overdue else "#6366F1")

        prog_row = QHBoxLayout()
        prog_row.setContentsMargins(0, 2, 0, 0)
        
        lbl_clips_cnt = QLabel(lbl_text)
        lbl_clips_cnt.setStyleSheet("font-family: 'Vazirmatn'; color: #8F909D; font-size: 11px; border: none; background: transparent;")
        prog_row.addWidget(lbl_clips_cnt, stretch=1)
        
        lbl_pct_val = QLabel(f"{to_persian_numbers(prog_val)}٪")
        lbl_pct_val.setStyleSheet(f"font-family: 'Vazirmatn'; color: {p_color}; font-size: 11.5px; font-weight: 800; border: none; background: transparent;")
        prog_row.addWidget(lbl_pct_val)
        self.card_layout.addLayout(prog_row)

        clips_data = self.project.get("clips_list", [])
        self.clip_bar = DynamicClipOverviewBar(clips_data=clips_data, parent=self)
        self.card_layout.addWidget(self.clip_bar)

        info_bg = "rgba(239, 68, 68, 0.08)" if self.is_overdue else "#0F1420"
        info_border = "rgba(239, 68, 68, 0.20)" if self.is_overdue else "rgba(255, 255, 255, 0.04)"
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {info_bg};
                border: 1px solid {info_border};
                border-radius: 7px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 6, 10, 6)
        info_layout.setSpacing(10)

        fee_str = format_toman(self.project.get("total_fee", 0))
        event_str = gregorian_to_jalali(self.project.get("event_date")) or "-"
        dead_str = gregorian_to_jalali(self.project.get("deadline")) or "-"

        lbl_fee = QLabel(f"کل: <b style='color:#F8FAFC;'>{fee_str}</b>")
        lbl_fee.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #8F909D;")
        info_layout.addWidget(lbl_fee)

        info_layout.addStretch()

        lbl_event = QLabel(f"مراسم: {event_str}")
        lbl_event.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #818CF8;")
        info_layout.addWidget(lbl_event)

        dead_color = "#EF4444" if self.is_overdue else "#64748B"
        lbl_dead = QLabel(f"تحویل: {dead_str}")
        lbl_dead.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 11px; color: {dead_color}; font-weight: {'700' if self.is_overdue else 'normal'};")
        info_layout.addWidget(lbl_dead)

        self.card_layout.addWidget(info_frame)

        foot_row = QHBoxLayout()
        foot_row.setContentsMargins(0, 2, 0, 0)
        foot_row.setSpacing(5)

        has_path = bool(self.project.get("primary_path") and Path(self.project.get("primary_path")).exists())
        drive_color = "#10B981" if has_path else "#EF4444"

        btn_folder = QPushButton("پوشه")
        btn_folder.setIcon(IconProvider.get_icon("folder", drive_color, size=13))
        btn_folder.setIconSize(QSize(13, 13))
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor if has_path else Qt.CursorShape.ForbiddenCursor)
        btn_folder.setStyleSheet(f"""
            QPushButton {{
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #F8FAFC;
                border: 1px solid {drive_color}33;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {drive_color};
                background-color: #1E283D;
            }}
        """)
        btn_folder.clicked.connect(self._open_folder)
        foot_row.addWidget(btn_folder)

        nle_path = self.project.get("nle_project_path", "")
        badge_info = NleLauncherHelper.get_file_badge_info(nle_path)
        b_label = badge_info["label"]
        has_nle_file = badge_info["has_file"]

        btn_nle = QPushButton(b_label)
        btn_nle.setIcon(IconProvider.get_icon("nle_launch", "#818CF8" if has_nle_file else "#64748B", size=13))
        btn_nle.setIconSize(QSize(13, 13))
        btn_nle.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_nle.setToolTip(f"اجرای مستقیم در {badge_info['name']}\n{nle_path}" if has_nle_file else "فایل پروژه متصل نشده است")
        btn_nle.setStyleSheet("""
            QPushButton {
                font-family: 'Segoe UI', 'Vazirmatn', sans-serif;
                background-color: #161F30;
                color: #F8FAFC;
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 6px;
                padding: 4px 9px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                border-color: #818CF8;
                background-color: #1E283D;
                color: #818CF8;
            }
        """)
        btn_nle.clicked.connect(self._launch_nle_project)
        foot_row.addWidget(btn_nle)

        btn_msg = QPushButton("پیام")
        btn_msg.setIcon(IconProvider.get_icon("message", "#38BDF8", size=12))
        btn_msg.setIconSize(QSize(12, 12))
        btn_msg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_msg.setToolTip("کپی پیام وضعیت و ارسال سریع در تلگرام یا واتساپ")
        btn_msg.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(56, 189, 248, 0.10);
                color: #38BDF8;
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 6px;
                padding: 4px 8px;
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

        btn_add_rev = QPushButton("+ اصلاحیه")
        btn_add_rev.setIcon(IconProvider.get_icon("revision", "#EA580C", size=12))
        btn_add_rev.setIconSize(QSize(12, 12))
        btn_add_rev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_rev.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(234, 88, 12, 0.10);
                color: #EA580C;
                border: 1px solid rgba(234, 88, 12, 0.25);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #EA580C; color: #FFFFFF; }
        """)
        btn_add_rev.clicked.connect(self._open_new_revision)
        foot_row.addWidget(btn_add_rev)

        project_obj = ProjectController.get_project_by_id(self.project_id)
        is_eligible_for_finance = FinanceController.is_project_eligible_for_finance(project_obj) if project_obj else False

        if is_eligible_for_finance:
            btn_pay = QPushButton("واریزی")
            btn_pay.setIcon(IconProvider.get_icon("dollar", "#10B981", size=12))
            btn_pay.setIconSize(QSize(12, 12))
            btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pay.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    background-color: rgba(16, 185, 129, 0.10);
                    color: #10B981;
                    border: 1px solid rgba(16, 185, 129, 0.25);
                    border-radius: 6px;
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover { background-color: #10B981; color: #FFFFFF; }
            """)
            btn_pay.clicked.connect(self._open_payment)
            foot_row.addWidget(btn_pay)

        status_info = self.project.get("status_info", {})
        status_key = status_info.get("key", "")
        if prog_val >= 100:
            if status_key == "ready_for_delivery":
                btn_deliver = QPushButton("تحویل به آتلیه 📤")
                btn_deliver.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_deliver.setStyleSheet("""
                    QPushButton {
                        font-family: 'Vazirmatn';
                        background-color: #0891B2;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        padding: 4px 10px;
                        font-size: 11px;
                        font-weight: 700;
                    }
                    QPushButton:hover { background-color: #06B6D4; }
                """)
                btn_deliver.clicked.connect(self._mark_delivered)
                foot_row.addWidget(btn_deliver)
            else:
                btn_archive = QPushButton("انتقال به آرشیو 📁")
                btn_archive.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_archive.setStyleSheet("""
                    QPushButton {
                        font-family: 'Vazirmatn';
                        background-color: #10B981;
                        color: #FFFFFF;
                        border: none;
                        border-radius: 6px;
                        padding: 4px 10px;
                        font-size: 11px;
                        font-weight: 700;
                    }
                    QPushButton:hover { background-color: #059669; }
                """)
                btn_archive.clicked.connect(self._open_archive_confirm)
                foot_row.addWidget(btn_archive)

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
                font-weight: 700;
                padding: 4px 4px;
            }
            QPushButton:hover { color: #A5B4FC; }
        """)
        btn_details.clicked.connect(self._open_details)
        foot_row.addWidget(btn_details)

        self.card_layout.addLayout(foot_row)

    def _show_context_menu(self, parent_btn: QPushButton):
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        act_nle = menu.addAction("اجرای فایل پروژه 🎬")
        act_edit = menu.addAction("ویرایش مشخصات پروژه ✏️")
        act_share = menu.addAction("ارسال فاکتور و وضعیت به استودیو 💬")
        act_archive = menu.addAction("انتقال به آرشیو 📁")
        act_delete = menu.addAction("حذف کامل پروژه 🗑️")

        action = menu.exec(parent_btn.mapToGlobal(parent_btn.rect().bottomLeft()))
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

    def _mark_delivered(self):
        ProjectController.mark_as_delivered(self.project_id)

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
        proj_id = self.project_id
        win = self.window()
        diag = ProjectDetailsDialog(proj_id, win)
        diag.exec()

    def _open_payment(self):
        proj_id = self.project_id
        win = self.window()
        diag = NewTransactionDialog(proj_id, parent=win)
        diag.exec()

    def _open_folder(self):
        path_str = self.project.get("primary_path")
        if not path_str or not Path(path_str).exists():
            global_signals.show_toast.emit("مسیر پوشه مشخص نشده یا هارد متصل نیست", "error")
            return
        
        couple_name = self.project.get("couple_names") or self.project.get("title", "پروژه")
        win = self.window()
        diag = ProjectMediaExplorerDialog(folder_path=path_str, project_title=couple_name, parent=win)
        diag.exec()