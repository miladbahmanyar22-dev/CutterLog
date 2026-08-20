# ==================================================
# FILE: widgets/project_details_dialog.py
# ==================================================
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QTimer
from core.persian_utils import gregorian_to_jalali, to_persian_numbers
from core.project_controller import ProjectController
from core.signals import global_signals
from widgets.project_checklist import ProjectChecklistWidget
from widgets.project_timeline import ProjectTimelineWidget, NewRevisionDialog
from widgets.new_transaction_dialog import NewTransactionDialog
from widgets.project_financial_summary_widget import ProjectFinancialSummaryWidget
from widgets.studio_dialog_base import StudioBaseDialog


class ProjectDetailsDialog(StudioBaseDialog):
    """دیالوگ پرونده جامع پروژه با زبان بصری مدرن و یکپارچه استودیو"""
    def __init__(self, project_id: int, parent=None):
        super().__init__(parent=parent)
        self.project_id = project_id
        self.setMinimumSize(800, 680)
        self.resize(860, 740)
        self.init_ui()
        self._connect_signals()

    def init_ui(self):
        project = ProjectController.get_project_by_id(self.project_id)
        if not project:
            QTimer.singleShot(0, self.reject)
            return

        fin = ProjectController.get_project_financial_summary(project)
        couple = project.couple_names or project.title or "پروژه بدون نام"
        p_num = f"{project.project_number:03d}" if project.project_number else f"{project.id:03d}"
        studio_str = project.client.company if (project.client and project.client.company) else (project.client.full_name if project.client else "بدون استودیو")
        event_str = gregorian_to_jalali(project.event_date) if project.event_date else "-"
        
        status_info = ProjectController.get_status_info(project)
        status_label = status_info.get("label", "در حال تدوین")

        # ۱. سربرگ استاندارد و مدرن استودیو
        self.build_header(
            f"پرونده رسمی: {couple}  ({to_persian_numbers(p_num)})",
            f"طرف قرارداد: {studio_str}    |    تاریخ مراسم: {event_str}    |    وضعیت: {status_label}",
            icon_name="projects",
            icon_color="#818CF8"
        )

        # ۲. کارت خلاصه وضعیت مالی
        self.fin_summary_widget = ProjectFinancialSummaryWidget(financial_data=fin)
        self.container_layout.addWidget(self.fin_summary_widget)

        # ۳. بدنه اسکرول‌شونده پرونده
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(4, 4, 4, 4)
        c_lay.setSpacing(18)

        # بخش تحویل اولیه کلیپ‌ها
        lbl_sec1 = QLabel("تحویل اولیه (کلیپ‌های اصلی مراسم)")
        lbl_sec1.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #6366F1; margin-top: 4px;")
        c_lay.addWidget(lbl_sec1)

        self.checklist_widget = ProjectChecklistWidget(self.project_id, parent=self)
        c_lay.addWidget(self.checklist_widget)

        # بخش تایم‌لاین و اصلاحیه‌ها
        lbl_sec2 = QLabel("تاریخچه رویدادها و دوره‌های اصلاحیه")
        lbl_sec2.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #6366F1; margin-top: 8px;")
        c_lay.addWidget(lbl_sec2)

        self.timeline_widget = ProjectTimelineWidget(self.project_id, parent=self)
        c_lay.addWidget(self.timeline_widget)

        scroll.setWidget(container)
        self.container_layout.addWidget(scroll, stretch=1)

        # ۴. نوار دکمه‌های پایانی
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        btn_add_rev = QPushButton("+ ثبت اصلاحیه جدید")
        btn_add_rev.setFixedHeight(38)
        btn_add_rev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_rev.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(234, 88, 12, 0.15);
                color: #EA580C;
                border: 1px solid rgba(234, 88, 12, 0.35);
                border-radius: 6px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #EA580C; color: #FFFFFF; }
        """)
        btn_add_rev.clicked.connect(self._open_new_revision)
        btn_bar.addWidget(btn_add_rev)

        btn_pay = QPushButton("ثبت واریزی / تسویه 💳")
        btn_pay.setFixedHeight(38)
        btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pay.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(16, 185, 129, 0.15);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 6px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #10B981; color: #FFFFFF; }
        """)
        btn_pay.clicked.connect(self._open_payment)
        btn_bar.addWidget(btn_pay)

        btn_bar.addStretch()

        btn_close = QPushButton("بستن پرونده")
        btn_close.setFixedHeight(38)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 20px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_close.clicked.connect(self.accept)
        btn_bar.addWidget(btn_close)

        self.container_layout.addLayout(btn_bar)

    def _connect_signals(self):
        global_signals.clip_status_toggled.connect(self._on_clip_toggled)

    def _on_clip_toggled(self, pid: int, _cid: int):
        if pid == self.project_id:
            project = ProjectController.get_project_by_id(self.project_id)
            if project:
                fin = ProjectController.get_project_financial_summary(project)
                self.fin_summary_widget.set_data(fin)

    def _open_new_revision(self):
        diag = NewRevisionDialog(self.project_id, self)
        if diag.exec():
            self.timeline_widget.refresh_timeline()
            project = ProjectController.get_project_by_id(self.project_id)
            if project:
                fin = ProjectController.get_project_financial_summary(project)
                self.fin_summary_widget.set_data(fin)

    def _open_payment(self):
        diag = NewTransactionDialog(self.project_id, parent=self)
        if diag.exec():
            project = ProjectController.get_project_by_id(self.project_id)
            if project:
                fin = ProjectController.get_project_financial_summary(project)
                self.fin_summary_widget.set_data(fin)