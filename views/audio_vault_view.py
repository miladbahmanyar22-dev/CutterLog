# ==================================================
# FILE: views/audio_vault_view.py
# ==================================================
import os
import math
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QFileDialog, 
    QApplication, QMenu, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QUrl, Signal, QMimeData, QPoint, QRectF
from PySide6.QtGui import (
    QDrag, QDragEnterEvent, QDropEvent, QMouseEvent, 
    QAction, QPainter, QColor, QPen, QPixmap, QLinearGradient,
    QFont, QPainterPath
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from config import open_path_in_os
from core.audio_vault_manager import AudioVaultManager, get_vault_root_dir
from core.icon_provider import IconProvider
from core.persian_utils import to_persian_numbers
from core.signals import global_signals
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog


class AudioCategoryDialog(StudioBaseDialog):
    """دیالوگ مدرن استودیو برای ایجاد و تغییر نام پوشه‌های صوتی"""
    def __init__(self, initial_name: str = "", is_rename: bool = False, parent=None):
        super().__init__(parent=parent)
        self.is_rename = is_rename
        self.setFixedWidth(440)
        
        title = "تغییر نام پوشه صوتی" if is_rename else "ایجاد پوشه صوتی جدید"
        subtitle = "نام جدید را برای دسته‌بندی وارد کنید" if is_rename else "نام دسته‌بندی جدید موزیک/صدا را وارد کنید"
        icon_name = "edit" if is_rename else "folder_add"
        
        self.build_header(title, subtitle, icon_name=icon_name, icon_color="#818CF8")
        
        self.container_layout.addWidget(QLabel("نام پوشه دسته‌بندی:"))
        
        self.input_name = QLineEdit(initial_name)
        self.input_name.setFixedHeight(38)
        self.input_name.setPlaceholderText("مثال: رقص تکی، ورود عروس و داماد، تیزر...")
        self.input_name.setStyleSheet("""
            QLineEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-family: 'Vazirmatn';
                font-size: 12.5px;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.input_name.returnPressed.connect(self._submit)
        self.container_layout.addWidget(self.input_name)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_submit_text = "ثبت تغییر نام" if is_rename else "ایجاد پوشه"
        self.btn_submit = QPushButton(btn_submit_text)
        self.btn_submit.setFixedHeight(36)
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        self.btn_submit.clicked.connect(self._submit)
        btn_box.addWidget(self.btn_submit, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _submit(self):
        name = self.input_name.text().strip()
        if not name:
            return
        self.accept()

    def get_category_name(self) -> str:
        return self.input_name.text().strip()


class FolderStoryCard(QFrame):
    selected = Signal(str, str)
    rename_requested = Signal(str)
    delete_requested = Signal(str)

    PALETTES = [
        ("#6366F1", "#1E1B4B", "#818CF8"),
        ("#059669", "#064E3B", "#34D399"),
        ("#D97706", "#78350F", "#FBBF24"),
        ("#DB2777", "#831843", "#F472B6"),
        ("#7C3AED", "#4C1D95", "#A78BFA"),
        ("#0284C7", "#0C4A6E", "#38BDF8"),
    ]

    def __init__(self, folder_data: Dict[str, Any], index: int = 0, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.folder_data = folder_data
        self.index = index
        self.is_active = is_active
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(175, 82)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.init_ui()
        self.update_texts()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        self.lbl_icon = QLabel()
        top_row.addWidget(self.lbl_icon)
        top_row.addStretch()
        layout.addLayout(top_row)

        layout.addSpacing(2)

        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 12.5px;
                font-weight: 800;
                color: #FFFFFF !important;
                background: transparent !important;
                border: none !important;
            }
        """)
        layout.addWidget(self.lbl_title)

        self.lbl_counter = QLabel()
        self.lbl_counter.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 10.5px;
                font-weight: 600;
                color: #E2E8F0 !important;
                background: transparent !important;
                border: none !important;
            }
        """)
        layout.addWidget(self.lbl_counter)

    def update_texts(self):
        self.lbl_title.setText(self.folder_data.get("name", "پوشه"))
        cnt_str = f"{to_persian_numbers(self.folder_data.get('count', 0))} فایل صوتی"
        self.lbl_counter.setText(cnt_str)

        palette = self.PALETTES[self.index % len(self.PALETTES)]
        icon_color = "#FFFFFF" if self.is_active else palette[2]
        self.lbl_icon.setPixmap(IconProvider.get_pixmap("folder", icon_color, size=15))

    def set_active_state(self, active: bool):
        self.is_active = active
        self.update_texts()
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.folder_data["path"], self.folder_data["name"])
        super().mousePressEvent(event)

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        act_ren = QAction(IconProvider.get_icon("edit", "#818CF8", size=14), "تغییر نام پوشه", self)
        act_ren.triggered.connect(lambda: self.rename_requested.emit(self.folder_data["name"]))
        menu.addAction(act_ren)

        act_del = QAction(IconProvider.get_icon("trash", "#EF4444", size=14), "حذف پوشه", self)
        act_del.triggered.connect(lambda: self.delete_requested.emit(self.folder_data["name"]))
        menu.addAction(act_del)

        menu.exec(self.mapToGlobal(pos))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        palette = self.PALETTES[self.index % len(self.PALETTES)]

        grad = QLinearGradient(0, 0, self.width(), self.height())
        if self.is_active:
            grad.setColorAt(0.0, QColor(palette[0]))
            grad.setColorAt(0.5, QColor(palette[1]))
            grad.setColorAt(1.0, QColor("#0B0F17"))
        else:
            grad.setColorAt(0.0, QColor("#161F30"))
            grad.setColorAt(1.0, QColor("#0E131F"))

        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.setClipPath(path)
        painter.fillRect(rect, grad)

        wm_color = "rgba(255, 255, 255, 0.10)" if self.is_active else "rgba(255, 255, 255, 0.03)"
        wm_pix = IconProvider.get_pixmap("folder", wm_color, size=56)
        painter.drawPixmap(self.width() - 60, self.height() - 56, wm_pix)

        painter.setClipping(False)
        if self.is_active:
            border_pen = QPen(QColor(palette[2]), 1.8)
        else:
            border_pen = QPen(QColor(255, 255, 255, 18), 1.0)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 10, 10)
        painter.end()


class AddFolderStoryCard(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(110, 82)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        painter.setBrush(QColor("#111827"))
        dash_pen = QPen(QColor(99, 102, 241, 150), 1.6, Qt.PenStyle.DashLine)
        painter.setPen(dash_pen)
        painter.drawRoundedRect(rect, 10, 10)

        icon_pix = IconProvider.get_pixmap("folder_add", "#818CF8", size=22)
        painter.drawPixmap(int((self.width() - 22) / 2), 16, icon_pix)

        painter.setPen(QColor("#818CF8"))
        f = QFont("Vazirmatn", 9)
        f.setBold(True)
        painter.setFont(f)
        painter.drawText(QRectF(0, 48, self.width(), 24), Qt.AlignmentFlag.AlignCenter, "+ پوشه جدید")
        painter.end()


class CenterRadialPlayBtn(QWidget):
    toggle_play_requested = Signal()
    seek_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_playing = False
        self.progress = 0.0
        self.is_dragging = False

    def set_playing_state(self, playing: bool):
        self.is_playing = playing
        self.update()

    def set_progress(self, current_ms: int, total_ms: int):
        if not self.is_dragging:
            self.progress = min(max(current_ms / total_ms, 0.0), 1.0) if total_ms > 0 else 0.0
            self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            center_x, center_y = self.width() / 2, self.height() / 2
            dx, dy = event.pos().x() - center_x, event.pos().y() - center_y
            if math.hypot(dx, dy) < 16:
                self.toggle_play_requested.emit()
            else:
                self.is_dragging = True
                self._update_seek(dx, dy)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging:
            dx = event.pos().x() - (self.width() / 2)
            dy = event.pos().y() - (self.height() / 2)
            self._update_seek(dx, dy)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            dx = event.pos().x() - (self.width() / 2)
            dy = event.pos().y() - (self.height() / 2)
            self._update_seek(dx, dy)

    def _update_seek(self, dx: float, dy: float):
        angle = math.degrees(math.atan2(dx, -dy))
        if angle < 0:
            angle += 360
        ratio = min(max(angle / 360.0, 0.0), 1.0)
        self.progress = ratio
        self.update()
        self.seek_requested.emit(ratio)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        outer_rect = QRectF(2.5, 2.5, w - 5, h - 5)
        inner_rect = QRectF(6.0, 6.0, w - 12, h - 12)

        bg_pen = QPen(QColor(255, 255, 255, 30), 2.2)
        painter.setPen(bg_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(outer_rect)

        if self.progress > 0:
            prog_pen = QPen(QColor("#818CF8"), 2.5)
            prog_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(prog_pen)
            painter.drawArc(outer_rect, 90 * 16, -int(self.progress * 360 * 16))

        painter.setPen(Qt.PenStyle.NoPen)
        center_color = QColor("#6366F1") if self.is_playing else QColor(15, 23, 42, 210)
        painter.setBrush(center_color)
        painter.drawEllipse(inner_rect)

        icon_key = "pause" if self.is_playing else "play"
        icon_pix = IconProvider.get_pixmap(icon_key, "#FFFFFF", size=13)
        ix = int((w - 13) / 2) + (1 if not self.is_playing else 0)
        iy = int((h - 13) / 2)
        painter.drawPixmap(ix, iy, icon_pix)
        painter.end()


class PosterArtworkWidget(QFrame):
    def __init__(self, track_data: dict, parent=None):
        super().__init__(parent)
        self.track_data = track_data
        self.setFixedHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.pixmap: Optional[QPixmap] = None
        self._load_cover()

    def _load_cover(self):
        cover_bytes = self.track_data.get("cover_bytes")
        if cover_bytes:
            pix = QPixmap()
            if pix.loadFromData(cover_bytes):
                self.pixmap = pix
                return

        for ext in [".png", ".jpg", ".webp", ".jpeg"]:
            p = Path("images") / f"default_music_banner{ext}"
            if p.exists():
                self.pixmap = QPixmap(str(p))
                return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 8, 8)
        painter.setClipPath(path)

        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            sx = int((scaled.width() - self.width()) / 2)
            sy = int((scaled.height() - self.height()) / 2)
            painter.drawPixmap(0, 0, scaled, sx, sy, self.width(), self.height())
            painter.fillRect(self.rect(), QColor(0, 0, 0, 75))
        else:
            grad = QLinearGradient(0, 0, self.width(), self.height())
            h_seed = (abs(hash(self.track_data["name"])) % 5)
            palette = [
                ("#312E81", "#1E1B4B"),
                ("#064E3B", "#022C22"),
                ("#701A75", "#4A044E"),
                ("#1E293B", "#0F172A"),
                ("#831843", "#500724")
            ][h_seed]
            
            grad.setColorAt(0.0, QColor(palette[0]))
            grad.setColorAt(1.0, QColor(palette[1]))
            painter.fillRect(self.rect(), grad)

            watermark = IconProvider.get_pixmap("music", "rgba(255, 255, 255, 0.08)", size=48)
            painter.drawPixmap(int((self.width() - 48) / 2), int((self.height() - 48) / 2), watermark)

        painter.end()


class VerticalMusicCard(QFrame):
    play_action_triggered = Signal(str, str)
    seek_action_triggered = Signal(float)

    def __init__(self, track_data: dict, parent=None):
        super().__init__(parent)
        self.track_data = track_data
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(196)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(7, 7, 7, 8)
        root_layout.setSpacing(6)

        self.poster = PosterArtworkWidget(self.track_data, self)
        poster_lay = QVBoxLayout(self.poster)
        poster_lay.setContentsMargins(6, 6, 6, 6)

        top_row = QHBoxLayout()
        top_row.addStretch()
        lbl_badge = QLabel(self.track_data["ext"])
        lbl_badge.setStyleSheet("""
            background-color: rgba(15, 23, 42, 0.85);
            color: #818CF8;
            font-family: 'Segoe UI';
            font-size: 9px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        """)
        top_row.addWidget(lbl_badge)
        poster_lay.addLayout(top_row)

        poster_lay.addStretch()

        center_row = QHBoxLayout()
        center_row.addStretch()
        self.btn_play = CenterRadialPlayBtn(self.poster)
        self.btn_play.toggle_play_requested.connect(lambda: self.play_action_triggered.emit(self.track_data["file_path"], self.track_data["name"]))
        self.btn_play.seek_requested.connect(self.seek_action_triggered.emit)
        center_row.addWidget(self.btn_play)
        center_row.addStretch()
        poster_lay.addLayout(center_row)

        poster_lay.addStretch()
        root_layout.addWidget(self.poster)

        raw_name = self.track_data["name"]
        if " - " in raw_name:
            parts = raw_name.split(" - ", 1)
            title_text = parts[1].strip()
            artist_text = parts[0].strip()
        else:
            title_text = raw_name
            artist_text = ""

        self.lbl_title = QLabel(title_text)
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.lbl_title.setFixedHeight(34)
        self.lbl_title.setToolTip(raw_name)
        self.lbl_title.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 11.5px;
                font-weight: 700;
                color: #F8FAFC;
                line-height: 1.25;
                background: transparent;
                border: none;
            }
        """)
        root_layout.addWidget(self.lbl_title)

        if artist_text:
            self.lbl_artist = QLabel(artist_text)
            self.lbl_artist.setAlignment(Qt.AlignmentFlag.AlignRight)
            self.lbl_artist.setStyleSheet("font-family: 'Vazirmatn'; font-size: 10px; color: #64748B; background: transparent; border: none;")
            root_layout.addWidget(self.lbl_artist)

        self.set_active_state(False)

    def set_active_state(self, is_active: bool):
        if is_active:
            self.setStyleSheet("""
                QFrame {
                    background-color: #1A243A;
                    border: 1.5px solid #6366F1;
                    border-radius: 9px;
                }
            """)
            self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #818CF8; background: transparent; border: none;")
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #121826;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 9px;
                }
                QFrame:hover {
                    background-color: #161F30;
                    border-color: rgba(99, 102, 241, 0.35);
                }
            """)
            self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: #F8FAFC; background: transparent; border: none;")
            try:
                self.btn_play.set_progress(0, 1)
            except RuntimeError:
                pass

    def update_playback_progress(self, current_ms: int, total_ms: int):
        try:
            self.btn_play.set_progress(current_ms, total_ms)
        except RuntimeError:
            pass

    def set_playback_state(self, is_playing: bool):
        try:
            self.btn_play.set_playing_state(is_playing)
            self.set_active_state(is_playing)
        except RuntimeError:
            pass

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, "_drag_start_pos"):
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        file_path = self.track_data.get("file_path")
        if file_path and os.path.exists(file_path):
            drag = QDrag(self)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(file_path)])
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)


class MinimalDropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(40)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap("folder_add", "#818CF8", size=15))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon_lbl)

        lbl_t = QLabel("فایل‌های صوتی را به اینجا بکشید یا دکمه افزودن را بزنید")
        lbl_t.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600; color: #94A3B8; border: none; background: transparent;")
        layout.addWidget(lbl_t, stretch=1)

        btn_add = QPushButton("افزودن فایل...")
        btn_add.setFixedHeight(24)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #818CF8;
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 4px;
                padding: 0 10px;
                font-size: 10.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #6366F1;
                color: #FFFFFF;
            }
        """)
        btn_add.clicked.connect(self._browse_files)
        layout.addWidget(btn_add)

        self._set_normal_style()

    def _set_normal_style(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #121826;
                border: 1px dashed rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }
            QFrame:hover {
                border-color: rgba(99, 102, 241, 0.4);
                background-color: #141C2B;
            }
        """)

    def _set_active_style(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #162032;
                border: 1.5px dashed #10B981;
                border-radius: 6px;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_active_style()

    def dragLeaveEvent(self, event):
        self._set_normal_style()

    def dropEvent(self, event: QDropEvent):
        self._set_normal_style()
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "انتخاب موزیک برای آرشیو", "",
            "Audio Files (*.mp3 *.wav *.flac *.aac *.m4a *.ogg);;All Files (*.*)"
        )
        if files:
            self.files_dropped.emit(files)


class AudioVaultView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.current_folder_path: Optional[str] = None
        self.current_folder_name: Optional[str] = None
        self.current_playing_file: Optional[str] = None
        self.active_card: Optional[VerticalMusicCard] = None
        self.story_cards: List[FolderStoryCard] = []
        self._current_cols = 6

        self._init_player()
        self.init_ui()
        self.refresh_categories()

    def _init_player(self):
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)

        self.player.positionChanged.connect(self._on_player_position_changed)
        self.player.durationChanged.connect(self._on_player_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 16, 24, 16)
        root_layout.setSpacing(12)

        # ۱. کادر پوشه‌ها
        self.folder_box_frame = QFrame()
        self.folder_box_frame.setStyleSheet("""
            QFrame#FolderBoxFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 12px;
            }
        """)
        self.folder_box_frame.setObjectName("FolderBoxFrame")
        folder_box_layout = QVBoxLayout(self.folder_box_frame)
        folder_box_layout.setContentsMargins(14, 12, 14, 12)
        folder_box_layout.setSpacing(10)

        folder_header_row = QHBoxLayout()
        folder_header_row.setSpacing(8)

        icon_f = QLabel()
        icon_f.setPixmap(IconProvider.get_pixmap("folder", "#818CF8", size=16))
        icon_f.setStyleSheet("border: none; background: transparent;")
        folder_header_row.addWidget(icon_f)

        lbl_f_title = QLabel("دسته‌بندی‌ها و پوشه‌های صوتی")
        lbl_f_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        folder_header_row.addWidget(lbl_f_title)
        folder_header_row.addStretch()

        self.lbl_folder_count = QLabel("")
        self.lbl_folder_count.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; border: none; background: transparent;")
        folder_header_row.addWidget(self.lbl_folder_count)

        folder_box_layout.addLayout(folder_header_row)

        self.scroll_stories = QScrollArea()
        self.scroll_stories.setFixedHeight(94)
        self.scroll_stories.setWidgetResizable(True)
        self.scroll_stories.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_stories.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.stories_container = QWidget()
        self.stories_container.setStyleSheet("background: transparent;")
        self.stories_layout = QHBoxLayout(self.stories_container)
        self.stories_layout.setContentsMargins(0, 0, 0, 0)
        self.stories_layout.setSpacing(10)
        self.stories_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.scroll_stories.setWidget(self.stories_container)
        folder_box_layout.addWidget(self.scroll_stories)

        root_layout.addWidget(self.folder_box_frame)

        # ۲. نوار ابزار
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)
        action_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.drop_zone = MinimalDropZone(self)
        self.drop_zone.files_dropped.connect(self._handle_files_ingest)
        action_bar.addWidget(self.drop_zone, stretch=1)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("جستجو در این پوشه...")
        self.txt_search.setFixedWidth(220)
        self.txt_search.setFixedHeight(40)
        self.txt_search.setStyleSheet("""
            QLineEdit {
                font-family: 'Vazirmatn';
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 10px;
                color: #F8FAFC;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #6366F1;
            }
        """)
        self.txt_search.textChanged.connect(self.refresh_tracks)
        action_bar.addWidget(self.txt_search)

        self.btn_open_win = QPushButton("نمایش در سیستم‌عامل ↗")
        self.btn_open_win.setFixedHeight(40)
        self.btn_open_win.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_win.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #121826;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #161F30;
                color: #F8FAFC;
                border-color: #6366F1;
            }
        """)
        self.btn_open_win.clicked.connect(self._open_in_windows_explorer)
        action_bar.addWidget(self.btn_open_win)

        root_layout.addLayout(action_bar)

        # ۳. گرید کارتی ریسپانسیو
        self.scroll_tracks = QScrollArea()
        self.scroll_tracks.setWidgetResizable(True)
        self.scroll_tracks.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.tracks_container = QWidget()
        self.tracks_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.tracks_container)
        self.grid_layout.setContentsMargins(0, 4, 0, 4)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_tracks.setWidget(self.tracks_container)
        root_layout.addWidget(self.scroll_tracks, stretch=1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.scroll_tracks.width()
        if w < 760:
            cols = 3
        elif w < 980:
            cols = 4
        elif w < 1240:
            cols = 5
        else:
            cols = 6

        if hasattr(self, "_current_cols") and self._current_cols == cols:
            return
        self._current_cols = cols

        for i in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(i, 0)
        for col_idx in range(cols):
            self.grid_layout.setColumnStretch(col_idx, 1)

        self.refresh_tracks()

    def refresh_categories(self):
        prev_name = self.current_folder_name
        self.story_cards.clear()

        while self.stories_layout.count():
            item = self.stories_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        add_card = AddFolderStoryCard(self)
        add_card.clicked.connect(self._add_category_dialog)
        self.stories_layout.addWidget(add_card)

        categories = AudioVaultManager.get_categories()
        target_folder = None

        for idx, cat in enumerate(categories):
            is_active = (prev_name and cat["name"] == prev_name) or (not prev_name and idx == 0)
            card = FolderStoryCard(cat, index=idx, is_active=is_active, parent=self)
            card.selected.connect(self._on_story_folder_selected)
            card.rename_requested.connect(self._rename_category)
            card.delete_requested.connect(self._delete_category)

            self.stories_layout.addWidget(card)
            self.story_cards.append(card)

            if is_active:
                target_folder = cat

        self.stories_layout.addStretch()

        cnt = len(categories)
        self.lbl_folder_count.setText(f"{to_persian_numbers(cnt)} دسته‌بندی فعال" if cnt > 0 else "")

        if target_folder:
            self._on_story_folder_selected(target_folder["path"], target_folder["name"])
        elif categories:
            self._on_story_folder_selected(categories[0]["path"], categories[0]["name"])
        else:
            self.current_folder_path = None
            self.current_folder_name = None
            self.refresh_tracks()

    def _on_story_folder_selected(self, folder_path: str, folder_name: str):
        self.current_folder_path = folder_path
        self.current_folder_name = folder_name

        for card in self.story_cards:
            card.set_active_state(card.folder_data["name"] == folder_name)

        self.refresh_tracks()

    def refresh_tracks(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()

        while self.grid_layout.count():
            w = self.grid_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        cols = getattr(self, "_current_cols", 6)

        if not self.current_folder_path:
            lbl_empty = QLabel("هنوز پوشه‌ای ساخته نشده است. با کلیک روی «+ پوشه جدید» اولین پوشه خود را ایجاد کنید.")
            lbl_empty.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; color: #64748B; margin-top: 60px; border: none;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl_empty, 0, 0, 1, cols)
            return

        tracks = AudioVaultManager.get_tracks_in_category(self.current_folder_path, self.txt_search.text())

        if not tracks:
            lbl_empty = QLabel(f"پوشه «{self.current_folder_name}» خالی است. فایل‌های صوتی را به این بخش بکشید و رها کنید.")
            lbl_empty.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; color: #64748B; margin-top: 60px; border: none;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl_empty, 0, 0, 1, cols)
            return

        for idx, trk in enumerate(tracks):
            card = VerticalMusicCard(trk, parent=self)
            card.play_action_triggered.connect(self._handle_track_toggle)
            card.seek_action_triggered.connect(self._handle_seek)
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card, row, col)

    def _handle_track_toggle(self, file_path: str, track_name: str):
        sender_card = self.sender().parent().parent() if isinstance(self.sender(), CenterRadialPlayBtn) else self.sender()
        if not isinstance(sender_card, VerticalMusicCard):
            return

        if self.current_playing_file == file_path:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            else:
                self.player.play()
            return

        if self.active_card:
            try:
                self.active_card.set_playback_state(False)
            except RuntimeError:
                pass

        self.active_card = sender_card
        self.current_playing_file = file_path
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.player.play()

    def _handle_seek(self, ratio: float):
        if self.player.duration() > 0:
            self.player.setPosition(int(self.player.duration() * ratio))

    def _on_playback_state_changed(self, state):
        if not self.active_card:
            return
        try:
            self.active_card.set_playback_state(state == QMediaPlayer.PlaybackState.PlayingState)
        except RuntimeError:
            pass

    def _on_player_position_changed(self, pos_ms: int):
        if not self.active_card:
            return
        try:
            self.active_card.update_playback_progress(pos_ms, self.player.duration())
        except RuntimeError:
            pass

    def _on_player_duration_changed(self, dur_ms: int):
        if not self.active_card:
            return
        try:
            self.active_card.update_playback_progress(self.player.position(), dur_ms)
        except RuntimeError:
            pass

    def _handle_files_ingest(self, file_paths: list):
        if not self.current_folder_path:
            global_signals.show_toast.emit("لطفاً ابتدا یک پوشه ایجاد یا انتخاب کنید.", "warning")
            return
        
        copied_cnt = AudioVaultManager.ingest_files_to_category(self.current_folder_path, file_paths)
        if copied_cnt > 0:
            global_signals.show_toast.emit(f"{to_persian_numbers(copied_cnt)} فایل با موفقیت اضافه شد.", "success")
            self.refresh_categories()
        else:
            global_signals.show_toast.emit("فایل صوتی معتبری برای افزودن یافت نشد.", "warning")

    def _add_category_dialog(self):
        diag = AudioCategoryDialog(initial_name="", is_rename=False, parent=self.window())
        if diag.exec():
            name = diag.get_category_name()
            if name and AudioVaultManager.create_category(name):
                global_signals.show_toast.emit("پوشه جدید با موفقیت ساخته شد.", "success")
                self.current_folder_name = name
                self.refresh_categories()
            else:
                global_signals.show_toast.emit("خطا در ایجاد پوشه یا نام تکراری است.", "error")

    def _rename_category(self, old_name: str):
        diag = AudioCategoryDialog(initial_name=old_name, is_rename=True, parent=self.window())
        if diag.exec():
            new_name = diag.get_category_name()
            if new_name and new_name != old_name:
                if AudioVaultManager.rename_category(old_name, new_name):
                    global_signals.show_toast.emit("نام پوشه با موفقیت تغییر کرد.", "success")
                    self.current_folder_name = new_name
                    self.refresh_categories()
                else:
                    global_signals.show_toast.emit("خطا در تغییر نام یا پوشه هم‌نام موجود است.", "error")

    def _delete_category(self, folder_name: str):
        if StudioConfirmDialog.ask(
            self.window(),
            title="تأیید حذف پوشه",
            message=f"آیا از حذف کامل پوشه صوتی «{folder_name}» اطمینان دارید؟",
            details="در صورت فعال بودن حالت کپی، تمامی فایل‌های فیزیکی این پوشه نیز پاک خواهند شد.",
            confirm_text="حذف پوشه",
            is_danger=True,
            icon_name="trash"
        ):
            if AudioVaultManager.delete_category(folder_name):
                global_signals.show_toast.emit("پوشه مورد نظر حذف شد.", "success")
                self.current_folder_name = None
                self.refresh_categories()
            else:
                global_signals.show_toast.emit("خطا در حذف پوشه.", "error")

    def _open_in_windows_explorer(self):
        target = self.current_folder_path if self.current_folder_path and os.path.exists(self.current_folder_path) else str(get_vault_root_dir().resolve())
        open_path_in_os(target)

    def hideEvent(self, event):
        self.player.stop()
        if self.active_card:
            try:
                self.active_card.set_playback_state(False)
            except RuntimeError:
                pass
        super().hideEvent(event)