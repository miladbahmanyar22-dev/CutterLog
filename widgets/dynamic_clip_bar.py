# ==================================================
# FILE: widgets/dynamic_clip_bar.py
# ==================================================
from typing import List, Dict, Any
from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QBrush, QLinearGradient, QMouseEvent

from core.persian_utils import to_persian_numbers, gregorian_to_jalali
from core.project_controller import ProjectController


class DynamicClipOverviewBar(QWidget):
    """
    نوار پیشرفت سگمنتی تعاملی به سبک تایم‌لاین NLE (DaVinci / Premiere)
    امکان تغییر وضعیت مستقیم کلیپ‌ها با کلیک روی هر سگمنت
    """
    clip_toggled = Signal(int, bool)  # (clip_id, new_status)

    def __init__(self, clips_data: List[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.clips = clips_data or []
        self.setFixedHeight(10)  # ارتفاع مناسب برای کلیک راحت
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hovered_idx = -1

    def set_clips(self, clips_data: List[Dict[str, Any]]):
        self.clips = clips_data or []
        self.update()

    def _get_segment_geometry(self, index: int) -> tuple[float, float, float, float]:
        w = float(self.width())
        h = float(self.height())
        total_clips = len(self.clips)
        if total_clips == 0:
            return 0.0, 0.0, 0.0, 0.0
        
        spacing = 3.0 if total_clips <= 8 else 2.0
        total_spacing = spacing * (total_clips - 1)
        seg_w = max(4.0, (w - total_spacing) / total_clips)
        x = index * (seg_w + spacing)
        return x, 1.0, seg_w, h - 2.0

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

        total_clips = len(self.clips)
        for i, clip in enumerate(self.clips):
            x, y, seg_w, seg_h = self._get_segment_geometry(i)
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
        global_pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()

        total_clips = len(self.clips)
        hovered_idx = -1

        for i in range(total_clips):
            x, _, seg_w, _ = self._get_segment_geometry(i)
            if x <= pos_x <= (x + seg_w + 2.0):
                hovered_idx = i
                break

        if 0 <= hovered_idx < total_clips:
            if self.hovered_idx != hovered_idx:
                self.hovered_idx = hovered_idx
                self.update()

            clip = self.clips[hovered_idx]
            name = clip.get("name") or clip.get("clip_name", f"کلیپ {hovered_idx + 1}")
            is_completed = clip.get("is_completed", False)
            comp_dt = clip.get("completed_at")

            status_txt = "✓ تکمیل شده (کلیک برای بازگردانی)" if is_completed else "○ باقی‌مانده (کلیک برای ثبت تکمیل)"
            dt_txt = f"\nزمان تحویل: {gregorian_to_jalali(comp_dt)}" if (is_completed and comp_dt) else ""

            tip = (
                f"🎬 {name}\n"
                f"وضعیت: {status_txt}{dt_txt}"
            )
            QToolTip.showText(global_pos, tip, self)
        else:
            if self.hovered_idx != -1:
                self.hovered_idx = -1
                self.update()
                QToolTip.hideText()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self.hovered_idx != -1:
            self.hovered_idx = -1
            self.update()
            QToolTip.hideText()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        # مهار کلیک برای جلوگیری از نفوذ به کارت پس‌زمینه
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        # تغییر وضعیت مستقیم کلیپ با مهار کامل رویداد
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            pos_x = event.position().x() if hasattr(event, "position") else event.pos().x()
            for i, clip in enumerate(self.clips):
                x, _, seg_w, _ = self._get_segment_geometry(i)
                if x <= pos_x <= (x + seg_w + 3.0):
                    clip_id = clip.get("id")
                    if clip_id:
                        new_res = ProjectController.toggle_clip_status(clip_id)
                        if new_res is not None:
                            clip["is_completed"] = new_res
                            self.clip_toggled.emit(clip_id, new_res)
                            self.update()
                    break
            return
        super().mouseReleaseEvent(event)