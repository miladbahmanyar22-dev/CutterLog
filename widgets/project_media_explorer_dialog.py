# ==================================================
# FILE: widgets/project_media_explorer_dialog.py
# ==================================================
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QLineEdit, QScrollArea, 
    QWidget, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QSlider, QSizePolicy,
    QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, QSize, QUrl, Signal, QByteArray, QThreadPool, 
    QPropertyAnimation, QEasingCurve
)
from PySide6.QtGui import QPixmap, QPainter, QIcon, QKeyEvent
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from config import open_path_in_os
from core.media_scanner import scan_directory_fast, ThumbnailWorker
from core.persian_utils import to_persian_numbers


SVG_TEMPLATES = {
    "arrow_left": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>''',
    "arrow_right": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>''',
    "arrow_up": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>''',
    "grid": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>''',
    "list": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>''',
    "folder": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>''',
    "external_link": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>''',
    "play": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}" stroke="{color}" stroke-width="1"><polygon points="5 3 19 12 5 21 5 3"/></svg>''',
    "pause": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{color}" stroke="{color}" stroke-width="1"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>''',
    "check": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>''',
    "close": '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>'''
}


def render_svg_icon(name: str, color: str = "#818CF8", size: int = 16, stroke: float = 2.0) -> QIcon:
    template = SVG_TEMPLATES.get(name)
    if not template:
        return QIcon()
    renderer = QSvgRenderer(QByteArray(template.format(color=color, stroke=stroke).encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def render_svg_pixmap(name: str, color: str = "#818CF8", size: int = 16, stroke: float = 2.0) -> QPixmap:
    template = SVG_TEMPLATES.get(name)
    if not template:
        return QPixmap()
    renderer = QSvgRenderer(QByteArray(template.format(color=color, stroke=stroke).encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QPixmap(pixmap)


def get_file_type_badge_svg(ext: str, category: str) -> QPixmap:
    ext_upper = (ext or "RAW").upper()
    color_map = {
        "PRPROJ": "#9999FF", "DRP": "#FF4A4A", "AEP": "#D291FF",
        "MP4": "#38BDF8", "MOV": "#60A5FA", "MXF": "#818CF8",
        "WAV": "#34D399", "MP3": "#10B981", "JPG": "#FBBF24",
        "JPEG": "#FBBF24", "PNG": "#F59E0B", "DNG": "#FB923C",
        "ARW": "#FB923C", "PDF": "#EF4444"
    }
    badge_color = color_map.get(ext_upper, "#94A3B8")

    svg_data = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
        <rect x="8" y="6" width="48" height="52" rx="8" fill="#141B2A" stroke="{badge_color}" stroke-width="2.2" />
        <path d="M40 6 L56 22 L40 22 Z" fill="{badge_color}" opacity="0.30" />
        <rect x="12" y="34" width="40" height="18" rx="4" fill="{badge_color}" opacity="0.15" />
        <text x="32" y="47" font-family="Segoe UI, sans-serif" font-size="11" font-weight="900" fill="{badge_color}" text-anchor="middle">{ext_upper[:5]}</text>
    </svg>
    """
    renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


class AppleQuickLookDialog(QDialog):
    """پنجره پیش‌نمایش شناور با پلیر بهینه‌شده و شروع آنی"""
    def __init__(self, file_data: dict, preloaded_player: QMediaPlayer, preloaded_audio: QAudioOutput, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.player = preloaded_player
        self.audio_output = preloaded_audio
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.setFixedSize(780, 530)
        self._setup_ui()
        self._setup_animation()

    def _setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        self.main_container = QFrame()
        self.main_container.setObjectName("QuickLookContainer")
        self.main_container.setStyleSheet("""
            QFrame#QuickLookContainer {
                background-color: #0C101B;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
            }
        """)
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(18, 14, 18, 16)
        container_layout.setSpacing(12)

        # سربرگ
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        self.lbl_title = QLabel(self.file_data.get("name", "Media Preview"))
        self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 14px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        header_row.addWidget(self.lbl_title, stretch=1)

        btn_close = QPushButton()
        btn_close.setIcon(render_svg_icon("close", "#94A3B8", size=14, stroke=2.5))
        btn_close.setIconSize(QSize(14, 14))
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setToolTip("بستن (Space / Esc)")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                border-color: #EF4444;
            }
        """)
        btn_close.clicked.connect(self.close)
        header_row.addWidget(btn_close)
        container_layout.addLayout(header_row)

        # ویدیو و HUD
        self.video_area = QFrame()
        self.video_area.setFixedHeight(370)
        self.video_area.setStyleSheet("background-color: #000000; border-radius: 8px;")
        v_layout = QVBoxLayout(self.video_area)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        self.video_widget = QVideoWidget(self.video_area)
        self.player.setVideoOutput(self.video_widget)
        v_layout.addWidget(self.video_widget)

        self.hud_controls = QFrame(self.video_area)
        self.hud_controls.setFixedHeight(48)
        self.hud_controls.setStyleSheet("""
            QFrame {
                background-color: rgba(12, 16, 27, 0.90);
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        hud_layout = QHBoxLayout(self.hud_controls)
        hud_layout.setContentsMargins(14, 0, 14, 0)
        hud_layout.setSpacing(10)

        self.btn_play = QPushButton()
        self.btn_play.setIcon(render_svg_icon("pause", "#FFFFFF", size=12))
        self.btn_play.setIconSize(QSize(12, 12))
        self.btn_play.setFixedSize(28, 28)
        self.btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_play.setStyleSheet("background-color: #6366F1; border-radius: 14px; border: none;")
        self.btn_play.clicked.connect(self._toggle_play)
        hud_layout.addWidget(self.btn_play)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { height: 4px; background: rgba(255, 255, 255, 0.15); border-radius: 2px; }
            QSlider::sub-page:horizontal { background: #6366F1; border-radius: 2px; }
            QSlider::handle:horizontal { width: 12px; margin: -4px 0; background: #F8FAFC; border-radius: 6px; }
        """)
        self.slider.sliderMoved.connect(lambda pos: self.player.setPosition(pos))
        hud_layout.addWidget(self.slider)

        self.lbl_time = QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("font-family: -apple-system, 'Segoe UI', 'Vazirmatn'; font-size: 11px; font-weight: 700; color: #94A3B8; border: none; background: transparent;")
        hud_layout.addWidget(self.lbl_time)

        v_layout.addWidget(self.hud_controls)
        container_layout.addWidget(self.video_area)

        # کپسول‌های افقی
        capsule_row = QHBoxLayout()
        capsule_row.setSpacing(8)

        capsule_row.addWidget(self._create_capsule(self.file_data.get("ext", "RAW"), "#818CF8"))
        capsule_row.addWidget(self._create_capsule(self.file_data.get("resolution", "—"), "#38BDF8"))
        capsule_row.addWidget(self._create_capsule(self.file_data.get("fps", "—"), "#C084FC"))
        capsule_row.addWidget(self._create_capsule(to_persian_numbers(self.file_data.get("size_str", "—")), "#34D399"))
        capsule_row.addWidget(self._create_capsule(to_persian_numbers(self.file_data.get("duration_str", "--:--")), "#FBBF24"))
        capsule_row.addStretch()

        lbl_hint = QLabel("Space یا Esc: بستن پنجره")
        lbl_hint.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; border: none; background: transparent;")
        capsule_row.addWidget(lbl_hint)

        container_layout.addLayout(capsule_row)
        root_layout.addWidget(self.main_container)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)

        if self.file_data.get("category") == "video":
            self.player.setSource(QUrl.fromLocalFile(self.file_data["path"]))
            self.player.play()
        else:
            self.hud_controls.setVisible(False)

    def _create_capsule(self, text: str, color_hex: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFixedHeight(26)
        lbl.setStyleSheet(f"""
            QLabel {{
                font-family: -apple-system, 'Segoe UI', 'Vazirmatn';
                font-size: 11px;
                font-weight: 700;
                color: {color_hex};
                background-color: #141B2A;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 10px;
            }}
        """)
        return lbl

    def _setup_animation(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(120)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play.setIcon(render_svg_icon("play", "#FFFFFF", size=12))
        else:
            self.player.play()
            self.btn_play.setIcon(render_svg_icon("pause", "#FFFFFF", size=12))

    def _on_position_changed(self, pos):
        self.slider.setValue(pos)
        cur = pos // 1000
        dur = self.player.duration() // 1000
        self.lbl_time.setText(f"{cur//60:02d}:{cur%60:02d} / {dur//60:02d}:{dur%60:02d}")

    def _on_duration_changed(self, dur):
        self.slider.setRange(0, dur)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Escape):
            event.accept()
            self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        try:
            self.player.positionChanged.disconnect(self._on_position_changed)
            self.player.durationChanged.disconnect(self._on_duration_changed)
        except Exception:
            pass
        self.player.stop()
        self.player.setSource(QUrl())
        super().closeEvent(event)


class StudioMediaCard(QFrame):
    clicked = Signal(dict)
    double_clicked = Signal(dict)

    def __init__(self, file_data: dict, index_num: int = 1, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.index_num = index_num
        self.is_selected = False

        self.setObjectName("StudioMediaCard")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._setup_ui()
        self._update_appearance()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.thumb_box = QFrame()
        self.thumb_box.setFixedHeight(96)
        self.thumb_box.setStyleSheet("background-color: #0A0E17; border-radius: 6px;")
        thumb_layout = QVBoxLayout(self.thumb_box)
        thumb_layout.setContentsMargins(5, 5, 5, 5)

        top_row = QHBoxLayout()
        lbl_idx = QLabel(to_persian_numbers(f"#{self.index_num:02d}"))
        lbl_idx.setStyleSheet("""
            background-color: rgba(11, 15, 23, 0.85);
            color: #818CF8;
            font-family: -apple-system, 'Segoe UI', 'Vazirmatn';
            font-size: 9px;
            font-weight: 800;
            padding: 1px 4px;
            border-radius: 3px;
        """)
        top_row.addWidget(lbl_idx)
        top_row.addStretch()

        self.lbl_chk = QLabel()
        self.lbl_chk.setFixedSize(16, 16)
        self.lbl_chk.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_chk.setStyleSheet("background-color: rgba(18, 24, 38, 0.8); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px;")
        top_row.addWidget(self.lbl_chk)
        thumb_layout.addLayout(top_row)
        thumb_layout.addStretch()

        bot_row = QHBoxLayout()
        self.lbl_res = QLabel(self.file_data.get("resolution", "—"))
        self.lbl_res.setStyleSheet("background-color: rgba(11, 15, 23, 0.85); color: #38BDF8; font-family: 'Vazirmatn'; font-size: 8.5px; font-weight: 700; padding: 1px 4px; border-radius: 3px;")
        self.lbl_res.setVisible(self.file_data.get("resolution") != "—")
        bot_row.addWidget(self.lbl_res)

        bot_row.addStretch()

        self.lbl_dur = QLabel(to_persian_numbers(self.file_data.get("duration_str", "--:--")))
        self.lbl_dur.setStyleSheet("background-color: rgba(99, 102, 241, 0.9); color: #FFFFFF; font-family: -apple-system, 'Segoe UI', 'Vazirmatn'; font-size: 9px; font-weight: bold; padding: 1px 4px; border-radius: 3px;")
        self.lbl_dur.setVisible(self.file_data.get("duration_str") != "--:--")
        bot_row.addWidget(self.lbl_dur)

        thumb_layout.addLayout(bot_row)
        layout.addWidget(self.thumb_box)

        self.lbl_bg = QLabel(self.thumb_box)
        self.lbl_bg.setGeometry(0, 0, 240, 96)
        self.lbl_bg.lower()

        if self.file_data.get("thumbnail_pixmap"):
            self.set_loaded_thumbnail(self.file_data["thumbnail_pixmap"])
        else:
            svg_icon = get_file_type_badge_svg(self.file_data.get("ext", "RAW"), self.file_data.get("category", "other"))
            self.lbl_bg.setPixmap(svg_icon)
            self.lbl_bg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_name = QLabel(self.file_data.get("name", "Clip"))
        lbl_name.setToolTip(self.file_data.get("name"))
        lbl_name.setFixedHeight(16)
        lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 700; color: #F8FAFC; border: none; background: transparent;")
        layout.addWidget(lbl_name)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(4)
        
        lbl_ext = QLabel(self.file_data.get("ext", "RAW"))
        lbl_ext.setStyleSheet("font-family: -apple-system, 'Segoe UI'; font-size: 9px; font-weight: 800; color: #818CF8;")
        meta_row.addWidget(lbl_ext)

        meta_row.addWidget(QLabel("•"))

        lbl_size = QLabel(to_persian_numbers(self.file_data.get("size_str", "")))
        lbl_size.setStyleSheet("font-family: 'Vazirmatn'; font-size: 9px; color: #64748B;")
        meta_row.addWidget(lbl_size)

        self.lbl_fps = QLabel(self.file_data.get("fps", ""))
        self.lbl_fps.setStyleSheet("font-family: -apple-system, 'Segoe UI'; font-size: 8.5px; color: #64748B;")
        self.lbl_fps.setVisible(self.file_data.get("fps") != "—")
        meta_row.addWidget(self.lbl_fps)

        meta_row.addStretch()
        layout.addLayout(meta_row)

    def set_loaded_thumbnail(self, pixmap: QPixmap, meta: dict = None):
        if pixmap and not pixmap.isNull():
            self.lbl_bg.setPixmap(pixmap)
            self.lbl_bg.setScaledContents(True)

        if meta:
            if meta.get("resolution") != "—":
                self.lbl_res.setText(meta["resolution"])
                self.lbl_res.setVisible(True)
                self.file_data["resolution"] = meta["resolution"]
            if meta.get("duration_str") != "--:--":
                self.lbl_dur.setText(to_persian_numbers(meta["duration_str"]))
                self.lbl_dur.setVisible(True)
                self.file_data["duration_str"] = meta["duration_str"]
            if meta.get("fps") != "—":
                self.lbl_fps.setText(meta["fps"])
                self.lbl_fps.setVisible(True)
                self.file_data["fps"] = meta["fps"]

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_appearance()

    def _update_appearance(self):
        if self.is_selected:
            self.setStyleSheet("""
                QFrame#StudioMediaCard {
                    background-color: #1A2438;
                    border: 1.5px solid #6366F1;
                    border-radius: 8px;
                }
            """)
            self.lbl_chk.setPixmap(render_svg_pixmap("check", "#FFFFFF", size=10, stroke=3.0))
            self.lbl_chk.setStyleSheet("background-color: #6366F1; border: 1px solid #6366F1; border-radius: 8px;")
        else:
            self.setStyleSheet("""
                QFrame#StudioMediaCard {
                    background-color: #121826;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                }
                QFrame#StudioMediaCard:hover {
                    background-color: #161F30;
                    border: 1px solid rgba(99, 102, 241, 0.35);
                }
            """)
            self.lbl_chk.setPixmap(QPixmap())
            self.lbl_chk.setStyleSheet("background-color: rgba(18, 24, 38, 0.7); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_data)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.file_data)
        super().mouseDoubleClickEvent(event)


class FolderItemPill(QFrame):
    double_clicked = Signal(str)

    def __init__(self, folder_data: dict, parent=None):
        super().__init__(parent)
        self.folder_data = folder_data
        self.setObjectName("FolderPill")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self.setMinimumWidth(170)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(render_svg_pixmap("folder", "#FBBF24", size=16))
        layout.addWidget(lbl_icon)

        lbl_name = QLabel(folder_data["name"])
        lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: #F8FAFC; background: transparent;")
        layout.addWidget(lbl_name, stretch=1)

        lbl_cnt = QLabel(f"({to_persian_numbers(folder_data['sub_items_count'])})")
        lbl_cnt.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10px; color: #64748B; background: transparent;")
        layout.addWidget(lbl_cnt)

        self.setStyleSheet("""
            QFrame#FolderPill {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
            }
            QFrame#FolderPill:hover {
                background-color: #1E283D;
                border-color: #6366F1;
            }
        """)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.folder_data["path"])
        super().mouseDoubleClickEvent(event)


class ProjectMediaExplorerDialog(QDialog):
    def __init__(self, folder_path: str, project_title: str = "", parent=None):
        super().__init__(parent)
        self.current_path = folder_path
        self.project_title = project_title
        self.view_mode = "grid"
        
        self.selected_file_data: Optional[dict] = None
        self.active_cards: Dict[str, StudioMediaCard] = {}
        self.quick_look_dialog: Optional[AppleQuickLookDialog] = None
        self.current_workers: List[ThumbnailWorker] = []
        self.current_generation = 0

        self.history_back = []
        self.history_forward = []

        self.preloaded_player = QMediaPlayer(self)
        self.preloaded_audio = QAudioOutput(self)
        self.preloaded_player.setAudioOutput(self.preloaded_audio)

        self.threadpool = QThreadPool.globalInstance()
        self.threadpool.setMaxThreadCount(3)

        self.setWindowTitle(f"مدیریت راش‌ها و مدیا: {project_title}")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumSize(940, 640)
        self.resize(1120, 720)
        self.setStyleSheet("background-color: #0B0F17; color: #F8FAFC;")

        self.init_ui()
        self.navigate_to(self.current_path, add_to_history=False)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(10)

        # نوار مسیر
        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)

        self.btn_back = self._create_svg_btn("arrow_left", "قبلی", self._go_back)
        self.btn_forward = self._create_svg_btn("arrow_right", "بعدی", self._go_forward)
        self.btn_up = self._create_svg_btn("arrow_up", "پوشه بالا", self._go_up)
        top_bar.addWidget(self.btn_back)
        top_bar.addWidget(self.btn_forward)
        top_bar.addWidget(self.btn_up)

        self.address_bar = QLineEdit()
        self.address_bar.setReadOnly(True)
        self.address_bar.setFixedHeight(34)
        self.address_bar.setStyleSheet("background-color: #121826; border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 0 10px; color: #94A3B8; font-size: 11.5px;")
        top_bar.addWidget(self.address_bar, stretch=1)

        btn_open_win = QPushButton("نمایش در سیستم‌عامل")
        btn_open_win.setIcon(render_svg_icon("external_link", "#818CF8", size=13))
        btn_open_win.setIconSize(QSize(13, 13))
        btn_open_win.setFixedHeight(34)
        btn_open_win.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_win.setStyleSheet("background-color: #161F30; color: #818CF8; border: 1px solid rgba(99,102,241,0.25); border-radius: 6px; padding: 0 12px; font-size: 11px; font-weight: bold;")
        btn_open_win.clicked.connect(self._open_in_system_explorer)
        top_bar.addWidget(btn_open_win)

        main_layout.addLayout(top_bar)

        # نوار فیلتر
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("جستجو در این پوشه...")
        self.inp_search.setFixedHeight(32)
        self.inp_search.setFixedWidth(220)
        self.inp_search.setStyleSheet("background-color: #121826; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 10px; color: #F8FAFC; font-size: 11.5px;")
        self.inp_search.textChanged.connect(self._filter_items)
        filter_bar.addWidget(self.inp_search)

        self.combo_filter = QComboBox()
        self.combo_filter.setFixedHeight(32)
        self.combo_filter.addItem("همه فایل‌ها", "all")
        self.combo_filter.addItem("راش‌های ویدیو (Video)", "video")
        self.combo_filter.addItem("فایل‌های صوتی (Audio)", "audio")
        self.combo_filter.addItem("تصاویر / فرمالیته (Images)", "image")
        self.combo_filter.currentIndexChanged.connect(self._filter_items)
        self.combo_filter.setStyleSheet("background-color: #121826; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 8px; color: #F8FAFC; font-size: 11px;")
        filter_bar.addWidget(self.combo_filter)

        filter_bar.addStretch()

        self.btn_grid = self._create_svg_btn("grid", "حالت کارت (Grid)", lambda: self._set_view_mode("grid"))
        self.btn_list = self._create_svg_btn("list", "حالت لیست (List)", lambda: self._set_view_mode("list"))
        filter_bar.addWidget(self.btn_grid)
        filter_bar.addWidget(self.btn_list)

        main_layout.addLayout(filter_bar)

        # قفسه افقی پوشه‌ها
        self.folders_wrap = QFrame()
        self.folders_wrap.setObjectName("FoldersShelfFrame")
        self.folders_wrap.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px;")
        folders_wrap_lay = QVBoxLayout(self.folders_wrap)
        folders_wrap_lay.setContentsMargins(10, 8, 10, 8)
        folders_wrap_lay.setSpacing(6)

        lbl_folders_head = QLabel("پوشه‌های زیرمجموعه:")
        lbl_folders_head.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: bold; color: #818CF8;")
        folders_wrap_lay.addWidget(lbl_folders_head)

        self.folders_scroll = QScrollArea()
        self.folders_scroll.setFixedHeight(48)
        self.folders_scroll.setWidgetResizable(True)
        self.folders_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.folders_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.folders_scroll.setStyleSheet("background: transparent; border: none;")

        self.folders_container = QWidget()
        self.folders_container.setStyleSheet("background: transparent;")
        self.folders_layout = QHBoxLayout(self.folders_container)
        self.folders_layout.setContentsMargins(0, 0, 0, 0)
        self.folders_layout.setSpacing(8)
        self.folders_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.folders_scroll.setWidget(self.folders_container)
        folders_wrap_lay.addWidget(self.folders_scroll)

        main_layout.addWidget(self.folders_wrap)

        # فایل‌ها
        self.media_scroll = QScrollArea()
        self.media_scroll.setWidgetResizable(True)
        self.media_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.media_scroll.setStyleSheet("background: transparent; border: none;")

        self.media_container = QWidget()
        self.media_container.setStyleSheet("background: transparent;")
        self.media_layout = QVBoxLayout(self.media_container)
        self.media_layout.setContentsMargins(0, 0, 0, 0)
        self.media_layout.setSpacing(8)
        self.media_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.files_wrap = QWidget()
        self.files_wrap_layout = QVBoxLayout(self.files_wrap)
        self.files_wrap_layout.setContentsMargins(0, 0, 0, 0)
        self.files_wrap_layout.setSpacing(8)
        
        lbl_files_head = QLabel("راش‌ها و فایل‌های مدیا (برای پیش‌نمایش کلید Space را بزنید):")
        lbl_files_head.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: bold; color: #94A3B8;")
        self.files_wrap_layout.addWidget(lbl_files_head)

        self.files_grid = QGridLayout()
        self.files_grid.setSpacing(8)
        self.files_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        for i in range(4):
            self.files_grid.setColumnStretch(i, 1)
        self.files_wrap_layout.addLayout(self.files_grid)
        
        self.media_layout.addWidget(self.files_wrap)

        self.table_view = QTableWidget()
        self.table_view.setColumnCount(6)
        self.table_view.setHorizontalHeaderLabels(["نام فایل", "فرمت", "رزولوشن", "زمان", "FPS", "حجم"])
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setStyleSheet("""
            QTableWidget { background-color: #121826; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; color: #F8FAFC; }
            QHeaderView::section { background-color: #161F30; color: #8F909D; padding: 6px; font-weight: bold; border: none; }
        """)
        self.table_view.itemClicked.connect(self._on_table_row_clicked)
        self.table_view.setVisible(False)
        self.media_layout.addWidget(self.table_view)

        self.media_scroll.setWidget(self.media_container)
        main_layout.addWidget(self.media_scroll, stretch=1)

        # فوتر
        footer_row = QHBoxLayout()
        self.lbl_status = QLabel("در حال بارگذاری...")
        self.lbl_status.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8;")
        footer_row.addWidget(self.lbl_status, stretch=1)

        self.lbl_selection_count = QLabel("فایلی انتخاب نشده")
        self.lbl_selection_count.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: bold; color: #818CF8;")
        footer_row.addWidget(self.lbl_selection_count)

        btn_close = QPushButton("بستن")
        btn_close.setFixedHeight(30)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("background-color: #161F30; color: #94A3B8; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; padding: 0 14px; font-size: 11.5px;")
        btn_close.clicked.connect(self.accept)
        footer_row.addWidget(btn_close)

        main_layout.addLayout(footer_row)

    def _create_svg_btn(self, icon_name: str, tip: str, callback) -> QPushButton:
        btn = QPushButton()
        btn.setIcon(render_svg_icon(icon_name, "#F8FAFC", size=14))
        btn.setIconSize(QSize(14, 14))
        btn.setFixedSize(32, 32)
        btn.setToolTip(tip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #1E283D; border-color: #6366F1; }
        """)
        btn.clicked.connect(callback)
        return btn

    def _set_view_mode(self, mode: str):
        self.view_mode = mode
        is_grid = (mode == "grid")
        self.media_scroll.setVisible(True)
        self.table_view.setVisible(not is_grid)
        self._render_current_data()

    def navigate_to(self, target_path: str, add_to_history: bool = True):
        if not target_path or not Path(target_path).exists():
            self.lbl_status.setText("این مسیر در دسترس نیست.")
            return

        self.current_generation += 1
        for w in self.current_workers:
            w.cancel()
        self.current_workers.clear()

        if add_to_history and self.current_path != target_path:
            self.history_back.append(self.current_path)
            self.history_forward.clear()

        self.current_path = str(Path(target_path).resolve())
        self.address_bar.setText(self.current_path)
        self.selected_file_data = None
        self.lbl_selection_count.setText("فایلی انتخاب نشده")

        self.current_data = scan_directory_fast(self.current_path)
        self._filter_items()

    def _filter_items(self):
        query = self.inp_search.text().strip().lower()
        cat_filter = self.combo_filter.currentData() or "all"

        folders = self.current_data.get("folders", [])
        files = self.current_data.get("files", [])

        if cat_filter != "all":
            files = [f for f in files if f["category"] == cat_filter]

        if query:
            folders = [fo for fo in folders if query in fo["name"].lower()]
            files = [fi for fi in files if query in fi["name"].lower() or query in fi["ext"].lower()]

        self.filtered_folders = folders
        self.filtered_files = files
        self._render_current_data()

    def _render_current_data(self):
        while self.folders_layout.count():
            item = self.folders_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        while self.files_grid.count():
            item = self.files_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.active_cards.clear()
        self.table_view.setRowCount(0)

        # ۱. پوشه‌ها
        if self.filtered_folders:
            self.folders_wrap.setVisible(True)
            for folder in self.filtered_folders:
                pill = FolderItemPill(folder)
                pill.double_clicked.connect(lambda p: self.navigate_to(p))
                self.folders_layout.addWidget(pill)
            self.folders_layout.addStretch()
        else:
            self.folders_wrap.setVisible(False)

        # ۲. فایل‌ها
        if self.view_mode == "grid":
            self.files_wrap.setVisible(True)
            for idx, file in enumerate(self.filtered_files):
                mc = StudioMediaCard(file, index_num=idx + 1)
                mc.clicked.connect(self._select_file)
                mc.double_clicked.connect(self._open_quick_look)
                
                row = idx // 4
                col = idx % 4
                self.files_grid.addWidget(mc, row, col)
                self.active_cards[file["path"]] = mc

                if not file.get("thumbnail_pixmap"):
                    worker = ThumbnailWorker(file["path"], file["category"], self.current_generation)
                    worker.signals.loaded.connect(self._on_thumbnail_ready)
                    self.current_workers.append(worker)
                    self.threadpool.start(worker)
        else:
            self.files_wrap.setVisible(False)
            self.table_view.setRowCount(len(self.filtered_files))
            for row_idx, f in enumerate(self.filtered_files):
                self.table_view.setItem(row_idx, 0, QTableWidgetItem(f["name"]))
                self.table_view.setItem(row_idx, 1, QTableWidgetItem(f["ext"]))
                self.table_view.setItem(row_idx, 2, QTableWidgetItem(f.get("resolution", "—")))
                self.table_view.setItem(row_idx, 3, QTableWidgetItem(f.get("duration_str", "--:--")))
                self.table_view.setItem(row_idx, 4, QTableWidgetItem(f.get("fps", "—")))
                self.table_view.setItem(row_idx, 5, QTableWidgetItem(f.get("size_str", "—")))

        self.lbl_status.setText(
            f"{to_persian_numbers(len(self.filtered_folders))} پوشه  |  {to_persian_numbers(len(self.filtered_files))} مدیا  |  حجم کل: {self.current_data.get('total_size_str')}"
        )

    def _select_file(self, file_data: dict):
        target_path = file_data["path"]

        if self.selected_file_data and self.selected_file_data["path"] in self.active_cards:
            self.active_cards[self.selected_file_data["path"]].set_selected(False)

        self.selected_file_data = file_data
        if target_path in self.active_cards:
            self.active_cards[target_path].set_selected(True)

        self.lbl_selection_count.setText(f"انتخاب شده: {file_data.get('name')}")

    def _on_table_row_clicked(self, item):
        row = item.row()
        if 0 <= row < len(self.filtered_files):
            file_data = self.filtered_files[row]
            self._select_file(file_data)

    def _on_thumbnail_ready(self, file_path: str, meta: dict, pixmap: QPixmap):
        card = self.active_cards.get(file_path)
        if card:
            card.set_loaded_thumbnail(pixmap, meta)

    def _open_quick_look(self, file_data: dict = None):
        target = file_data or self.selected_file_data
        if not target:
            return

        if self.quick_look_dialog and self.quick_look_dialog.isVisible():
            self.quick_look_dialog.close()

        self.quick_look_dialog = AppleQuickLookDialog(
            target, 
            self.preloaded_player, 
            self.preloaded_audio, 
            self
        )
        self.quick_look_dialog.exec()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Space:
            event.accept()
            if self.selected_file_data:
                self._open_quick_look(self.selected_file_data)
            return
        super().keyPressEvent(event)

    def _go_back(self):
        if self.history_back:
            prev_path = self.history_back.pop()
            self.history_forward.append(self.current_path)
            self.navigate_to(prev_path, add_to_history=False)

    def _go_forward(self):
        if self.history_forward:
            next_path = self.history_forward.pop()
            self.history_back.append(self.current_path)
            self.navigate_to(next_path, add_to_history=False)

    def _go_up(self):
        curr = Path(self.current_path)
        if curr.parent != curr and curr.parent.exists():
            self.navigate_to(str(curr.parent.resolve()), add_to_history=True)

    def _open_in_system_explorer(self):
        if self.current_path and Path(self.current_path).exists():
            open_path_in_os(self.current_path)