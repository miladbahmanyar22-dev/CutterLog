# ==================================================
# FILE: widgets/project_timeline.py
# ==================================================
from datetime import datetime
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QLineEdit, 
    QCheckBox, QMessageBox, QScrollArea, QListWidget, QListWidgetItem, QProgressBar,
    QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
import jdatetime

from database.models import ProjectRevision, ProjectRevisionTask, RevisionStatusEnum
from core.project_controller import ProjectController, get_persian_round_title
from core.persian_utils import format_toman, gregorian_to_jalali, to_persian_numbers, normalize_to_english_digits
from core.icon_provider import IconProvider
from core.signals import global_signals
from widgets.studio_dialog_base import StudioBaseDialog


class RevisionTaskItemWidget(QFrame):
    """ردیف هر تسک با استایل کامپکت و پشتیبانی از متن چندخطی"""
    def __init__(self, task: ProjectRevisionTask, parent=None):
        super().__init__(parent)
        self.task_id = task.id
        self.is_completed = task.is_completed
        self.task = task
        self.setObjectName("RevisionTaskItem")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # دکمه چک‌باکس
        self.btn_check = QPushButton()
        self.btn_check.setFixedSize(22, 22)
        self.btn_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check.clicked.connect(self._toggle)
        layout.addWidget(self.btn_check, alignment=Qt.AlignmentFlag.AlignTop)

        # متن تسک
        self.lbl_text = QLabel(self.task.task_text)
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.lbl_text.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; font-weight: 500; border: none; background: transparent; padding: 2px 0;")
        layout.addWidget(self.lbl_text, stretch=1)

        # زمان و حذف
        left_box = QHBoxLayout()
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(6)
        left_box.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.lbl_dt = QLabel()
        self.lbl_dt.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #10B981; border: none; background: transparent; padding-top: 2px;")
        if self.task.is_completed and self.task.completed_at:
            j_dt = jdatetime.datetime.fromgregorian(datetime=self.task.completed_at).strftime("%H:%M")
            self.lbl_dt.setText(f"✓ ({to_persian_numbers(j_dt)})")
        left_box.addWidget(self.lbl_dt)

        btn_del = QPushButton("×")
        btn_del.setFixedSize(20, 20)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet("background: transparent; color: #EF4444; font-size: 16px; font-weight: bold; border: none;")
        btn_del.clicked.connect(self._delete_self)
        left_box.addWidget(btn_del)

        layout.addLayout(left_box)
        self._update_appearance()

    def _update_appearance(self):
        if self.is_completed:
            self.setStyleSheet("""
                QFrame#RevisionTaskItem {
                    background-color: rgba(16, 185, 129, 0.08);
                    border: none;
                    border-radius: 6px;
                }
            """)
            self.btn_check.setText("✓")
            self.btn_check.setStyleSheet("background-color: #10B981; color: #FFFFFF; border: none; border-radius: 11px; font-size: 11px; font-weight: bold;")
            self.lbl_text.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #F8FAFC; border: none; background: transparent; padding: 2px 0;")
        else:
            self.setStyleSheet("""
                QFrame#RevisionTaskItem {
                    background-color: #161F30;
                    border: none;
                    border-radius: 6px;
                }
                QFrame#RevisionTaskItem:hover {
                    background-color: #1E283D;
                }
            """)
            self.btn_check.setText("")
            self.btn_check.setStyleSheet("background-color: #242E42; border: none; border-radius: 11px;")
            self.lbl_text.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #94A3B8; border: none; background: transparent; padding: 2px 0;")

    def _toggle(self):
        res = ProjectController.toggle_revision_task(self.task_id)
        if res is not None:
            self.is_completed = res
            self._update_appearance()

    def _delete_self(self):
        ProjectController.delete_revision_task(self.task_id)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self._toggle()
            return
        super().mouseReleaseEvent(event)


