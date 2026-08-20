# widgets/stage_stepper.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QFrame
from PySide6.QtCore import Qt, Signal
from config import PIPELINE_STAGES


class StageStepper(QWidget):
    stage_changed = Signal(str)

    def __init__(self, current_stage: str = "rough_cut", parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.current_stage = current_stage
        self.buttons = {}
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(4)

        stages_list = list(PIPELINE_STAGES.items())
        current_idx = self._get_stage_index(self.current_stage)

        for idx, (key, info) in enumerate(stages_list):
            btn = QPushButton(info["label"])
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            
            # استایل‌دهی بر اساس وضعیت مرحله
            if idx < current_idx:
                # مرحله پشت سر گذاشته شده (تکمیل)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(16, 185, 129, 0.15);
                        color: #10B981;
                        border: 1px solid rgba(16, 185, 129, 0.3);
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: bold;
                        padding: 0 8px;
                    }
                    QPushButton:hover {
                        background-color: rgba(16, 185, 129, 0.25);
                    }
                """)
            elif idx == current_idx:
                # مرحله جاری و فعال
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #6366F1;
                        color: #FFFFFF;
                        border: 1px solid #7C80F8;
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: bold;
                        padding: 0 8px;
                    }
                    QPushButton:hover {
                        background-color: #7C80F8;
                    }
                """)
            else:
                # مراحل آینده
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #242E42;
                        color: #94A3B8;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 6px;
                        font-size: 11px;
                        padding: 0 8px;
                    }
                    QPushButton:hover {
                        background-color: #2D3952;
                        color: #F8FAFC;
                        border-color: rgba(99, 102, 241, 0.5);
                    }
                """)

            btn.clicked.connect(lambda _, k=key: self._on_step_clicked(k))
            layout.addWidget(btn, stretch=1)
            self.buttons[key] = btn

            # خط اتصال بین مراحل
            if idx < len(stages_list) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFixedHeight(2)
                line_color = "#10B981" if idx < current_idx else ("rgba(99, 102, 241, 0.5)" if idx == current_idx else "rgba(255, 255, 255, 0.08)")
                line.setStyleSheet(f"background-color: {line_color}; border: none;")
                layout.addWidget(line)

    def _get_stage_index(self, stage_key: str) -> int:
        stages_keys = list(PIPELINE_STAGES.keys())
        return stages_keys.index(stage_key) if stage_key in stages_keys else 0

    def _on_step_clicked(self, stage_key: str):
        self.current_stage = stage_key
        self.stage_changed.emit(stage_key)
        self._refresh_styles()

    def set_stage(self, stage_key: str):
        self.current_stage = stage_key
        self._refresh_styles()

    def _refresh_styles(self):
        # پاکسازی و چینش دوباره
        while self.layout().count():
            item = self.layout().takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.init_ui()