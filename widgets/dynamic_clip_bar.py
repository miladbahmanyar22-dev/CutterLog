# ==================================================
# FILE: widgets/dynamic_clip_bar.py
# ==================================================
from typing import List, Dict, Any
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QLinearGradient, QMouseEvent
from sqlalchemy import select, func

from database.db_manager import db
from time_tracking.models import WorkSession
from core.project_controller import ProjectController


class DynamicClipOverviewBar(QWidget):
    """
    نوار پیشرفت سگمنتی تعاملی متصل به ماژول زمان و راندمان:
    - نسبت طول هر سگمنت دقیقاً بر اساس دقایق کارکرد ثبت‌شده روی همان کلیپ محاسبه می‌شود.
    - پاپ‌آپ‌های ناخواسته هنگام حرکت موس حذف شده‌اند.
    """
    clip_toggled = Signal(int, bool)  # (clip_id, new_status)

    def __init__(self, clips_data: List[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.clips = clips_data or []
        self.clip_durations: Dict[int, int] = {}
        self.setFixedHeight(10)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hovered_idx = -1
        self._load_durations_from_work_sessions()

    def _load_durations_from_work_sessions(self):
        """استخراج مجموع زمان‌های کارکرد ثبت‌شده برای هر کلیپ از جدول جلسات کاری"""
        self.clip_durations.clear()
        clip_ids = [c.get("id") for c in self.clips if c.get("id")]
        if not clip_ids:
            return

        try:
            with db.get_session() as session:
                stmt = (
                    select(WorkSession.clip_id, func.sum(WorkSession.active_duration))
                    .where(WorkSession.clip_id.in_(clip_ids))
                    .group_by(WorkSession.clip_id)
                )
                for c_id, total_sec in session.execute(stmt).all():
                    if c_id:
                        self.clip_durations[c_id] = total_sec or 0
        except Exception:
            pass

    def set_clips(self, clips_data: List[Dict[str, Any]]):
        self.clips = clips_data or []
        self._load_durations_from_work_sessions()
        self.update()

    def _calculate_segments_layout(self) -> List[tuple[float, float, float, float]]:
        """
        محاسبه داینامیک مختصات و طول هر کلیپ بر اساس دقایق کارکرد
        """
        total_clips = len(self.clips)
        if total_clips == 0:
            return []

        w = float(self.width())
        h = float(self.height())
        spacing = 3.0 if total_clips <= 8 else 2.0
        available_w = max(10.0, w - (spacing * (total_clips - 1)))

        # جمع کل ثانیه‌های کارشده در پروژه
        total_work_seconds = sum(self.clip_durations.get(c.get("id"), 0) for c in self.clips)

        # تعیین حداقل عرض برای هر سگمنت تا کلیپ‌های با زمان صفر محو نشوند
        min_seg_w = max(6.0, available_w / (total_clips * 3.0))
        remaining_pool = max(0.0, available_w - (min_seg_w * total_clips))

        geometries = []
        current_x = 0.0

        for clip in self.clips:
            c_id = clip.get("id")
            c_sec = self.clip_durations.get(c_id, 0)

            if total_work_seconds > 0 and remaining_pool > 0:
                time_ratio = c_sec / total_work_seconds
                seg_w = min_seg_w + (remaining_pool * time_ratio)
            else:
                seg_w = available_w / total_clips

            geometries.append((current_x, 1.0, seg_w, h - 2.0))
            current_x += seg_w + spacing

        return geometries

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())

        if not self.clips:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#161F30")))
            painter.drawRoundedRect(QRectF(0, 1.0, w, h - 2.0), 3, 3)
            painter.end()
            return

        geometries = self._calculate_segments_layout()

        for i, clip in enumerate(self.clips):
            if i >= len(geometries):
                break
            x, y, seg_w, seg_h = geometries[i]
            rect = QRectF(x, y, seg_w, seg_h)
            is_completed = clip.get("is_completed", False)

            grad = QLinearGradient(x, y, x, y + seg_h)
            if is_completed:
                if i == self.hovered_idx:
                    grad.setColorAt(0.0, QColor("#34D399"))
                    grad.setColorAt(1.0, QColor("#10B981"))
                else:
                    grad.setColorAt(0.0, QColor("#10B981"))
                    grad.setColorAt(1.0, QColor("#059669"))
            else:
                if i == self.hovered_idx:
                    grad.setColorAt(0.0, QColor("#3A4866"))
                    grad.setColorAt(1.0, QColor("#242E42"))
                else:
                    grad.setColorAt(0.0, QColor("#1E283D"))
                    grad.setColorAt(1.0, QColor("#121826"))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(rect, 2.5, 2.5)

        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.clips:
            return

        pos_x = event.position().x() if hasattr(event, "position") else event.pos().x()
        geometries = self._calculate_segments_layout()
        found_idx = -1

        for i, (x, _, seg_w, _) in enumerate(geometries):
            if x <= pos_x <= (x + seg_w + 2.0):
                found_idx = i
                break

        if self.hovered_idx != found_idx:
            self.hovered_idx = found_idx
            self.update()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.hovered_idx != -1:
            self.hovered_idx = -1
            self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            pos_x = event.position().x() if hasattr(event, "position") else event.pos().x()
            geometries = self._calculate_segments_layout()

            for i, clip in enumerate(self.clips):
                if i >= len(geometries):
                    break
                x, _, seg_w, _ = geometries[i]
                if x <= pos_x <= (x + seg_w + 3.0):
                    clip_id = clip.get("id")
                    if clip_id:
                        new_res = ProjectController.toggle_clip_status(clip_id)
                        if new_res is not None:
                            clip["is_completed"] = new_res
                            self.clip_toggled.emit(clip_id, new_res)
                            self._load_durations_from_work_sessions()
                            self.update()
                    break
            return
        super().mouseReleaseEvent(event)