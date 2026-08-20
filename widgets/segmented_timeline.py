# widgets/segmented_timeline.py
from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtCore import Qt, QRectF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QBrush
from config import PIPELINE_STAGES


class SegmentedTimelineWidget(QWidget):
    """
    ویجت تایم‌لاین سگمنتی به سبک نرم‌افزارهای تدوین NLE
    نمایش مراحل پروژه به صورت بلاک‌های گرافیکی تفکیک‌شده
    """
    def __init__(self, current_stage="rough_cut", parent=None):
        super().__init__(parent)
        self.current_stage = self._normalize_stage(current_stage)
        self.setFixedHeight(10)
        self.setMouseTracking(True)
        
        self.stages_keys = list(PIPELINE_STAGES.keys())
        self.anim_progress = float(self._get_target_progress())

        self.anim = QVariantAnimation(self)
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.valueChanged.connect(self._on_anim_value_changed)

    def _normalize_stage(self, stage_val) -> str:
        if hasattr(stage_val, "value"):
            stage_str = str(stage_val.value).lower()
        else:
            stage_str = str(stage_val).lower() if stage_val else "rough_cut"
        
        stage_mapping = {
            "ingest": "rough_cut",
            "color_audio": "color_grading",
            "audio_vfx": "audio_vfx",
        }
        return stage_mapping.get(stage_str, stage_str)

    def _get_target_progress(self) -> float:
        if self.current_stage not in self.stages_keys:
            return 0.2
        idx = self.stages_keys.index(self.current_stage)
        return (idx + 1) / max(1, len(self.stages_keys))

    def _on_anim_value_changed(self, value):
        self.anim_progress = float(value)
        self.update()

    def set_stage(self, stage_key):
        normalized = self._normalize_stage(stage_key)
        if self.current_stage == normalized:
            return
        self.current_stage = normalized
        target = float(self._get_target_progress())
        self.anim.stop()
        self.anim.setStartValue(float(self.anim_progress))
        self.anim.setEndValue(float(target))
        self.anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = float(self.width())
        h = float(self.height())
        total_stages = len(self.stages_keys)
        spacing = 4.0
        total_spacing = spacing * (total_stages - 1)
        seg_w = max(4.0, (w - total_spacing) / total_stages)

        current_idx = self.stages_keys.index(self.current_stage) if self.current_stage in self.stages_keys else 0

        for i, key in enumerate(self.stages_keys):
            x = i * (seg_w + spacing)
            rect = QRectF(x, 1.0, seg_w, h - 2.0)
            stage_color = QColor(PIPELINE_STAGES[key].get("color", "#6366F1"))

            painter.setPen(Qt.PenStyle.NoPen)
            if i <= current_idx:
                painter.setBrush(QBrush(stage_color))
            else:
                painter.setBrush(QBrush(QColor("#242E42")))

            painter.drawRoundedRect(rect, 3, 3)

        painter.end()

    def mouseMoveEvent(self, event):
        w = float(self.width())
        total_stages = len(self.stages_keys)
        spacing = 4.0
        seg_w = max(4.0, (w - (spacing * (total_stages - 1))) / total_stages)

        if hasattr(event, "pos"):
            pos_x = event.pos().x()
            global_pos = event.globalPos()
        else:
            pos_x = event.position().x()
            global_pos = event.globalPosition().toPoint()

        hovered_idx = int(pos_x // (seg_w + spacing))

        if 0 <= hovered_idx < total_stages:
            key = self.stages_keys[hovered_idx]
            label = PIPELINE_STAGES[key].get("label", key)
            curr_idx = self.stages_keys.index(self.current_stage) if self.current_stage in self.stages_keys else 0
            
            if hovered_idx < curr_idx:
                status = "✓ تکمیل شده"
            elif hovered_idx == curr_idx:
                status = "● در حال انجام"
            else:
                status = "○ در نوبت"

            QToolTip.showText(global_pos, f"{label} ({status})", self)
        else:
            QToolTip.hideText()
            
        super().mouseMoveEvent(event)