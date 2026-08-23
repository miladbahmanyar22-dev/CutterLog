# ==================================================
# FILE: time_tracking/widgets/manual_entry_dialog.py
# ==================================================
from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, 
    QTextEdit, QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from sqlalchemy import select

from database.db_manager import db
from database.models import Project, ProjectClipItem
from time_tracking.models import WorkSession, SessionStatusEnum
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog
from core.persian_utils import normalize_to_english_digits
from core.signals import global_signals


class FocusStatusSwitchBlock(QFrame):
    """باکس انتخاب رسمی وضعیت مرحله کاری قطعه"""
    valueChanged = Signal(bool)

    def __init__(self, is_complete: bool = False, parent=None):
        super().__init__(parent)
        self.is_complete = is_complete
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.btn_continue = QPushButton("در جریان تدوین و بازبینی")
        self.btn_continue.setFixedHeight(36)
        self.btn_continue.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_continue.clicked.connect(lambda: self._set_state(False))
        btn_row.addWidget(self.btn_continue, stretch=1)

        self.btn_complete = QPushButton("خاتمه فرآیند و ثبت خروجی نهایی")
        self.btn_complete.setFixedHeight(36)
        self.btn_complete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_complete.clicked.connect(lambda: self._set_state(True))
        btn_row.addWidget(self.btn_complete, stretch=1)

        self.layout.addLayout(btn_row)

        self.lbl_feedback = QLabel()
        self.lbl_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_feedback.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600; border: none; background: transparent;")
        self.layout.addWidget(self.lbl_feedback)

        self._update_ui_state()

    def _set_state(self, is_complete: bool):
        if self.is_complete != is_complete:
            self.is_complete = is_complete
            self._update_ui_state()
            self.valueChanged.emit(self.is_complete)

    def _update_ui_state(self):
        if self.is_complete:
            self.setStyleSheet("""
                FocusStatusSwitchBlock {
                    background-color: rgba(16, 185, 129, 0.08);
                    border: 1.5px solid #10B981;
                    border-radius: 10px;
                }
            """)
            self.btn_continue.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    font-size: 11.5px;
                    font-weight: 500;
                    color: #94A3B8;
                    background-color: #121826;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #161F30; color: #F8FAFC; }
            """)
            self.btn_complete.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    font-size: 12px;
                    font-weight: 800;
                    color: #FFFFFF;
                    background-color: #10B981;
                    border: none;
                    border-radius: 6px;
                }
            """)
            self.lbl_feedback.setText("کلیپ در وضعیت خروجی نهایی ثبت و آماده تحویل خواهد شد.")
            self.lbl_feedback.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 700; color: #10B981; border: none; background: transparent;")
        else:
            self.setStyleSheet("""
                FocusStatusSwitchBlock {
                    background-color: rgba(99, 102, 241, 0.08);
                    border: 1.5px solid rgba(99, 102, 241, 0.5);
                    border-radius: 10px;
                }
            """)
            self.btn_continue.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    font-size: 12px;
                    font-weight: 800;
                    color: #FFFFFF;
                    background-color: #6366F1;
                    border: none;
                    border-radius: 6px;
                }
            """)
            self.btn_complete.setStyleSheet("""
                QPushButton {
                    font-family: 'Vazirmatn';
                    font-size: 11.5px;
                    font-weight: 500;
                    color: #94A3B8;
                    background-color: #121826;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                }
                QPushButton:hover { background-color: #161F30; color: #F8FAFC; }
            """)
            self.lbl_feedback.setText("قطعه در وضعیت باز باقی مانده و امکان ادامه ثبت جلسات کاری وجود دارد.")
            self.lbl_feedback.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600; color: #818CF8; border: none; background: transparent;")


class ManualTimeEntryDialog(StudioBaseDialog):
    def __init__(self, initial_project_id: int = None, initial_clip_id: int = None, parent=None):
        super().__init__(parent=parent)
        self.initial_project_id = initial_project_id
        self.initial_clip_id = initial_clip_id
        self.setFixedWidth(460)
        self.init_ui()

    def init_ui(self):
        self.build_header("ثبت دستی زمان کاری", "ثبت سوابق تدوین و اعمال مستقیم به زمان‌سنج قطعه", icon_name="edit", icon_color="#6366F1")

        # ۱. انتخاب پروژه
        self.container_layout.addWidget(QLabel("انتخاب پروژه:"))
        self.combo_project = QComboBox()
        self.combo_project.setFixedHeight(36)
        self.combo_project.currentIndexChanged.connect(self._load_clips_for_project)
        self.container_layout.addWidget(self.combo_project)

        # ۲. انتخاب کلیپ
        self.container_layout.addWidget(QLabel("انتخاب قطعه / کلیپ:"))
        self.combo_clip = QComboBox()
        self.combo_clip.setFixedHeight(36)
        self.container_layout.addWidget(self.combo_clip)

        # ۳. مدت زمان و مرحله کاری
        row = QHBoxLayout()
        row.setSpacing(10)

        col1 = QVBoxLayout()
        col1.setSpacing(3)
        col1.addWidget(QLabel("مدت زمان (دقیقه):*"))
        self.inp_minutes = QLineEdit()
        self.inp_minutes.setFixedHeight(36)
        self.inp_minutes.setPlaceholderText("مثال: 90")
        col1.addWidget(self.inp_minutes)
        row.addLayout(col1, stretch=1)

        col2 = QVBoxLayout()
        col2.setSpacing(3)
        col2.addWidget(QLabel("مرحله فرآیند (اختیاری):"))
        self.inp_stage = QLineEdit()
        self.inp_stage.setFixedHeight(36)
        self.inp_stage.setPlaceholderText("مثال: راف‌کات، تصحیح رنگ...")
        col2.addWidget(self.inp_stage)
        row.addLayout(col2, stretch=1)
        
        self.container_layout.addLayout(row)

        # ۴. باکس وضعیت قطعه
        self.container_layout.addWidget(QLabel("وضعیت قطعه پس از ثبت زمان:*"))
        self.status_block = FocusStatusSwitchBlock(is_complete=False, parent=self)
        self.container_layout.addWidget(self.status_block)

        # ۵. یادداشت فعالیت
        self.container_layout.addWidget(QLabel("یادداشت و جزئیات فعالیت (اختیاری):"))
        self.txt_note = QTextEdit()
        self.txt_note.setFixedHeight(50)
        self.txt_note.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 6px; color: #F8FAFC; font-family: 'Vazirmatn'; font-size: 11.5px;")
        self.container_layout.addWidget(self.txt_note)

        # ۶. دکمه‌های اقدام
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_save = QPushButton("ثبت نهایی فعالیت")
        btn_save.setFixedHeight(38)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 6px;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        btn_save.clicked.connect(self._submit)
        btn_box.addWidget(btn_save, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #1E283D; color: #F8FAFC; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)
        self._load_projects()

    def _load_projects(self):
        self.combo_project.blockSignals(True)
        self.combo_project.clear()
        with db.get_session() as session:
            projs = session.scalars(select(Project).where(Project.is_archived == False).order_by(Project.created_at.desc())).all()
            for p in projs:
                self.combo_project.addItem(p.couple_names or p.title, p.id)

        if self.initial_project_id:
            idx = self.combo_project.findData(self.initial_project_id)
            if idx >= 0:
                self.combo_project.setCurrentIndex(idx)

        self.combo_project.blockSignals(False)
        self._load_clips_for_project()

    def _load_clips_for_project(self):
        self.combo_clip.clear()
        pid = self.combo_project.currentData()
        if not pid:
            return
        with db.get_session() as session:
            clips = session.scalars(select(ProjectClipItem).where(ProjectClipItem.project_id == pid)).all()
            for c in clips:
                label = f"{c.clip_name} {'(تأیید نهایی)' if c.is_completed else ''}"
                self.combo_clip.addItem(label, c.id)

        if self.initial_clip_id:
            idx = self.combo_clip.findData(self.initial_clip_id)
            if idx >= 0:
                self.combo_clip.setCurrentIndex(idx)

    def _submit(self):
        pid = self.combo_project.currentData()
        cid = self.combo_clip.currentData()
        mins_str = normalize_to_english_digits(self.inp_minutes.text().strip())

        if not pid or not mins_str.isdigit() or int(mins_str) <= 0:
            StudioConfirmDialog.ask(self, "خطا", "لطفاً مدت زمان معتبری به دقیقه وارد نمایید.", icon_name="alert")
            return

        is_complete_selected = self.status_block.is_complete
        dur_seconds = int(mins_str) * 60
        stage = self.inp_stage.text().strip() or "Editing"
        note = self.txt_note.toPlainText().strip()

        with db.get_session() as session:
            sess = WorkSession(
                project_id=pid,
                clip_id=cid,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                active_duration=dur_seconds,
                paused_duration=0,
                idle_duration=0,
                total_duration=dur_seconds,
                stage_name=stage,
                status=SessionStatusEnum.COMPLETED,
                note=note,
                is_manual=True,
                is_clip_completed=is_complete_selected
            )
            session.add(sess)

            if is_complete_selected and cid:
                clip = session.get(ProjectClipItem, cid)
                if clip:
                    clip.is_completed = True
                    clip.completed_at = datetime.utcnow()
                    session.flush()
                    global_signals.clip_status_toggled.emit(pid, cid)

            session.commit()

        global_signals.session_ended.emit(0)
        global_signals.project_updated.emit(pid)
        global_signals.show_toast.emit("زمان کاری با موفقیت ثبت شد.", "success")
        self.accept()