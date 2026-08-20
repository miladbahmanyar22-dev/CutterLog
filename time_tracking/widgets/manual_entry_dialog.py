# ==================================================
# FILE: time_tracking/widgets/manual_entry_dialog.py
# ==================================================
from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QTextEdit, QPushButton
)
from PySide6.QtCore import Qt
from sqlalchemy import select

from database.db_manager import db
from database.models import Project, ProjectClipItem
from time_tracking.models import WorkSession, SessionStatusEnum
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog
from core.persian_utils import normalize_to_english_digits
from core.signals import global_signals


class ManualTimeEntryDialog(StudioBaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setFixedWidth(460)
        self.init_ui()

    def init_ui(self):
        self.build_header("ثبت زمان کاری دستی", "ثبت سشن‌های خارج از تایمر به صورت دستی با پرچم manual", icon_name="edit", icon_color="#6366F1")

        self.container_layout.addWidget(QLabel("انتخاب پروژه:"))
        self.combo_project = QComboBox()
        self.combo_project.setFixedHeight(36)
        self.combo_project.currentIndexChanged.connect(self._load_clips_for_project)
        self.container_layout.addWidget(self.combo_project)

        self.container_layout.addWidget(QLabel("انتخاب کلیپ (اختیاری):"))
        self.combo_clip = QComboBox()
        self.combo_clip.setFixedHeight(36)
        self.container_layout.addWidget(self.combo_clip)

        row = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("مدت زمان به دقیقه:*"))
        self.inp_minutes = QLineEdit()
        self.inp_minutes.setFixedHeight(36)
        self.inp_minutes.setPlaceholderText("مثال: 90")
        col1.addWidget(self.inp_minutes)
        row.addLayout(col1)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel("مرحله کاری:"))
        self.combo_stage = QComboBox()
        self.combo_stage.setFixedHeight(36)
        self.combo_stage.addItems(["Editing", "Culling", "Selection", "Color", "Audio"])
        col2.addWidget(self.combo_stage)
        row.addLayout(col2)
        self.container_layout.addLayout(row)

        self.container_layout.addWidget(QLabel("یادداشت فعالیت:"))
        self.txt_note = QTextEdit()
        self.txt_note.setFixedHeight(65)
        self.txt_note.setStyleSheet("background-color: #161F30; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 6px; color: #F8FAFC; font-family: 'Vazirmatn';")
        self.container_layout.addWidget(self.txt_note)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("ثبت فعالیت دستی")
        btn_save.setFixedHeight(38)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("background-color: #6366F1; color: #FFFFFF; font-weight: bold; border-radius: 6px; border: none; font-family: 'Vazirmatn';")
        btn_save.clicked.connect(self._submit)
        btn_box.addWidget(btn_save, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("background-color: #161F30; color: #94A3B8; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; font-family: 'Vazirmatn';")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)
        self._load_projects()

    def _load_projects(self):
        self.combo_project.clear()
        with db.get_session() as session:
            projs = session.scalars(select(Project).where(Project.is_archived == False)).all()
            for p in projs:
                self.combo_project.addItem(p.couple_names or p.title, p.id)

    def _load_clips_for_project(self):
        self.combo_clip.clear()
        self.combo_clip.addItem("کل پروژه (بدون کلیپ خاص)", None)
        pid = self.combo_project.currentData()
        if not pid:
            return
        with db.get_session() as session:
            clips = session.scalars(select(ProjectClipItem).where(ProjectClipItem.project_id == pid)).all()
            for c in clips:
                self.combo_clip.addItem(c.clip_name, c.id)

    def _submit(self):
        pid = self.combo_project.currentData()
        cid = self.combo_clip.currentData()
        mins_str = normalize_to_english_digits(self.inp_minutes.text().strip())

        if not pid or not mins_str.isdigit() or int(mins_str) <= 0:
            StudioConfirmDialog.ask(self, "خطا", "لطفاً مدت زمان معتبری به دقیقه وارد کنید.", icon_name="alert")
            return

        dur_seconds = int(mins_str) * 60
        stage = self.combo_stage.currentText()
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
                is_manual=True
            )
            session.add(sess)
            session.commit()

        global_signals.session_ended.emit(0)
        global_signals.show_toast.emit("زمان کاری دستی با موفقیت ثبت شد.", "success")
        self.accept()