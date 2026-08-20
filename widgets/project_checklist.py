# ==================================================
# FILE: widgets/project_checklist.py
# ==================================================
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
import jdatetime
from core.persian_utils import to_persian_numbers
from core.project_controller import ProjectController


class ClipChecklistItem(QFrame):
    toggled = Signal(int)

    def __init__(self, clip_id: int, clip_name: str, is_completed: bool, completed_at: datetime = None, parent=None):
        super().__init__(parent)
        self.clip_id = clip_id
        self.clip_name = clip_name
        self.is_completed = is_completed
        self.completed_at = completed_at
        self.setObjectName("ClipItemFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(14, 10, 14, 10)
        self.layout.setSpacing(12)

        # دکمه چک‌باکس دایره‌ای
        self.btn_check = QPushButton()
        self.btn_check.setFixedSize(24, 24)
        self.btn_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check.clicked.connect(self._on_clicked)
        self.layout.addWidget(self.btn_check)

        # نام کلیپ
        self.lbl_name = QLabel(self.clip_name)
        self.layout.addWidget(self.lbl_name, stretch=1)

        # وضعیت و تاریخ
        self.lbl_status = QLabel()
        self.layout.addWidget(self.lbl_status)

        self._update_appearance()

    def _format_datetime(self, dt: datetime) -> str:
        if not dt:
            return ""
        try:
            j_dt = jdatetime.datetime.fromgregorian(datetime=dt)
            date_str = j_dt.strftime("%Y/%m/%d")
            time_str = j_dt.strftime("%H:%M")
            return f"({to_persian_numbers(date_str)} - {to_persian_numbers(time_str)})"
        except Exception:
            return ""

    def _update_appearance(self):
        if self.is_completed:
            self.setStyleSheet("""
                QFrame#ClipItemFrame {
                    background-color: rgba(16, 185, 129, 0.08);
                    border: 1px solid rgba(16, 185, 129, 0.3);
                    border-radius: 8px;
                }
                QLabel {
                    background: transparent;
                    border: none;
                }
            """)
            self.btn_check.setText("✓")
            self.btn_check.setStyleSheet("""
                QPushButton {
                    background-color: #10B981;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 12px;
                    font-size: 13px;
                    font-weight: bold;
                }
            """)
            self.lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 700; color: #F8FAFC; border: none; background: transparent;")
            
            dt_str = self._format_datetime(self.completed_at)
            status_txt = f"تکمیل شده {dt_str}" if dt_str else "تکمیل شده"
            self.lbl_status.setText(status_txt)
            self.lbl_status.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #10B981; font-weight: 600; border: none; background: transparent;")
        else:
            self.setStyleSheet("""
                QFrame#ClipItemFrame {
                    background-color: #161F30;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                }
                QFrame#ClipItemFrame:hover {
                    background-color: #1A253A;
                    border-color: rgba(99, 102, 241, 0.4);
                }
                QLabel {
                    background: transparent;
                    border: none;
                }
            """)
            self.btn_check.setText("")
            self.btn_check.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 2px solid #475569;
                    border-radius: 12px;
                }
                QPushButton:hover {
                    border-color: #6366F1;
                }
            """)
            self.lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 500; color: #94A3B8; border: none; background: transparent;")
            self.lbl_status.setText("باقی‌مانده")
            self.lbl_status.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; border: none; background: transparent;")

    def _on_clicked(self):
        self.toggled.emit(self.clip_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self._on_clicked()
            return
        super().mouseReleaseEvent(event)


class ProjectChecklistWidget(QWidget):
    progress_changed = Signal(int, int, int)

    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.clip_items: dict[int, ClipChecklistItem] = {}
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        header_row = QHBoxLayout()
        self.lbl_header = QLabel("وضعیت پیشرفت کلیپ‌ها")
        self.lbl_header.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 600; color: #94A3B8; border: none; background: transparent;")
        header_row.addWidget(self.lbl_header, stretch=1)

        self.lbl_fraction = QLabel("۰ / ۰")
        self.lbl_fraction.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #6366F1; border: none; background: transparent;")
        header_row.addWidget(self.lbl_fraction)
        self.main_layout.addLayout(header_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(5)
        self.main_layout.addWidget(self.progress_bar)

        self.items_container = QVBoxLayout()
        self.items_container.setSpacing(8)
        self.main_layout.addLayout(self.items_container)

        self.refresh_checklist()

    def refresh_checklist(self):
        project = ProjectController.get_project_by_id(self.project_id)
        if not project or not project.clips:
            self.lbl_fraction.setText("۰ / ۰")
            self.progress_bar.setValue(0)
            return

        completed_cnt, total_cnt, pct = ProjectController.calculate_project_progress(project)
        self.lbl_fraction.setText(f"{to_persian_numbers(completed_cnt)} از {to_persian_numbers(total_cnt)} کلیپ ({to_persian_numbers(pct)}٪)")
        self.progress_bar.setValue(pct)
        
        if pct == 100:
            self.progress_bar.setStyleSheet("QProgressBar { background-color: #242E42; border: none; border-radius: 2.5px; } QProgressBar::chunk { background-color: #10B981; border-radius: 2.5px; }")
            self.lbl_fraction.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #10B981; border: none; background: transparent;")
        else:
            self.progress_bar.setStyleSheet("QProgressBar { background-color: #242E42; border: none; border-radius: 2.5px; } QProgressBar::chunk { background-color: #6366F1; border-radius: 2.5px; }")
            self.lbl_fraction.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #6366F1; border: none; background: transparent;")

        if not self.clip_items:
            for clip in project.clips:
                item_widget = ClipChecklistItem(clip.id, clip.clip_name, clip.is_completed, clip.completed_at)
                item_widget.toggled.connect(self._handle_clip_toggle)
                self.items_container.addWidget(item_widget)
                self.clip_items[clip.id] = item_widget
        else:
            for clip in project.clips:
                if clip.id in self.clip_items:
                    widget = self.clip_items[clip.id]
                    widget.is_completed = clip.is_completed
                    widget.completed_at = clip.completed_at
                    widget._update_appearance()

        self.progress_changed.emit(completed_cnt, total_cnt, pct)

    def _handle_clip_toggle(self, clip_id: int):
        ProjectController.toggle_clip_status(clip_id)
        self.refresh_checklist()