class RevisionRoundFolderDialog(StudioBaseDialog):
    """دیالوگ مشاهده و مدیریت تسک‌های دور اصلاحیه با هدر استودیویی"""
    def __init__(self, revision_id: int, parent=None):
        super().__init__(parent)
        self.revision_id = revision_id
        self.setFixedWidth(540)
        self.setMinimumHeight(440)
        
        self.init_ui()
        self._connect_signals()
        self.refresh_tasks_only()

    def init_ui(self):
        self.build_header("مشاهده و مدیریت دور اصلاحیه", "چک‌لیست تغییرات و تسک‌های اعمال‌شده", icon_name="folder", icon_color="#6366F1")

        # اطلاعات وضعیت
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        
        self.status_tag = QLabel()
        meta_row.addWidget(self.status_tag)
        
        self.date_lbl = QLabel()
        self.date_lbl.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #94A3B8; border: none;")
        meta_row.addWidget(self.date_lbl, stretch=1)
        
        self.prog_lbl = QLabel()
        self.prog_lbl.setStyleSheet("font-family: 'Vazirmatn'; font-weight: bold; font-size: 12px; border: none;")
        meta_row.addWidget(self.prog_lbl)
        
        self.container_layout.addLayout(meta_row)

        self.pb = QProgressBar()
        self.pb.setRange(0, 100)
        self.pb.setTextVisible(False)
        self.pb.setFixedHeight(4)
        self.container_layout.addWidget(self.pb)

        # ورودی تسک جدید
        add_box = QHBoxLayout()
        add_box.setSpacing(8)
        self.inp_new_task = QLineEdit()
        self.inp_new_task.setFixedHeight(36)
        self.inp_new_task.setPlaceholderText("+ افزودن تغییر جدید به این دور...")
        self.inp_new_task.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 12px; font-size: 12px; color: #F8FAFC;")
        self.inp_new_task.returnPressed.connect(self._add_task)
        add_box.addWidget(self.inp_new_task, stretch=1)

        btn_add = QPushButton("افزودن")
        btn_add.setFixedHeight(36)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("background-color: #6366F1; color: #FFFFFF; font-weight: bold; border: none; border-radius: 6px; padding: 0 16px; font-size: 12px;")
        btn_add.clicked.connect(self._add_task)
        add_box.addWidget(btn_add)
        self.container_layout.addLayout(add_box)

        # اسکرول تسک‌ها
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        self.tasks_container = QWidget()
        self.tasks_container.setStyleSheet("background: transparent;")
        self.t_lay = QVBoxLayout(self.tasks_container)
        self.t_lay.setContentsMargins(0, 4, 0, 4)
        self.t_lay.setSpacing(6)

        scroll.setWidget(self.tasks_container)
        self.container_layout.addWidget(scroll, stretch=1)

        # دکمه بستن
        foot_row = QHBoxLayout()
        foot_row.addStretch()
        btn_close = QPushButton("بستن جزئیات")
        btn_close.setFixedHeight(36)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("background-color: #161F30; color: #94A3B8; font-weight: 600; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 20px; font-size: 12px;")
        btn_close.clicked.connect(self.accept)
        foot_row.addWidget(btn_close)
        self.container_layout.addLayout(foot_row)

    def refresh_tasks_only(self):
        rev = None
        for p in ProjectController.get_all_projects() + ProjectController.get_archived_projects():
            for r in p.revisions:
                if r.id == self.revision_id:
                    rev = r
                    break
            if rev: 
                break

        if not rev:
            self.reject()
            return

        completed_cnt, total_cnt, pct = ProjectController.calculate_revision_progress(rev)
        is_completed = (pct == 100) and (total_cnt > 0)

        tag_bg = "rgba(16, 185, 129, 0.15)" if is_completed else "rgba(245, 158, 11, 0.15)"
        tag_color = "#10B981" if is_completed else "#F59E0B"
        self.status_tag.setText("✓ تکمیل شده" if is_completed else "● در حال انجام")
        self.status_tag.setStyleSheet(f"background-color: {tag_bg}; color: {tag_color}; border: none; padding: 3px 8px; border-radius: 5px; font-family: 'Vazirmatn'; font-weight: bold; font-size: 11px;")

        self.date_lbl.setText(f"ثبت: {gregorian_to_jalali(rev.requested_at)} | کل تغییرات: {to_persian_numbers(total_cnt)}")

        self.prog_lbl.setText(f"{to_persian_numbers(completed_cnt)} از {to_persian_numbers(total_cnt)} ({to_persian_numbers(pct)}٪)")
        self.prog_lbl.setStyleSheet(f"font-family: 'Vazirmatn'; font-weight: bold; font-size: 12px; color: {tag_color}; border: none;")
        self.pb.setValue(pct)
        self.pb.setStyleSheet(f"QProgressBar {{ background-color: #1A2234; border: none; border-radius: 2px; }} QProgressBar::chunk {{ background-color: {tag_color}; border-radius: 2px; }}")

        while self.t_lay.count():
            item = self.t_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if rev.tasks:
            for t in rev.tasks:
                self.t_lay.addWidget(RevisionTaskItemWidget(t))
        else:
            empty_lbl = QLabel("هنوز تغییری در این دوره ثبت نشده است.")
            empty_lbl.setStyleSheet("font-family: 'Vazirmatn'; color: #64748B; font-size: 12px; padding: 24px 0; border: none;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.t_lay.addWidget(empty_lbl)

        self.t_lay.addStretch()

    def _add_task(self):
        txt = self.inp_new_task.text().strip()
        if txt:
            ProjectController.add_task_to_revision(self.revision_id, txt)
            self.inp_new_task.clear()

    def _connect_signals(self):
        global_signals.revision_task_toggled.connect(lambda _p, rid, _t: self._on_sync(rid))
        global_signals.revision_updated.connect(lambda _p, rid: self._on_sync(rid))

    def _on_sync(self, rid: int):
        if rid == self.revision_id:
            QTimer.singleShot(0, self.refresh_tasks_only)


class RevisionFolderSummaryCard(QFrame):
    """کارت خلاصه هر دوره اصلاحیه در پرونده پروژه"""
    def __init__(self, revision: ProjectRevision, parent=None):
        super().__init__(parent)
        self.setObjectName("SurfaceCard")
        self.revision = revision
        self.revision_id = revision.id
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        completed_cnt, total_cnt, pct = ProjectController.calculate_revision_progress(self.revision)
        is_completed = (pct == 100) and (total_cnt > 0)
        is_active = not is_completed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        lbl_title = QLabel(self.revision.title)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #F8FAFC; border: none;")
        top_row.addWidget(lbl_title, stretch=1)

        status_lbl = QLabel()
        if is_completed:
            status_lbl.setText("✓ تکمیل شده")
            status_lbl.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 600; color: #10B981; background-color: rgba(16, 185, 129, 0.12); border-radius: 4px; padding: 2px 6px;")
        elif completed_cnt > 0:
            status_lbl.setText("● در حال انجام")
            status_lbl.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 600; color: #F59E0B; background-color: rgba(245, 158, 11, 0.12); border-radius: 4px; padding: 2px 6px;")
        else:
            status_lbl.setText("○ در انتظار شروع")
            status_lbl.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; font-weight: 500; color: #94A3B8; background-color: #242E42; border-radius: 4px; padding: 2px 6px;")
        top_row.addWidget(status_lbl)
        layout.addLayout(top_row)

        mid_row = QHBoxLayout()
        mid_row.setSpacing(6)
        fraction_text = f"{to_persian_numbers(completed_cnt)} از {to_persian_numbers(total_cnt)} تغییر انجام شده"
        lbl_fraction = QLabel(fraction_text)
        lbl_fraction.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 500; color: #94A3B8; border: none;")
        mid_row.addWidget(lbl_fraction, stretch=1)

        pct_color = "#10B981" if is_completed else ("#F59E0B" if is_active else "#6366F1")
        lbl_pct = QLabel(f"{to_persian_numbers(pct)}٪")
        lbl_pct.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 800; color: {pct_color}; border: none;")
        mid_row.addWidget(lbl_pct)
        layout.addLayout(mid_row)

        pb = QProgressBar()
        pb.setRange(0, 100)
        pb.setValue(pct)
        pb.setTextVisible(False)
        pb.setFixedHeight(3)
        pb.setStyleSheet(f"QProgressBar {{ background-color: #242E42; border: none; border-radius: 1.5px; }} QProgressBar::chunk {{ background-color: {pct_color}; border-radius: 1.5px; }}")
        layout.addWidget(pb)

        date_row = QHBoxLayout()
        date_row.setSpacing(8)
        reg_date = gregorian_to_jalali(self.revision.requested_at)
        dates_text = f"ثبت: {reg_date}"
        if self.revision.completed_at:
            dates_text += f" | تکمیل: {gregorian_to_jalali(self.revision.completed_at)}"
        elif is_active:
            rem_cnt = total_cnt - completed_cnt
            if rem_cnt > 0:
                dates_text += f" | {to_persian_numbers(rem_cnt)} تغییر مانده"

        lbl_dates = QLabel(dates_text)
        lbl_dates.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10.5px; color: #64748B; border: none;")
        date_row.addWidget(lbl_dates, stretch=1)
        layout.addLayout(date_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none;")
        layout.addWidget(divider)

        foot_row = QHBoxLayout()
        foot_row.setSpacing(6)
        if self.revision.extra_fee > 0:
            lbl_fee = QLabel(f"هزینه دوره: {format_toman(self.revision.extra_fee)}")
            lbl_fee.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600; color: #FBBF24; border: none;")
            foot_row.addWidget(lbl_fee)

        foot_row.addStretch()
        btn_action = QPushButton("ادامه اصلاحیه ←" if is_active else "مشاهده جزئیات ←")
        btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        if is_active:
            btn_action.setStyleSheet("QPushButton { font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 700; background-color: rgba(245, 158, 11, 0.15); color: #F59E0B; border: none; border-radius: 5px; padding: 4px 10px; } QPushButton:hover { background-color: #F59E0B; color: #000000; }")
        else:
            btn_action.setStyleSheet("QPushButton { font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 600; background-color: transparent; color: #6366F1; border: none; padding: 4px 6px; } QPushButton:hover { color: #7C80F8; }")
        btn_action.clicked.connect(self._open_folder)
        foot_row.addWidget(btn_action)
        layout.addLayout(foot_row)

        self.setStyleSheet("QFrame#SurfaceCard { background-color: #161F30; border: none; border-radius: 8px; } QFrame#SurfaceCard:hover { background-color: #1A253A; }")

    def _open_folder(self):
        diag = RevisionRoundFolderDialog(self.revision_id, self.window())
        diag.exec()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            QTimer.singleShot(0, self._open_folder)
            return
        super().mouseReleaseEvent(event)


class ProjectTimelineWidget(QWidget):
    """بخش تاریخچه دوره‌های اصلاحیه در پاپ‌آپ پرونده"""
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()
        self.refresh_timeline()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(8)

    def refresh_timeline(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        project = ProjectController.get_project_by_id(self.project_id)
        if not project:
            return

        if not project.revisions:
            empty_frame = QFrame()
            empty_frame.setStyleSheet("background-color: #121826; border: none; border-radius: 8px; padding: 18px;")
            empty_lay = QVBoxLayout(empty_frame)
            empty_lay.setSpacing(4)
            empty_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

            lbl_empty_title = QLabel("هنوز دوره‌ای از اصلاحیه برای این پروژه ثبت نشده است.")
            lbl_empty_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 700; color: #94A3B8; border: none;")
            lbl_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lay.addWidget(lbl_empty_title)

            lbl_empty_desc = QLabel("دوره‌های اصلاحیه پس از تحویل اولیه و با ارسال موارد تغییرات از طرف استودیو ایجاد می‌شوند.")
            lbl_empty_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; border: none;")
            lbl_empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lay.addWidget(lbl_empty_desc)

            self.main_layout.addWidget(empty_frame)
            return

        for rev in project.revisions:
            self.main_layout.addWidget(RevisionFolderSummaryCard(rev))


class NewRevisionDialog(StudioBaseDialog):
    """دیالوگ ثبت دور جدید اصلاحیه با سیستم دیالوگ استودیو"""
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        
        project = ProjectController.get_project_by_id(self.project_id)
        self.round_number = (len(project.revisions) + 1) if project else 1
        self.round_title = get_persian_round_title(self.round_number)

        self.setFixedWidth(480)
        self.init_ui()

    def init_ui(self):
        self.build_header(f"ثبت {self.round_title}", "تعریف موارد تغییرات درخواستی استودیو", icon_name="revision", icon_color="#EA580C")

        self.container_layout.addWidget(QLabel("تغییرات مدنظر را وارد کرده و دکمه افزودن را بزنید:"))

        add_task_row = QHBoxLayout()
        add_task_row.setSpacing(8)
        self.input_task = QLineEdit()
        self.input_task.setFixedHeight(36)
        self.input_task.setPlaceholderText("مثال: اصلاح رنگ سکانس رقص، تعویض موزیک...")
        self.input_task.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        self.input_task.returnPressed.connect(self._add_task)
        add_task_row.addWidget(self.input_task, stretch=1)

        btn_add = QPushButton("+ افزودن")
        btn_add.setFixedHeight(36)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("background-color: #6366F1; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 0 14px; font-size: 12px; border: none;")
        btn_add.clicked.connect(self._add_task)
        add_task_row.addWidget(btn_add)
        self.container_layout.addLayout(add_task_row)

        self.tasks_list = QListWidget()
        self.tasks_list.setFixedHeight(120)
        self.tasks_list.setStyleSheet("""
            QListWidget {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 6px;
                color: #F8FAFC;
                padding: 4px;
                font-family: 'Vazirmatn';
                font-size: 11.5px;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 4px;
                background-color: #161F30;
                margin-bottom: 3px;
            }
        """)
        self.tasks_list.itemDoubleClicked.connect(self._remove_selected_task)
        self.container_layout.addWidget(self.tasks_list)

        lbl_hint = QLabel("<span style='color:#64748B; font-size:10.5px;'>* برای حذف هر مورد، روی آن دوبار کلیک کنید.</span>")
        self.container_layout.addWidget(lbl_hint)

        self.chk_fee = QCheckBox("این دوره از اصلاحیه‌ها مشمول هزینه مازاد است")
        self.chk_fee.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
        self.chk_fee.toggled.connect(lambda v: self.input_fee.setEnabled(v))
        self.container_layout.addWidget(self.chk_fee)

        self.input_fee = QLineEdit()
        self.input_fee.setFixedHeight(34)
        self.input_fee.setPlaceholderText("مبلغ توافق‌شده به تومان (مثال: 500000)...")
        self.input_fee.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; font-size: 12px; color: #F8FAFC;")
        self.input_fee.setEnabled(False)
        self.container_layout.addWidget(self.input_fee)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_submit = QPushButton(f"ایجاد {self.round_title}")
        self.btn_submit.setFixedHeight(38)
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setStyleSheet("background-color: #EA580C; color: #FFFFFF; font-weight: bold; border-radius: 6px; border: none; font-size: 12.5px;")
        self.btn_submit.clicked.connect(self._submit)
        btn_box.addWidget(self.btn_submit, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("background-color: #161F30; color: #94A3B8; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; font-size: 12px;")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _add_task(self):
        t = self.input_task.text().strip()
        if t:
            self.tasks_list.addItem(t)
            self.input_task.clear()

    def _remove_selected_task(self, item: QListWidgetItem):
        row = self.tasks_list.row(item)
        self.tasks_list.takeItem(row)

    def _submit(self):
        tasks = [self.tasks_list.item(i).text().strip() for i in range(self.tasks_list.count())]
        current_input = self.input_task.text().strip()
        if current_input and current_input not in tasks:
            tasks.append(current_input)

        if not tasks:
            return

        fee = 0
        if self.chk_fee.isChecked():
            fee_str = normalize_to_english_digits(self.input_fee.text().strip())
            fee = int(fee_str) if fee_str.isdigit() else 0

        self.btn_submit.setEnabled(False)
        if ProjectController.create_revision_round(self.project_id, "", tasks, fee):
            self.accept()
        else:
            self.btn_submit.setEnabled(True)